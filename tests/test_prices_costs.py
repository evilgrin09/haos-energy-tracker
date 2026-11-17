"""Tests for price changes within contracts and the cost history."""

from datetime import date

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_tracker.calc import (
    PROFILES,
    ConsumptionModel,
    Reading,
    billing_forecast,
    build_tariff,
)
from custom_components.energy_tracker.const import DOMAIN
from custom_components.energy_tracker.costs import (
    bill_days,
    calendar_years,
    meter_cost_history,
    period_costs,
    sum_years,
)
from custom_components.energy_tracker.store import migrate

FLAT = PROFILES["flat"]
YEAR = (date(2024, 10, 1), date(2025, 9, 30))  # billing year 2024/25, 365 days
TODAY = date(2026, 1, 15)


def _model(per_day: float, start: date, end: date) -> ConsumptionModel:
    """Exactly ``per_day`` measured consumption on every day after ``start``."""
    return ConsumptionModel([Reading(start, 0.0), Reading(end, per_day * (end - start).days)], FLAT)


def _contract(**extra) -> dict:
    return {
        "id": "c",
        "start_date": "2020-01-01",
        "unit_price": 0.30,
        "base_price": 10.0,
        "conversion_factor": 1.0,
        **extra,
    }


# ------------------------------------------------------------ price changes


def test_price_change_mid_billing_year() -> None:
    """A price change on 01.04. splits the year into two segments."""
    model = _model(10, date(2024, 9, 30), date(2025, 9, 30))
    tariff = build_tariff(
        _contract(price_changes=[{"date": "2025-04-01", "unit_price": 0.40, "base_price": 12.0}])
    )
    result = billing_forecast(model, [tariff], YEAR, TODAY)
    segments = [
        (s["start"], s["end"], s["days"], s["unit_price"], s["base_price"]) for s in result["segments"]
    ]
    assert segments == [
        ("2024-10-01", "2025-03-31", 182, 0.30, 10.0),
        ("2025-04-01", "2025-09-30", 183, 0.40, 12.0),
    ]
    assert result["energy_cost"] == pytest.approx(1820 * 0.30 + 1830 * 0.40)
    assert result["base_cost"] == pytest.approx(10 * 12 / 365 * 182 + 12 * 12 / 365 * 183)
    assert result["segments"][1]["energy_cost"] == pytest.approx(1830 * 0.40)


def test_several_price_changes_and_empty_fields() -> None:
    """Several changes; empty fields keep the previous value."""
    tariff = build_tariff(
        _contract(
            price_changes=[
                {"date": "2025-07-01", "unit_price": 0.35, "note": "Erhöhung"},
                {"date": "2025-01-01", "base_price": 11.0},
                {"date": "2025-09-01", "unit_price": 0.33, "base_price": None},
            ]
        )
    )
    phases = [(p.start.isoformat(), p.unit_price, p.base_price, p.note) for p in tariff.phases]
    assert phases == [
        ("2020-01-01", 0.30, 10.0, ""),
        ("2025-01-01", 0.30, 11.0, ""),
        ("2025-07-01", 0.35, 11.0, "Erhöhung"),
        ("2025-09-01", 0.33, 11.0, ""),
    ]
    model = _model(10, date(2024, 9, 30), date(2025, 9, 30))
    result = billing_forecast(model, [tariff], YEAR, TODAY)
    assert [s["days"] for s in result["segments"]] == [92, 181, 62, 30]
    assert result["energy_cost"] == pytest.approx(10 * (273 * 0.30 + 62 * 0.35 + 30 * 0.33))


