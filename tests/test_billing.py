"""Tests for billing periods, tariffs, advance payments, bills and forecast."""

from datetime import date
from pathlib import Path

import pytest

from custom_components.energy_tracker.calc import (
    FORECAST_AVERAGE,
    PROFILES,
    ConsumptionModel,
    Reading,
    Tariff,
    bill_result,
    billing_date,
    billing_forecast,
    billing_period_for,
    billing_periods,
    build_model,
    build_tariff,
    compare_bill,
    payment_schedule,
    period_index,
    period_label,
)
from custom_components.energy_tracker.importer import parse_csv
from custom_components.energy_tracker.store import migrate

FLAT = PROFILES["flat"]
FIXTURES = Path(__file__).parent / "fixtures" / "energy_tracker_ios"


def _flat_model(per_day: float, start: date, end: date) -> ConsumptionModel:
    """Model with exactly ``per_day`` measured consumption on every day."""
    days = (end - start).days
    return ConsumptionModel([Reading(start, 1000.0), Reading(end, 1000.0 + per_day * days)], FLAT)


# ------------------------------------------------------------ billing periods


def test_billing_periods_by_billing_date() -> None:
    """Periods run from the day after the billing date to the billing date."""
    assert billing_period_for(date(2025, 9, 30), 30, 9) == (date(2024, 10, 1), date(2025, 9, 30))
    assert billing_period_for(date(2025, 10, 1), 30, 9) == (date(2025, 10, 1), date(2026, 9, 30))
    assert billing_period_for(date(2026, 1, 15), 31, 12) == (date(2026, 1, 1), date(2026, 12, 31))
    # 29.02. is clamped in other years
    assert billing_period_for(date(2025, 3, 10), 29, 2) == (date(2025, 3, 1), date(2026, 2, 28))
    assert billing_date(2028, 29, 2) == date(2028, 2, 29)

    periods = billing_periods(date(2024, 1, 2), date(2026, 11, 17), 30, 9)
    assert [period_label(s, e) for s, e in periods] == ["2023/24", "2024/25", "2025/26", "2026/27"]
    assert periods[0] == (date(2023, 10, 1), date(2024, 9, 30))
    assert period_index(periods, date(2026, 11, 17)) == 3
    assert period_label(date(2026, 1, 1), date(2026, 12, 31)) == "2026"


def test_period_independent_of_contract_start() -> None:
    """A contract starting mid-period does not shift the billing period."""
    model = _flat_model(10, date(2025, 1, 1), date(2025, 12, 31))
    tariff = Tariff("c", date(2025, 3, 15), None, unit_price=0.5)
    result = billing_forecast(model, [tariff], billing_period_for(date(2025, 6, 1), 30, 9), date(2026, 1, 1))
    assert (result["start"], result["end"], result["label"]) == ("2024-10-01", "2025-09-30", "2024/25")
    # 15.03.-30.09.2025 = 200 days with tariff out of 365
    assert result["cost_coverage"] == pytest.approx(200 / 365)
    assert result["total_cost"] == pytest.approx(200 * 10 * 0.5)


# ---------------------------------------------------- several tariffs


def test_tariff_change_within_period() -> None:
    """Price change and change of provider are applied day by day."""
    model = _flat_model(10, date(2024, 9, 30), date(2025, 9, 30))
    old = Tariff("a", date(2023, 1, 1), date(2025, 3, 31), unit_price=0.30, base_price=12.0, provider="Alt")
    new = Tariff("b", date(2025, 4, 1), None, unit_price=0.40, base_price=6.0, provider="Neu")
    result = billing_forecast(model, [new, old], (date(2024, 10, 1), date(2025, 9, 30)), date(2025, 10, 1))
    # 182 days old tariff (01.10.-31.03.), 183 days new tariff
    assert [(s["provider"], s["days"]) for s in result["segments"]] == [("Alt", 182), ("Neu", 183)]
    assert result["energy_cost"] == pytest.approx(182 * 10 * 0.30 + 183 * 10 * 0.40)
    assert result["base_cost"] == pytest.approx(12 * 12 / 365 * 182 + 6 * 12 / 365 * 183)
    assert result["segments"][0]["energy_cost"] == pytest.approx(182 * 3.0)
    assert result["cost_coverage"] == pytest.approx(1.0)


