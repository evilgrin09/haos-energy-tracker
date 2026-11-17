"""High level evaluations on top of the calculation core."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .calc import (
    DEFAULT_BILLING_DAY,
    DEFAULT_BILLING_MONTH,
    aggregate,
    bill_result,
    billing_forecast,
    billing_period_for,
    billing_periods,
    compare_bill,
    find_tariff,
    parse_date,
    period_index,
    period_label,
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
        "contract": store.active_contract(meter_id, today),
        "billing": None,
        "last_bill": None,
    }
    tariffs = store.tariffs(meter_id)
    if tariffs:
        day, month = billing_date_of(meter)
        result["billing"] = billing_forecast(
            model, tariffs, billing_period_for(today, day, month), today, month
        )
    if bills := store.meter_bills(meter_id):
        result["last_bill"] = bill_details(store, bills[-1], today)
    return result


def billing_date_of(meter: dict[str, Any]) -> tuple[int, int]:
    """Billing date (day, month) of a meter."""
    return (
        int(meter.get("billing_day") or DEFAULT_BILLING_DAY),
        int(meter.get("billing_month") or DEFAULT_BILLING_MONTH),
    )


def meter_periods(store: TrackerStore, meter_id: str, today: date) -> list[tuple[date, date]]:
    """Billing periods of a meter: from the first data up to the current period."""
    day, month = billing_date_of(store.meters[meter_id])
    starts = [today]
    readings = store.meter_readings(meter_id)
    if readings:
        # the first reading only marks the start of the measurement
        starts.append(parse_date(readings[0]["date"]) + timedelta(days=1))
    starts.extend(parse_date(c["start_date"]) for c in store.meter_contracts(meter_id))
    starts.extend(parse_date(b["start_date"]) for b in store.meter_bills(meter_id))
    ends = [today] + [parse_date(b["end_date"]) for b in store.meter_bills(meter_id)]
    return billing_periods(min(starts), max(ends), day, month)


def tariff_gaps(store: TrackerStore, meter_id: str, today: date) -> dict[str, Any]:
    """Days without tariff: gaps between contracts and the time before the first one."""
    contracts = store.meter_contracts(meter_id)
    readings = store.meter_readings(meter_id)
    result: dict[str, Any] = {"gaps": [], "before": None, "after": None}
    if not contracts:
        return result
    tariffs = store.tariffs(meter_id)
    first = min(t.start for t in tariffs)
    open_end = any(t.end is None for t in tariffs)
    last = None if open_end else max(t.end for t in tariffs if t.end)
    # gaps between the first and the last contract
    gap_start = None
    end = last or max(t.start for t in tariffs)
    day = first
    while day <= end:
        if find_tariff(tariffs, day) is None:
            gap_start = gap_start or day
        elif gap_start:
            result["gaps"].append(
                {"start": gap_start.isoformat(), "end": (day - timedelta(days=1)).isoformat()}
            )
            gap_start = None
        day += timedelta(days=1)
    if readings:
        data_start = parse_date(readings[0]["date"]) + timedelta(days=1)
        if data_start < first:
            result["before"] = {
                "start": data_start.isoformat(),
                "end": (first - timedelta(days=1)).isoformat(),
            }
    if last is not None and last < today:
        result["after"] = {"start": (last + timedelta(days=1)).isoformat(), "end": None}
    return result


def bill_details(store: TrackerStore, bill: dict[str, Any], today: date) -> dict[str, Any]:
    """A bill together with the own calculation of its period."""
    meter_id = bill["meter_id"]
    _day, month = billing_date_of(store.meters[meter_id])
    start = parse_date(bill["start_date"])
    end = parse_date(bill["end_date"])
    own = billing_forecast(store.model(meter_id), store.tariffs(meter_id), (start, end), today, month)
    return {
        "bill": bill,
        "label": period_label(start, end),
        "result": bill_result(bill),
        "own": own,
        "comparison": compare_bill(bill, own),
    }


def meter_billing(
    store: TrackerStore, meter_id: str, today: date, index: int | None = None
) -> dict[str, Any]:
    """Billing periods of a meter and the calculation of one of them."""
    if meter_id not in store.meters:
        raise TrackerError("not_found", f"Meter {meter_id} not found")
    _day, month = billing_date_of(store.meters[meter_id])
    periods = meter_periods(store, meter_id, today)
    current = period_index(periods, today)
    if index is None or not 0 <= index < len(periods):
        index = current
    bills = store.meter_bills(meter_id)

    def bill_for(period: tuple[date, date]) -> dict[str, Any] | None:
        start, end = period
        matching = [b for b in bills if start <= parse_date(b["end_date"]) <= end]
        return matching[-1] if matching else None

    selected = periods[index]
    bill = bill_for(selected)
    return {
        "meter_id": meter_id,
        "periods": [
            {
                "index": i,
                "start": s.isoformat(),
                "end": e.isoformat(),
                "label": period_label(s, e),
                "bill_id": (b["id"] if (b := bill_for((s, e))) else None),
            }
            for i, (s, e) in enumerate(periods)
        ],
        "current_index": current,
        "selected_index": index,
        "selected": billing_forecast(store.model(meter_id), store.tariffs(meter_id), selected, today, month),
        "bill": bill_details(store, bill, today) if bill else None,
        "bills": [bill_details(store, b, today) for b in reversed(bills)],
        "tariff_gaps": tariff_gaps(store, meter_id, today),
    }


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