def test_change_of_base_price_only() -> None:
    """Only the base price changes: the energy cost stays the same."""
    model = _model(10, date(2024, 9, 30), date(2025, 9, 30))
    plain = billing_forecast(model, [build_tariff(_contract())], YEAR, TODAY)
    changed = billing_forecast(
        model,
        [build_tariff(_contract(price_changes=[{"date": "2025-01-01", "base_price": 15.0}]))],
        YEAR,
        TODAY,
    )
    assert changed["energy_cost"] == pytest.approx(plain["energy_cost"])
    assert changed["base_cost"] == pytest.approx(10 * 12 / 365 * 92 + 15 * 12 / 365 * 273)
    assert [s["unit_price"] for s in changed["segments"]] == [0.30, 0.30]


def test_gas_with_changed_conversion_factor() -> None:
    """The new conversion factor applies to the m³ of the days after the change."""
    model = _model(2, date(2024, 9, 30), date(2025, 9, 30))
    tariff = build_tariff(
        _contract(
            unit_price=0.10,
            base_price=0.0,
            conversion_factor=10.0,
            price_changes=[{"date": "2025-01-01", "conversion_factor": 11.0}],
        )
    )
    result = billing_forecast(model, [tariff], YEAR, TODAY)
    assert result["consumption_billing_unit"] == pytest.approx(92 * 20 + 273 * 22)
    assert result["energy_cost"] == pytest.approx((92 * 20 + 273 * 22) * 0.10)
    assert [s["conversion_factor"] for s in result["segments"]] == [10.0, 11.0]


# -------------------------------------------------------------- cost history


def test_bill_takes_precedence() -> None:
    """A recorded bill replaces the own calculation of its days."""
    model = _model(10, date(2024, 9, 30), date(2025, 9, 30))
    tariffs = [build_tariff(_contract())]
    bill = {
        "id": "b",
        "start_date": "2024-10-01",
        "end_date": "2025-09-30",
        "consumption": 3800,
        "total_cost": 1500.0,
        "base_price": 12.0,
    }
    shares = bill_days(model, tariffs, [bill], TODAY)
    year = period_costs(model, tariffs, shares, YEAR, TODAY, date(2024, 10, 1), "kWh")
    assert year["source"] == "bill"
    assert year["status"] == "complete"
    assert year["total_cost"] == pytest.approx(1500)
    assert year["base_cost"] == pytest.approx(144)
    assert year["energy_cost"] == pytest.approx(1356)
    assert year["consumption"] == pytest.approx(3800)
    assert year["avg_price"] == pytest.approx(1500 * 100 / 3800)
    assert year["bill_ids"] == ["b"]

    # calendar year 2025: Jan-Sep from the bill, Oct-Dec calculated
    calendar = period_costs(
        model, tariffs, shares, (date(2025, 1, 1), date(2025, 12, 31)), TODAY, date(2024, 10, 1), "kWh"
    )
    assert calendar["source"] == "mixed"
    bill_part = 1356 * 273 / 365 + 144 * 273 / 365
    own_part = 92 * 10 * 0.30 + 10 * 12 / 365 * 92
    assert calendar["total_cost"] == pytest.approx(bill_part + own_part)


def test_gaps_no_data_and_no_tariff() -> None:
    """Years without data or without tariff are gaps, not 0 EUR."""
    model = _model(10, date(2024, 12, 31), date(2025, 12, 31))
    tariffs = [build_tariff(_contract(start_date="2025-07-01"))]
    periods = calendar_years(date(2023, 1, 1), date(2026, 1, 15))
    years = meter_cost_history(model, tariffs, [], periods, date(2026, 1, 15), "kWh", 9, "calendar")
    by_label = {y["label"]: y for y in years}
    assert by_label["2023"]["status"] == "gap"
    assert by_label["2023"]["gap_reason"] == "no_data"
    assert by_label["2023"]["total_cost"] is None
    assert by_label["2023"]["consumption"] is None
    # 2025: data for the whole year, tariff only from July
    assert by_label["2025"]["status"] == "partial"
    assert by_label["2025"]["cost_coverage"] == pytest.approx(184 / 365)
    assert by_label["2025"]["avg_price"] is None
    assert by_label["2026"]["forecast"] is True
    assert by_label["2026"]["status"] == "complete"
    # no change against an incomplete year
    assert by_label["2026"]["change"] is None

    no_tariff = meter_cost_history(model, [], [], periods, date(2026, 1, 15), "kWh", 9, "calendar")
    assert {y["label"]: y["gap_reason"] for y in no_tariff} == {
        "2023": "no_data",
        "2024": "no_data",
        "2025": "no_tariff",
        "2026": "no_tariff",
    }


