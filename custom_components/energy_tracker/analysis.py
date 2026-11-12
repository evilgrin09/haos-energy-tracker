"""High level evaluations on top of the calculation core."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .calc import (
    aggregate,
    billing_forecast,
    billing_periods,
    build_tariff,
    current_period_index,
    summarize,
)
from .store import TrackerError, TrackerStore

MIN_GOOD_DAYS = 90


def _range_summary(store: TrackerStore, meter_id: str, start: date, end: date, today: date) -> dict[str, Any]:
    model = store.model(meter_id)
    buckets = aggregate(model, start, end, "year", today, store.tariffs(meter_id))
    summary = summarize(buckets)
    summary["start"] = start.isoformat()
    summary["end"] = end.isoformat()
    return summary


def data_quality(store: TrackerStore, meter_id: str) -> str:
    """Rate how reliable the calculations for a meter are."""
    model = store.model(meter_id)
    if not model.intervals:
        return "none"
    if model.measured_days < MIN_GOOD_DAYS:
        return "low"
    return "good"


def meter_overview(store: TrackerStore, meter_id: str, today: date) -> dict[str, Any]:
    """Return key figures of a meter."""
    meter = store.meters[meter_id]
    model = store.model(meter_id)
    readings = store.meter_readings(meter_id)
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    prev_year_start = year_start.replace(year=today.year - 1)

    result: dict[str, Any] = {
        "meter": meter,
        "last_reading": readings[-1] if readings else None,
        "readings_count": len(readings),
        "measured_days": model.measured_days,
        "annual_rate": model.annual_rate,
        "measured_annual_rate": model.measured_annual_rate,
        "average_daily": model.average_daily,
        "fallback_annual": model.fallback_annual,
        "quality": data_quality(store, meter_id),
        "month_to_date": _range_summary(store, meter_id, month_start, today, today),
        "month_forecast": _range_summary(store, meter_id, month_start, next_month - timedelta(days=1), today),
        "previous_month": _range_summary(
            store, meter_id, prev_month_start, month_start - timedelta(days=1), today
        ),
        "year_to_date": _range_summary(store, meter_id, year_start, today, today),
        "year_forecast": _range_summary(store, meter_id, year_start, year_end, today),
        "previous_year": _range_summary(
            store, meter_id, prev_year_start, year_start - timedelta(days=1), today
        ),
        "contract": None,
        "billing": None,
    }
    contract = store.active_contract(meter_id, today)
    if contract:
        result["contract"] = contract
        result["billing"] = contract_billing(store, contract["id"], today)["selected"]
    return result


def overview(store: TrackerStore, today: date) -> list[dict[str, Any]]:
    """Return the overview for all meters."""
    return [
        meter_overview(store, meter_id, today)
        for meter_id in sorted(store.meters, key=lambda m: str(store.meters[m].get("name", "")).lower())
    ]


def statistics(
    store: TrackerStore,
    meter_id: str,
    start: date,
    end: date,
    granularity: str,
    today: date,
    compare_start: date | None = None,
    compare_end: date | None = None,
) -> dict[str, Any]:
    """Return aggregated consumption, optionally with a comparison range."""
    if meter_id not in store.meters:
        raise TrackerError("not_found", f"Meter {meter_id} not found")
    if end < start:
        raise TrackerError("invalid_dates", "End date is before start date")
    if (end - start).days > 366 * 30:
        raise TrackerError("range_too_large", "Range is too large")
    model = store.model(meter_id)
    tariffs = store.tariffs(meter_id)
    buckets = aggregate(model, start, end, granularity, today, tariffs)
    result: dict[str, Any] = {
        "meter_id": meter_id,
        "granularity": granularity,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "buckets": buckets,
        "summary": summarize(buckets),
        "average_daily": model.average_daily,
        "first_reading": model.first_day.isoformat() if model.first_day else None,
        "last_reading": model.last_day.isoformat() if model.last_day else None,
        "compare": None,
    }
    if compare_start and compare_end:
        if compare_end < compare_start:
            raise TrackerError("invalid_dates", "End date is before start date")
        compare_buckets = aggregate(model, compare_start, compare_end, granularity, today, tariffs)
        result["compare"] = {
            "start": compare_start.isoformat(),
            "end": compare_end.isoformat(),
            "buckets": compare_buckets,
            "summary": summarize(compare_buckets),
        }
    return result


def contract_billing(
    store: TrackerStore, contract_id: str, today: date, period_index: int | None = None
) -> dict[str, Any]:
    """Return billing periods of a contract and the forecast of one period."""
    contract = store.contracts.get(contract_id)
    if contract is None:
        raise TrackerError("not_found", f"Contract {contract_id} not found")
    tariff = build_tariff(contract)
    model = store.model(contract["meter_id"])
    periods = billing_periods(tariff, today)
    current = current_period_index(periods, today)
    if period_index is None or not 0 <= period_index < len(periods):
        period_index = current
    return {
        "contract": contract,
        "periods": [
            {"index": i, "start": s.isoformat(), "end": e.isoformat()} for i, (s, e) in enumerate(periods)
        ],
        "current_index": current,
        "selected_index": period_index,
        "selected": billing_forecast(model, tariff, periods[period_index], today),
    }