def test_conversion_factor_per_tariff() -> None:
    """Gas in m³ is converted with the factor of the tariff valid on each day."""
    model = _flat_model(2, date(2024, 12, 31), date(2025, 12, 31))
    t1 = Tariff("a", date(2025, 1, 1), date(2025, 6, 30), unit_price=0.1, conversion_factor=10.0)
    t2 = Tariff("b", date(2025, 7, 1), None, unit_price=0.1, conversion_factor=11.0)
    result = billing_forecast(model, [t1, t2], (date(2025, 1, 1), date(2025, 12, 31)), date(2026, 1, 1))
    assert result["consumption_billing_unit"] == pytest.approx(181 * 20 + 184 * 22)
    assert result["energy_cost"] == pytest.approx((181 * 20 + 184 * 22) * 0.1)


# ------------------------------------------------------------ advance payments


def test_twelve_payments() -> None:
    """12 payments on the payment day, starting with the first payment."""
    tariff = Tariff(
        "c", date(2025, 10, 1), None, advance_payment=80, payment_day=15, first_payment=date(2025, 10, 15)
    )
    schedule = payment_schedule(tariff, date(2026, 9, 30), 9)
    assert len(schedule) == 12
    assert schedule[0] == (date(2025, 10, 15), 80)
    assert schedule[-1] == (date(2026, 9, 15), 80)


def test_eleven_payments_skip_billing_month() -> None:
    """With 11 payments there is none in the month of the billing date."""
    tariff = Tariff("c", date(2025, 10, 1), None, advance_payment=100, payments_per_year=11)
    schedule = payment_schedule(tariff, date(2026, 9, 30), 9)
    assert len(schedule) == 11
    assert all(day.month != 9 for day, _ in schedule)
    model = _flat_model(10, date(2025, 9, 30), date(2026, 9, 30))
    result = billing_forecast(model, [tariff], (date(2025, 10, 1), date(2026, 9, 30)), date(2026, 3, 20), 9)
    assert result["payments_count"] == 11
    assert result["advance_total"] == pytest.approx(1100)
    assert result["paid_to_date"] == pytest.approx(600)  # Oct-Mar
    assert result["payments_per_year"] == 11


def test_payment_day_clamped_and_default_start() -> None:
    """Payment day 31 falls on the last day of shorter months; default start is the contract start."""
    tariff = Tariff("c", date(2025, 1, 10), date(2025, 4, 30), advance_payment=50, payment_day=31)
    assert [d for d, _ in payment_schedule(tariff, date(2025, 12, 31), 9)] == [
        date(2025, 1, 31),
        date(2025, 2, 28),
        date(2025, 3, 31),
        date(2025, 4, 30),
    ]
    late = Tariff("c", date(2025, 1, 20), None, advance_payment=50, payment_day=5)
    assert payment_schedule(late, date(2025, 3, 31), 9)[0][0] == date(2025, 2, 5)


def test_advance_change_within_period() -> None:
    """From a given date a new advance amount applies."""
    contract = {
        "id": "c",
        "start_date": "2025-10-01",
        "advance_payment": 80,
        "payment_day": 1,
        "advance_changes": [{"date": "2026-03-01", "amount": 95}],
    }
    tariff = build_tariff(contract)
    model = _flat_model(10, date(2025, 9, 30), date(2026, 9, 30))
    result = billing_forecast(model, [tariff], (date(2025, 10, 1), date(2026, 9, 30)), date(2026, 4, 15))
    amounts = [p["amount"] for p in result["payments"]]
    assert amounts == [80] * 5 + [95] * 7
    assert result["advance_total"] == pytest.approx(5 * 80 + 7 * 95)
    assert result["paid_to_date"] == pytest.approx(5 * 80 + 2 * 95)
    # a "new advance from" of a bill is an advance change, the contract wins on the same day
    tariff = build_tariff(contract, [(date(2026, 3, 1), 90.0), (date(2026, 6, 1), 70.0)])
    assert tariff.advance_changes == [(date(2026, 3, 1), 95.0), (date(2026, 6, 1), 70.0)]


# ------------------------------------------------------------ interpolation


