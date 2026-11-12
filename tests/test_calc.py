"""Tests of the calculation core."""

from datetime import date

import pytest

from custom_components.energy_tracker.calc import (
    ESTIMATED,
    FORECAST,
    MEASURED,
    PROFILES,
    ConsumptionModel,
    Reading,
    Tariff,
    add_months,
    aggregate,
    billing_forecast,
    billing_periods,
    current_period_index,
    summarize,
)

FLAT = PROFILES["flat"]


def test_profiles_sum_to_one() -> None:
    """All profiles distribute exactly one year."""
    for factors in PROFILES.values():
        assert sum(factors) == pytest.approx(1.0)


def test_add_months_clamps() -> None:
    """Adding months clamps to the end of the month."""
    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
    assert add_months(date(2024, 11, 15), 3) == date(2025, 2, 15)


def test_linear_interpolation() -> None:
    """Consumption is spread evenly over the days of an interval."""
    model = ConsumptionModel([Reading(date(2025, 3, 1), 100), Reading(date(2025, 3, 11), 200)], FLAT)
    series = model.series(date(2025, 3, 2), date(2025, 3, 11), date(2025, 12, 31))
    assert [kind for _, _, kind in series] == [MEASURED] * 10
    assert all(value == pytest.approx(10) for _, value, _ in series)
    assert model.annual_rate == pytest.approx(10 * 365)


def test_seasonal_weighting() -> None:
    """With the heating profile winter days get more consumption."""
    model = ConsumptionModel(
        [Reading(date(2024, 12, 31), 0), Reading(date(2025, 12, 31), 1000)],
        PROFILES["heating"],
    )
    jan = summarize(aggregate(model, date(2025, 1, 1), date(2025, 1, 31), "month", date(2026, 1, 1)))
    jul = summarize(aggregate(model, date(2025, 7, 1), date(2025, 7, 31), "month", date(2026, 1, 1)))
    heating = PROFILES["heating"]
    year_weight = sum(
        f * days for f, days in zip(heating, (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31), strict=True)
    )
    assert jan["total"] == pytest.approx(1000 * 0.17 * 31 / year_weight)
    assert jul["total"] == pytest.approx(1000 * 0.02 * 31 / year_weight)
    assert jan["measured"] == pytest.approx(jan["total"])
    assert jan["total"] > 7 * jul["total"]


def test_fallback_without_readings() -> None:
    """Without readings the reference consumption is used."""
    model = ConsumptionModel([], FLAT, fallback_annual=3650)
    year = summarize(aggregate(model, date(2025, 1, 1), date(2025, 12, 31), "year", date(2025, 6, 30)))
    assert year["total"] == pytest.approx(3650)
    assert year["measured"] == 0
    assert year["estimated"] > 0
    assert year["forecast"] > 0


def test_blending_with_little_data() -> None:
    """Short measurements are blended with the reference value."""
    readings = [Reading(date(2025, 1, 1), 0), Reading(date(2025, 1, 31), 300)]
    model = ConsumptionModel(readings, FLAT, fallback_annual=1000)
    measured_rate = 300 / (30 / 365)
    expected = (measured_rate * 30 + 1000 * 30) / 60
    assert model.measured_annual_rate == pytest.approx(measured_rate)
    assert model.annual_rate == pytest.approx(expected)


def test_estimate_and_forecast_flags() -> None:
    """Days without readings are estimated (past) or forecast (future)."""
    model = ConsumptionModel([Reading(date(2025, 1, 1), 0), Reading(date(2025, 1, 11), 10)], FLAT)
    today = date(2025, 1, 20)
    assert model.day(date(2025, 1, 5), today)[1] == MEASURED
    assert model.day(date(2025, 1, 15), today)[1] == ESTIMATED
    assert model.day(date(2025, 1, 25), today)[1] == FORECAST
    assert model.day(date(2024, 12, 15), today)[1] == ESTIMATED


def test_meter_replacement() -> None:
    """A reset starts a new meter without negative consumption."""
    readings = [
        Reading(date(2025, 1, 1), 1000),
        Reading(date(2025, 1, 11), 1100),
        Reading(date(2025, 1, 11), 0, reset=True),
        Reading(date(2025, 1, 21), 100),
    ]
    model = ConsumptionModel(readings, FLAT)
    assert len(model.intervals) == 2
    total = summarize(aggregate(model, date(2025, 1, 2), date(2025, 1, 21), "month", date(2025, 2, 1)))
    assert total["total"] == pytest.approx(200)
    assert total["measured"] == pytest.approx(200)


