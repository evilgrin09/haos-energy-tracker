"""Tests for the 0.6.1 corrections of the cost history."""

from datetime import date
from pathlib import Path

import pytest

from custom_components.energy_tracker.calc import (
    PROFILES,
    ConsumptionModel,
    Reading,
    build_model,
    build_tariff,
)
from custom_components.energy_tracker.costs import (
    MAX_EDGE_GAP_DAYS,
    bill_days,
    calendar_years,
    meter_cost_history,
    period_costs,
    sum_years,
)
from custom_components.energy_tracker.importer import parse_csv
from custom_components.energy_tracker.store import migrate

FLAT = PROFILES["flat"]
FIXTURES = Path(__file__).parent / "fixtures" / "energy_tracker_ios"
TODAY = date(2026, 11, 17)


def _gas_model() -> ConsumptionModel:
    text = (FIXTURES / "Nebenkosten___Gas_-_Za_hlersta_nde.csv").read_text(encoding="utf-8")
    readings = [{"date": r.day.isoformat(), "value": r.value} for r in parse_csv(text).rows]
    return build_model(readings, {"type": "gas", "unit": "m³"})


def _gas_tariffs():
    return [
        build_tariff(
            {
                "id": "c",
                "start_date": "2023-01-01",
                "unit_price": 0.12,
                "base_price": 14.0,
                "conversion_factor": 10.3,
                "price_changes": [{"date": "2025-01-01", "unit_price": 0.11, "conversion_factor": 10.45}],
            }
        )
    ]


def test_first_reading_on_january_1st_keeps_year_complete() -> None:
    """Gas fixture: first reading 01.01.2024, so only 01.01. itself has no data."""
    model = _gas_model()
    assert model.first_day == date(2024, 1, 1)
    years = meter_cost_history(
        model,
        _gas_tariffs(),
        [],
        calendar_years(date(2024, 1, 1), TODAY),
        TODAY,
        "m³",
        9,
        "calendar",
    )
    by_label = {y["label"]: y for y in years}
    y2024 = by_label["2024"]
    assert y2024["status"] == "complete"
    assert y2024["estimated_days"] == 1
    assert y2024["avg_price"] is not None
    assert y2024["cost_coverage"] == 1
    # the estimate is the average of the neighbouring days 02.-08.01.2024
    neighbours = [model.day(date(2024, 1, d), TODAY)[0] for d in range(2, 9)]
    measured_rest = sum(v for d, v in model.measured.items() if d.year == 2024)
    assert y2024["consumption"] == pytest.approx(measured_rest + sum(neighbours) / 7)
    y2025 = by_label["2025"]
    assert y2025["estimated_days"] == 0
    assert y2025["change_pct"] is not None
    assert y2025["change"] == pytest.approx(y2025["total_cost"] - y2024["total_cost"])


def _model_from(first: date) -> ConsumptionModel:
    return ConsumptionModel(
        [Reading(first, 0.0), Reading(date(2025, 12, 31), 10 * (date(2025, 12, 31) - first).days)], FLAT
    )


@pytest.mark.parametrize(
    ("first_reading", "status", "estimated"),
    [
        (date(2024, 12, 31), "complete", 0),
        (date(2025, 1, 1), "complete", 1),  # 01.01. missing
        (date(2025, 1, MAX_EDGE_GAP_DAYS), "complete", MAX_EDGE_GAP_DAYS),
        (date(2025, 1, MAX_EDGE_GAP_DAYS + 1), "partial", 0),
    ],
)
def test_edge_gap_limit(first_reading: date, status: str, estimated: int) -> None:
    """At most 7 missing days at the beginning are estimated."""
    model = _model_from(first_reading)
    tariffs = [build_tariff({"id": "c", "start_date": "2020-01-01", "unit_price": 0.5, "base_price": 0.0})]
    years = meter_cost_history(
        model, tariffs, [], [(date(2025, 1, 1), date(2025, 12, 31))], TODAY, "kWh", 9, "calendar"
    )
    assert (years[0]["status"], years[0]["estimated_days"]) == (status, estimated)
    if status == "complete":
        # 10 kWh per day at 0.50 EUR, also on the estimated days
        assert years[0]["total_cost"] == pytest.approx(365 * 5)


def test_edge_gap_tariff_starts_late_and_gap_in_between() -> None:
    """Missing tariff days at the start are estimated, a gap in between is not."""
    model = _model_from(date(2024, 12, 31))
    late = [build_tariff({"id": "c", "start_date": "2025-01-04", "unit_price": 0.5, "base_price": 0.0})]
    year = meter_cost_history(
        model, late, [], [(date(2025, 1, 1), date(2025, 12, 31))], TODAY, "kWh", 9, "calendar"
    )[0]
    assert (year["status"], year["estimated_days"]) == ("complete", 3)
    # consumption of the days without tariff is known and kept
    assert year["consumption"] == pytest.approx(3650)

    gap = [
        build_tariff({"id": "a", "start_date": "2024-01-01", "end_date": "2025-05-31", "unit_price": 0.5}),
        build_tariff({"id": "b", "start_date": "2025-06-03", "unit_price": 0.5}),
    ]
    year = meter_cost_history(
        model, gap, [], [(date(2025, 1, 1), date(2025, 12, 31))], TODAY, "kWh", 9, "calendar"
    )[0]
    assert (year["status"], year["estimated_days"]) == ("partial", 0)


def test_bill_without_base_price_and_tariff_has_unknown_split() -> None:
    """Only the total is known: energy and base cost are None."""
    model = _model_from(date(2023, 12, 31))
    bill = {"id": "b", "start_date": "2024-01-01", "end_date": "2024-12-31", "total_cost": 900.0}
    shares = bill_days(model, [], [bill], TODAY)
    assert not shares[date(2024, 5, 1)].split_known
    year = period_costs(
        model, [], shares, (date(2024, 1, 1), date(2024, 12, 31)), TODAY, date(2024, 1, 1), "kWh"
    )
    assert year["total_cost"] == pytest.approx(900)
    assert year["split_known"] is False
    assert (year["energy_cost"], year["base_cost"]) == (None, None)
    assert year["status"] == "complete"

    # with a base price on the bill the split is known
    shares = bill_days(model, [], [{**bill, "base_price": 12.0}], TODAY)
    year = period_costs(
        model, [], shares, (date(2024, 1, 1), date(2024, 12, 31)), TODAY, date(2024, 1, 1), "kWh"
    )
    assert year["split_known"] is True
    assert year["base_cost"] == pytest.approx(12 * 12 / 365 * 366)
    assert year["energy_cost"] + year["base_cost"] == pytest.approx(900)

    # the sum of several meters is only split if all are split
    known = {**year, "advances": None, "result": None}
    unknown = {**known, "split_known": False, "energy_cost": None, "base_cost": None}
    total = sum_years([("a", [known]), ("b", [unknown])])[0]
    assert total["total_cost"] == pytest.approx(1800)
    assert total["split_known"] is False
    assert total["energy_cost"] is None


def test_migration_to_version_4() -> None:
    """Readings taken from bills are marked with source "bill"."""
    data = {
        "readings": [
            {"id": "a", "date": "2022-09-30", "value": 1.0, "note": "aus Abrechnung"},
            {"id": "b", "date": "2024-01-01", "value": 2.0, "note": ""},
        ]
    }
    readings = migrate(3, data)["readings"]
    assert [r["source"] for r in readings] == ["bill", "manual"]