def test_reading_interpolated_to_billing_date() -> None:
    """The meter value on the billing date follows the seasonal profile."""
    readings = [Reading(date(2025, 9, 7), 10000.0), Reading(date(2025, 11, 1), 10100.0)]
    model = ConsumptionModel(readings, PROFILES["heating"])
    value = model.reading_at(date(2025, 9, 30), date(2026, 1, 1))
    # September is weighted 0.04, October 0.08: 23 Sept days of 55 days in total
    sept, octo = 23 * 0.04, 31 * 0.08 + 1 * 0.11
    assert value == pytest.approx(10000 + 100 * sept / (sept + octo))
    assert model.reading_at(date(2025, 11, 1), date(2026, 1, 1)) == pytest.approx(10100)
    result = billing_forecast(model, [], (date(2024, 10, 1), date(2025, 9, 30)), date(2026, 1, 1))
    assert result["reading_end"] == pytest.approx(value)
    assert result["reading_end_kind"] == "interpolated"
    assert result["result"] == "no_tariff"


def test_reading_extrapolated_after_last_reading() -> None:
    """After the last reading the value is extrapolated with the forecast."""
    model = _flat_model(10, date(2025, 1, 1), date(2025, 9, 7))
    end = date(2025, 9, 30)
    assert model.reading_at(end, date(2025, 9, 10)) == pytest.approx(
        1000 + 10 * (end - date(2025, 1, 1)).days
    )
    result = billing_forecast(model, [], (date(2024, 10, 1), end), date(2025, 9, 10))
    assert result["reading_end_kind"] == "forecast"
    assert result["reading_start_kind"] == "estimated"


# ---------------------------------------------------------------- bills


def test_compare_bill() -> None:
    """Own calculation versus the bill of the utility."""
    model = _flat_model(10, date(2024, 9, 30), date(2025, 9, 30))
    tariff = Tariff("c", date(2024, 1, 1), None, unit_price=0.3, base_price=10, advance_payment=100)
    own = billing_forecast(model, [tariff], (date(2024, 10, 1), date(2025, 9, 30)), date(2025, 11, 1))
    assert own["finished"]
    assert own["total_cost"] == pytest.approx(3650 * 0.3 + 120)
    bill = {
        "start_date": "2024-10-01",
        "end_date": "2025-09-30",
        "consumption": 3700,
        "total_cost": 1250.0,
        "advances_paid": 1200.0,
    }
    assert bill_result(bill) == pytest.approx(-50)
    comparison = compare_bill(bill, own)
    assert comparison["consumption"]["diff"] == pytest.approx(50)
    assert comparison["consumption"]["pct"] == pytest.approx(50 / 3650 * 100)
    assert comparison["total_cost"]["diff"] == pytest.approx(1250 - own["total_cost"])
    assert comparison["advances"]["diff"] == pytest.approx(0)
    assert comparison["balance"]["own"] == pytest.approx(own["balance"])
    assert comparison["balance"]["diff"] == pytest.approx(-50 - own["balance"])

    # explicit result wins, consumption in billing unit
    bill = {**bill, "balance": 12.5, "consumption": 36500, "consumption_unit": "billing"}
    assert bill_result(bill) == 12.5
    gas = Tariff("c", date(2024, 1, 1), None, unit_price=0.03, conversion_factor=10)
    own = billing_forecast(model, [gas], (date(2024, 10, 1), date(2025, 9, 30)), date(2025, 11, 1))
    assert compare_bill(bill, own)["consumption"]["diff"] == pytest.approx(0)

    # without tariffs only the consumption can be compared
    own = billing_forecast(model, [], (date(2024, 10, 1), date(2025, 9, 30)), date(2025, 11, 1))
    comparison = compare_bill(bill | {"consumption_unit": "meter", "consumption": 3650}, own)
    assert comparison["consumption"]["diff"] == pytest.approx(0)
    assert comparison["total_cost"] is None
    assert comparison["balance"] is None


# --------------------------------------------------------------- forecast


def _fixture_model(name: str, meter_type: str, method: str | None = None):
    text = (FIXTURES / f"Nebenkosten___{name}_-_Za_hlersta_nde.csv").read_text(encoding="utf-8")
    readings = [{"date": row.day.isoformat(), "value": row.value} for row in parse_csv(text).rows]
    meter = {"type": meter_type, "unit": "m³" if meter_type != "electricity" else "kWh"}
    if method:
        meter["forecast_method"] = method
    return build_model(readings, meter)