def test_week_buckets() -> None:
    """Weeks start on Monday and are clipped to the range."""
    model = ConsumptionModel([], FLAT, fallback_annual=365)
    buckets = aggregate(model, date(2025, 1, 1), date(2025, 1, 31), "week", date(2025, 1, 1))
    assert buckets[0]["key"] == "2024-12-30"
    assert buckets[0]["start"] == "2025-01-01"
    assert buckets[0]["days"] == 5
    assert sum(b["days"] for b in buckets) == 31


def test_costs_in_buckets() -> None:
    """Costs are calculated with the valid tariff."""
    model = ConsumptionModel([], FLAT, fallback_annual=3650)
    tariff = Tariff("c", date(2025, 1, 1), None, unit_price=0.5, base_price=0)
    buckets = aggregate(model, date(2024, 12, 31), date(2025, 1, 1), "day", date(2025, 1, 1), [tariff])
    assert buckets[0]["cost"] is None
    assert buckets[1]["cost"] == pytest.approx(10 * 0.5 * 365 / 365, rel=0.02)


def test_billing_forecast_additional_payment() -> None:
    """Half a year measured, rest extrapolated, advance payments too low."""
    model = ConsumptionModel([Reading(date(2024, 12, 31), 0), Reading(date(2025, 6, 30), 1000)], FLAT)
    tariff = Tariff("c", date(2025, 1, 1), None, unit_price=0.3, base_price=10, advance_payment=50)
    periods = billing_periods(tariff, date(2025, 6, 30))
    assert periods[0] == (date(2025, 1, 1), date(2025, 12, 31))
    result = billing_forecast(model, tariff, periods[0], date(2025, 6, 30))
    total = 1000 + 1000 / 181 * 184  # 181 measured days, 184 extrapolated
    cost = total * 0.3 + 120
    assert result["consumption"]["total"] == pytest.approx(total)
    assert result["consumption"]["measured"] == pytest.approx(1000)
    assert result["consumption"]["forecast"] == pytest.approx(total - 1000)
    assert result["total_cost"] == pytest.approx(cost)
    assert result["advance_total"] == pytest.approx(600)
    assert result["paid_to_date"] == pytest.approx(300)
    assert result["balance"] == pytest.approx(600 - cost)
    assert result["result"] == "additional_payment"
    assert result["recommended_advance"] == pytest.approx(cost / 12)


def test_billing_forecast_conversion_factor_refund() -> None:
    """Gas in m³ is converted to kWh for billing."""
    model = ConsumptionModel([], FLAT, fallback_annual=1000)
    tariff = Tariff("c", date(2025, 1, 1), None, unit_price=0.1, advance_payment=100, conversion_factor=10)
    result = billing_forecast(model, tariff, (date(2025, 1, 1), date(2025, 12, 31)), date(2025, 1, 1))
    assert result["consumption_billing_unit"] == pytest.approx(10000)
    assert result["total_cost"] == pytest.approx(1000)
    assert result["balance"] == pytest.approx(200)
    assert result["result"] == "refund"


def test_billing_periods_with_end() -> None:
    """Periods end with the contract."""
    tariff = Tariff("c", date(2023, 4, 1), date(2025, 9, 30))
    periods = billing_periods(tariff, date(2025, 1, 1))
    assert periods == [
        (date(2023, 4, 1), date(2024, 3, 31)),
        (date(2024, 4, 1), date(2025, 3, 31)),
        (date(2025, 4, 1), date(2025, 9, 30)),
    ]
    assert current_period_index(periods, date(2025, 1, 1)) == 1
    assert current_period_index(periods, date(2026, 1, 1)) == 2


def test_open_ended_periods_include_next() -> None:
    """Open ended contracts list periods up to the next one."""
    tariff = Tariff("c", date(2022, 1, 1), None)
    periods = billing_periods(tariff, date(2025, 3, 1))
    assert periods[-2] == (date(2025, 1, 1), date(2025, 12, 31))
    assert periods[-1] == (date(2026, 1, 1), date(2026, 12, 31))