def test_change_to_previous_year_and_sum() -> None:
    """Change in EUR and % to the previous year; sum over meters."""
    model = _model(10, date(2023, 12, 31), date(2025, 12, 31))
    tariffs = [build_tariff(_contract(price_changes=[{"date": "2025-01-01", "unit_price": 0.33}]))]
    periods = calendar_years(date(2024, 1, 1), date(2025, 12, 31))
    years = meter_cost_history(model, tariffs, [], periods, date(2026, 1, 1), "kWh", 9, "calendar")
    cost_2024 = 3660 * 0.30 + 120 * 366 / 365
    cost_2025 = 3650 * 0.33 + 120
    assert years[0]["total_cost"] == pytest.approx(cost_2024)
    assert years[1]["change"] == pytest.approx(cost_2025 - cost_2024)
    assert years[1]["change_pct"] == pytest.approx((cost_2025 - cost_2024) / cost_2024 * 100)
    assert years[1]["avg_price"] == pytest.approx(cost_2025 * 100 / 3650)

    water = meter_cost_history(
        _model(0.3, date(2023, 12, 31), date(2025, 12, 31)),
        [build_tariff(_contract(unit_price=4.0, base_price=5.0))],
        [],
        periods,
        date(2026, 1, 1),
        "m³",
        9,
        "calendar",
    )
    assert water[1]["avg_price_unit"] == "€/m³"
    total = sum_years([("Strom", years), ("Wasser", water)])
    assert total[1]["total_cost"] == pytest.approx(years[1]["total_cost"] + water[1]["total_cost"])
    assert total[1]["status"] == "complete"
    assert total[1]["consumption"] is None


def test_billing_mode_uses_bill_result() -> None:
    """Billing years show payments and result of the bill or the own calculation."""
    model = _model(10, date(2023, 9, 30), date(2025, 9, 30))
    tariffs = [build_tariff(_contract(advance_payment=100, payment_day=1))]
    bill = {
        "id": "b",
        "start_date": "2023-10-01",
        "end_date": "2024-09-30",
        "total_cost": 1300.0,
        "advances_paid": 1200.0,
    }
    periods = [(date(2023, 10, 1), date(2024, 9, 30)), YEAR]
    years = meter_cost_history(model, tariffs, [bill], periods, TODAY, "kWh", 9, "billing")
    assert [y["label"] for y in years] == ["2023/24", "2024/25"]
    assert (years[0]["result"], years[0]["result_source"]) == (pytest.approx(-100), "bill")
    assert years[0]["advances_source"] == "bill"
    assert years[1]["advances"] == pytest.approx(1200)
    assert years[1]["result"] == pytest.approx(1200 - years[1]["total_cost"])
    assert years[1]["result_source"] == "calculated"


def test_migration_to_version_3() -> None:
    """Contracts get an empty list of price changes, bills keep their values."""
    data = {
        "meters": [],
        "contracts": [{"id": "c", "start_date": "2025-01-01", "unit_price": 0.3}],
        "bills": [{"id": "b", "total_cost": 100.0}],
    }
    migrated = migrate(2, data)
    assert migrated["contracts"][0]["price_changes"] == []
    assert migrated["contracts"][0]["unit_price"] == 0.3
    assert migrated["bills"] == [{"id": "b", "total_cost": 100.0}]


# ----------------------------------------------------------------- websocket


@pytest.fixture
def frozen(freezer: FrozenDateTimeFactory) -> None:
    """Freeze the time before the websocket client (and its token) is created."""
    freezer.move_to("2026-01-15 12:00:00+00:00")