@pytest.mark.parametrize(
    ("name", "meter_type", "last_year", "tolerance"),
    [
        ("Strom", "electricity", 3975.2, 0.03),
        # mild October 2026 and a lower consumption in the last 365 days
        ("Gas", "gas", 727.06, 0.10),
        ("Wasser", "water", 109.0, 0.03),
    ],
)
def test_forecast_with_real_data(name: str, meter_type: str, last_year: float, tolerance: float) -> None:
    """The forecast for 2026/27 follows the consumption of the last billing year.

    Reference: readings 08.09.2025 - 07.09.2026 as reported to the utility.
    """
    today = date(2026, 11, 17)
    model = _fixture_model(name, meter_type)
    # sanity check of the reference value with the readings
    readings = {r.day: r.value for r in model.readings}
    assert readings[date(2026, 9, 7)] - readings[date(2025, 9, 8)] == pytest.approx(last_year)

    period = billing_period_for(today, 30, 9)
    assert period == (date(2026, 10, 1), date(2027, 9, 30))
    total = billing_forecast(model, [], period, today)["consumption"]["total"]
    assert total == pytest.approx(last_year, rel=tolerance)

    # the annual rate is the measured year up to the last reading (02.11.2026)
    window = sum(v for d, v in model.measured.items() if d > date(2025, 11, 2))
    assert model.annual_rate == pytest.approx(window, rel=0.01)

    # the previous method (average of two years) is still available, but further off
    average = _fixture_model(name, meter_type, FORECAST_AVERAGE)
    old_total = billing_forecast(average, [], period, today)["consumption"]["total"]
    assert abs(total - last_year) < abs(old_total - last_year)

    # the finished billing year 2025/26, interpolated to the billing date 30.09.
    previous = billing_forecast(model, [], (date(2025, 10, 1), date(2026, 9, 30)), today)
    assert previous["consumption"]["total"] == pytest.approx(last_year, rel=0.02)
    assert previous["consumption"]["forecast"] == 0
    assert previous["reading_end_kind"] == "interpolated"


def test_last_year_method_weights_season() -> None:
    """An incomplete year is extrapolated with the seasonal profile."""
    # winter half year only: 600 units Oct-Mar with the heating profile
    start, end = date(2024, 9, 30), date(2025, 3, 31)
    model = ConsumptionModel([Reading(start, 0.0), Reading(end, 600.0)], PROFILES["heating"])
    winter = sum(
        PROFILES["heating"][m - 1] * 12 / 365 * days
        for m, days in ((10, 31), (11, 30), (12, 31), (1, 31), (2, 28), (3, 31))
    )
    assert model.measured_annual_rate == pytest.approx(600 / winter)
    # the winter half year holds ~75 % of the heating: less than a linear extrapolation
    assert model.measured_annual_rate < 600 / 182 * 365


# ---------------------------------------------------------------- migration


def test_migration_from_version_1() -> None:
    """Existing meters get billing date 30.09., contracts keep their values."""
    old = {
        "meters": [{"id": "m", "name": "Strom", "type": "electricity", "unit": "kWh", "profile": "auto"}],
        "readings": [{"id": "r", "meter_id": "m", "date": "2025-01-01", "value": 1.0}],
        "contracts": [
            {
                "id": "c",
                "meter_id": "m",
                "start_date": "2025-03-15",
                "unit_price": 0.3,
                "base_price": 10.0,
                "advance_payment": 80.0,
                "billing_months": 12,
                "provider": "Stadtwerke",
            }
        ],
    }
    data = migrate(1, old)
    meter = data["meters"][0]
    assert (meter["billing_day"], meter["billing_month"], meter["forecast_method"]) == (30, 9, "last_year")
    contract = data["contracts"][0]
    assert contract["unit_price"] == 0.3
    assert contract["advance_payment"] == 80.0
    assert contract["provider"] == "Stadtwerke"
    assert (contract["payments_per_year"], contract["payment_day"]) == (12, 15)
    assert contract["advance_changes"] == []
    assert data["bills"] == []
    assert data["readings"] == old["readings"]
    assert migrate(2, {"meters": []}) == {"meters": []}
