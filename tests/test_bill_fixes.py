"""Tests for the 0.6.2 corrections (several bills, bill prices, plausibility)."""

from datetime import date

import pytest

from custom_components.energy_tracker.calc import (
    PROFILES,
    ConsumptionModel,
    Reading,
    bill_plausibility,
    billing_forecast,
    build_tariff,
)
from custom_components.energy_tracker.costs import (
    MAX_BILL_EXTRAPOLATION_DAYS,
    bill_days,
    meter_cost_history,
)

FLAT = PROFILES["flat"]
TODAY = date(2026, 11, 17)
YEAR_25_26 = (date(2025, 10, 1), date(2026, 9, 30))


def _model(per_day: float = 10.0) -> ConsumptionModel:
    """Exactly ``per_day`` on every day from 2024 to 2026."""
    start, end = date(2023, 12, 31), date(2026, 11, 10)
    return ConsumptionModel([Reading(start, 0.0), Reading(end, per_day * (end - start).days)], FLAT)


# ------------------------------------------------- several bills in one year


def test_annual_and_final_bill_are_added_up() -> None:
    """Annual bill + final bill (change of supplier) in the same billing year."""
    annual = {
        "id": "a",
        "start_date": "2025-10-01",
        "end_date": "2026-03-31",
        "total_cost": 900.0,
        "advances_paid": 800.0,
    }
    final = {
        "id": "b",
        "start_date": "2026-04-01",
        "end_date": "2026-09-30",
        "total_cost": 700.0,
        "advances_paid": 750.0,
    }
    years = meter_cost_history(_model(), [], [annual, final], [YEAR_25_26], TODAY, "kWh", 9, "billing")
    year = years[0]
    assert year["bill_count"] == 2
    assert year["total_cost"] == pytest.approx(1600)
    assert year["advances"] == pytest.approx(1550)
    assert year["result"] == pytest.approx(-100 + 50)
    assert year["result_source"] == "bill"
    assert year["result_incomplete"] is False
    assert year["status"] == "complete"


def test_missing_payments_make_the_result_incomplete() -> None:
    """Without the payments of one bill the result only contains the other one."""
    annual = {
        "id": "a",
        "start_date": "2025-10-01",
        "end_date": "2026-03-31",
        "total_cost": 900.0,
        "advances_paid": 800.0,
    }
    final = {"id": "b", "start_date": "2026-04-01", "end_date": "2026-09-30", "total_cost": 700.0}
    year = meter_cost_history(_model(), [], [annual, final], [YEAR_25_26], TODAY, "kWh", 9, "billing")[0]
    assert year["advances"] == pytest.approx(800)
    assert year["result"] == pytest.approx(-100)
    assert year["result_incomplete"] is True

    # a bill with an explicit result counts even without payments
    final["balance"] = 25.0
    year = meter_cost_history(_model(), [], [annual, final], [YEAR_25_26], TODAY, "kWh", 9, "billing")[0]
    assert year["result"] == pytest.approx(-75)
    assert year["result_incomplete"] is True  # payments of the final bill unknown


# --------------------------------------- days between bill and billing date


def test_days_up_to_billing_date_get_the_bill_price() -> None:
    """Bill 09.09.2025-07.09.2026, billing year until 30.09.2026, no tariff."""
    bill = {
        "id": "b",
        "start_date": "2025-09-09",
        "end_date": "2026-09-07",
        "consumption": 3640,  # 364 days * 10
        "total_cost": 1456.0,  # 0.40 EUR per unit including base price
    }
    model = _model()
    years = meter_cost_history(model, [], [bill], [YEAR_25_26], TODAY, "kWh", 9, "billing")
    year = years[0]
    assert year["status"] == "complete"
    assert year["source"] == "bill_extrapolated"
    assert year["extrapolated_days"] == 23  # 08.-30.09.2026
    bill_part = 1456.0 * (364 - 22) / 364  # 01.10.2025-07.09.2026 of the bill
    assert year["total_cost"] == pytest.approx(bill_part + 23 * 10 * 0.40)
    assert year["avg_price"] == pytest.approx(40.0)
    assert year["split_known"] is False

    # the days before the bill (01.-08.09.2025) belong to 2024/25 and are valued as well
    shares = bill_days(model, [], [bill], TODAY)
    assert shares[date(2025, 9, 8)].extrapolated
    assert shares[date(2025, 9, 8)].total_cost == pytest.approx(4.0)
    first = date(2025, 9, 9).toordinal() - MAX_BILL_EXTRAPOLATION_DAYS
    assert date.fromordinal(first) in shares
    assert date.fromordinal(first - 1) not in shares
    assert date(2026, 9, 7).toordinal() + MAX_BILL_EXTRAPOLATION_DAYS == max(d.toordinal() for d in shares)