@pytest.fixture
async def ws(hass: HomeAssistant, frozen, hass_ws_client, enable_custom_integrations):
    """Integration with a websocket helper (time frozen before the token is created)."""
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, options={"show_panel": False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)

    async def call(msg_type: str, **data):
        await client.send_json_auto_id({"type": f"{DOMAIN}/{msg_type}", **data})
        return await client.receive_json()

    return call


async def test_price_change_validation(hass: HomeAssistant, ws) -> None:
    """Dates within the term, one change per day, prices > 0."""
    meter = (await ws("meter/save", name="Gas", meter_type="gas", unit="m³"))["result"]
    base = {"meter_id": meter["id"], "start_date": "2024-01-01", "end_date": "2025-12-31", "unit_price": 0.1}
    for changes, code in (
        ([{"date": "2024-01-01", "unit_price": 0.2}], "price_change_outside"),
        ([{"date": "2026-01-01", "unit_price": 0.2}], "price_change_outside"),
        (
            [{"date": "2024-06-01", "unit_price": 0.2}, {"date": "2024-06-01", "base_price": 3}],
            "price_change_duplicate",
        ),
        ([{"date": "2024-06-01", "unit_price": 0}], "price_change_invalid"),
        ([{"date": "2024-06-01", "unit_price": None, "note": "x"}], "price_change_empty"),
    ):
        msg = await ws("contract/save", **base, price_changes=changes)
        assert not msg["success"], changes
        assert msg["error"]["code"] == code

    msg = await ws(
        "contract/save",
        **base,
        price_changes=[
            {"date": "2025-01-01", "unit_price": 0.12, "note": "Preisanpassung"},
            {"date": "2024-07-01", "conversion_factor": 10.5, "unit_price": ""},
        ],
    )
    assert msg["success"], msg
    assert msg["result"]["price_changes"] == [
        {"date": "2024-07-01", "unit_price": None, "base_price": None, "conversion_factor": 10.5, "note": ""},
        {
            "date": "2025-01-01",
            "unit_price": 0.12,
            "base_price": None,
            "conversion_factor": None,
            "note": "Preisanpassung",
        },
    ]


async def test_bill_readings_and_cost_history(hass: HomeAssistant, ws) -> None:
    """Readings from bills fill the history; bills without readings or tariffs are allowed."""
    store = hass.data[DOMAIN]
    meter = (await ws("meter/save", name="Gas", meter_type="gas", unit="m³"))["result"]
    await ws("reading/save", meter_id=meter["id"], date="2024-10-05", value=9502)

    # old bill: no readings and no tariff in this period
    msg = await ws(
        "bill/save",
        meter_id=meter["id"],
        start_date="2022-10-01",
        end_date="2023-09-30",
        consumption=11000,
        consumption_unit="billing",
        total_cost=1650.0,
        advances_paid=1500.0,
        reading_start=7900,
        reading_end=8950,
        unit_price=0.12,
        base_price=14.0,
        conversion_factor=10.48,
        take_readings=True,
    )
    assert msg["success"], msg
    assert [(r["which"], r["date"], r["status"]) for r in msg["result"]["imported_readings"]] == [
        ("start", "2022-09-30", "added"),
        ("end", "2023-09-30", "added"),
    ]
    readings = store.meter_readings(meter["id"])
    assert [(r["date"], r["value"], r["note"]) for r in readings][:2] == [
        ("2022-09-30", 7900.0, "aus Abrechnung"),
        ("2023-09-30", 8950.0, "aus Abrechnung"),
    ]
    assert "imported_readings" not in store.bills[msg["result"]["id"]]

    # next bill: end reading conflicts with the own reading of 05.10.2024 (lower value)
    msg = await ws(
        "bill/save",
        meter_id=meter["id"],
        start_date="2023-10-01",
        end_date="2024-09-30",
        total_cost=1400.0,
        reading_start=8950,
        reading_end=9600,
        take_readings=True,
    )
    result = {r["which"]: r for r in msg["result"]["imported_readings"]}
    assert result["start"]["status"] == "exists"
    assert result["end"]["status"] == "conflict"
    assert result["end"]["code"] == "value_too_high"

    # without take_readings nothing is imported
    msg = await ws(
        "bill/save", meter_id=meter["id"], start_date="2021-10-01", end_date="2022-09-30", reading_start=1
    )
    assert msg["result"]["imported_readings"] == []

    msg = await ws("cost_history", meter_id=meter["id"], mode="billing")
    assert msg["success"], msg
    years = {y["label"]: y for y in msg["result"]["meters"][0]["years"]}
    assert years["2022/23"]["source"] == "bill"
    assert years["2022/23"]["total_cost"] == pytest.approx(1650)
    assert years["2022/23"]["consumption_billing"] == pytest.approx(11000)
    assert years["2022/23"]["result"] == pytest.approx(-150)
    assert years["2023/24"]["total_cost"] == pytest.approx(1400)
    # 45 days after the last bill are valued with its prices, the rest has no tariff
    assert years["2024/25"]["status"] == "partial"
    assert years["2024/25"]["extrapolated_days"] == 45
    assert years["2024/25"]["source"] == "bill_extrapolated"
    assert msg["result"]["total"] is None

    msg = await ws("cost_history", mode="calendar")
    result = msg["result"]
    assert [y["label"] for y in result["meters"][0]["years"]][:2] == ["2021", "2022"]
    assert result["meters"][0]["years"][-1]["label"] == "2026"
    assert result["total"][-1]["label"] == "2026"
    msg = await ws("cost_history", meter_id="nope")
    assert msg["error"]["code"] == "not_found"


async def test_reading_source_and_estimated_end(hass: HomeAssistant, ws) -> None:
    """Readings from bills have source "bill"; an estimated end reading is not taken over."""
    store = hass.data[DOMAIN]
    meter = (await ws("meter/save", name="Wasser", meter_type="water", unit="m³"))["result"]
    await ws("reading/save", meter_id=meter["id"], date="2025-11-01", value=640)
    msg = await ws(
        "bill/save",
        meter_id=meter["id"],
        start_date="2024-10-01",
        end_date="2025-09-30",
        total_cost=480.0,
        reading_start=520,
        reading_end=625,
        reading_end_estimated=True,
        take_readings=True,
    )
    assert msg["success"], msg
    assert [(r["which"], r["status"]) for r in msg["result"]["imported_readings"]] == [("start", "added")]
    assert msg["result"]["reading_end_estimated"] is True
    readings = store.meter_readings(meter["id"])
    assert [(r["date"], r["source"]) for r in readings] == [("2024-09-30", "bill"), ("2025-11-01", "manual")]


async def test_bill_save_reports_implausible_consumption(hass: HomeAssistant, ws) -> None:
    """The bill is saved, but a warning is returned."""
    meter = (await ws("meter/save", name="Strom", meter_type="electricity", unit="kWh"))["result"]
    await ws("reading/save", meter_id=meter["id"], date="2024-09-30", value=1000)
    await ws("reading/save", meter_id=meter["id"], date="2025-09-30", value=4650)
    msg = await ws(
        "bill/save",
        meter_id=meter["id"],
        start_date="2024-10-01",
        end_date="2025-09-30",
        consumption=5000,
        total_cost=1500.0,
    )
    assert msg["success"], msg
    assert msg["result"]["plausibility"]["warning"] is True
    assert msg["result"]["plausibility"]["pct"] == pytest.approx((5000 - 3650) / 3650 * 100)
    assert msg["result"]["id"] in hass.data[DOMAIN].bills
    msg = await ws("billing", meter_id=meter["id"])
    assert msg["result"]["bills"][0]["comparison"]["plausibility"]["warning"] is True