def test_bill_prices_with_unit_and_base_price() -> None:
    """With unit and base price on the bill these are used for the extra days."""
    bill = {
        "id": "b",
        "start_date": "2025-09-09",
        "end_date": "2026-09-07",
        "total_cost": 1500.0,
        "unit_price": 0.30,
        "base_price": 12.0,
    }
    shares = bill_days(_model(), [], [bill], TODAY)
    day = shares[date(2026, 9, 20)]
    assert day.extrapolated
    assert day.energy_cost == pytest.approx(3.0)
    assert day.base_cost == pytest.approx(12 * 12 / 365)

    # a tariff on these days has priority over the bill prices
    tariff = build_tariff({"id": "c", "start_date": "2026-09-15", "unit_price": 0.5})
    shares = bill_days(_model(), [tariff], [bill], TODAY)
    assert date(2026, 9, 14) in shares
    assert date(2026, 9, 15) not in shares


def test_nearest_bill_wins_between_two_bills() -> None:
    """A gap between two bills takes the prices of the nearer bill."""
    first = {"id": "a", "start_date": "2025-01-01", "end_date": "2025-06-30", "total_cost": 362.0}
    second = {"id": "b", "start_date": "2025-07-11", "end_date": "2025-12-31", "total_cost": 1000.0}
    shares = bill_days(_model(), [], [first, second], TODAY)
    assert shares[date(2025, 7, 2)].bill_id == "a"
    assert shares[date(2025, 7, 9)].bill_id == "b"
    assert shares[date(2025, 7, 2)].total_cost == pytest.approx(362.0 / 1810 * 10)


# ------------------------------------------------------------ plausibility


def _own(start: date, end: date, model: ConsumptionModel | None = None) -> dict:
    return billing_forecast(model or _model(), [], (start, end), TODAY)


@pytest.mark.parametrize(
    ("consumption", "unit", "factor", "warning"),
    [
        (3650, "meter", None, False),
        (4560, "meter", None, False),  # +24.9 %
        (4600, "meter", None, True),  # +26 %
        (2700, "meter", None, True),  # -26 %
        (36500 * 1.3, "billing", 10.0, True),
        (36500, "billing", 10.0, False),
    ],
)
def test_plausibility(consumption: float, unit: str, factor: float | None, warning: bool) -> None:
    """More than 25 % deviation from the own readings is reported."""
    own = _own(date(2025, 1, 1), date(2025, 12, 31))
    bill = {"consumption": consumption, "consumption_unit": unit, "conversion_factor": factor}
    result = bill_plausibility(bill, own)
    assert result["checked"] is True
    assert result["warning"] is warning
    assert result["own"] == pytest.approx(3650)


def test_plausibility_needs_readings() -> None:
    """Without enough own readings in the period there is no check."""
    model = ConsumptionModel([Reading(date(2025, 11, 1), 0.0), Reading(date(2025, 12, 31), 600.0)], FLAT)
    own = _own(date(2025, 1, 1), date(2025, 12, 31), model)
    result = bill_plausibility({"consumption": 99999}, own)
    assert result["checked"] is False
    assert result["warning"] is False
    assert bill_plausibility({}, _own(date(2025, 1, 1), date(2025, 12, 31)))["checked"] is False
