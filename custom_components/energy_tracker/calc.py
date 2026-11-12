"""Calculation core of Energy Tracker.

This module is intentionally free of Home Assistant imports so that it can be
unit tested in isolation.

Concepts
--------
* A *reading* is the meter value at the end of a given day.
* Consumption between two consecutive readings is distributed over the days in
  between, weighted by a seasonal *profile* (e.g. gas is mostly used in winter).
* For days that are not covered by two readings (before the first reading,
  after the last reading, gaps caused by a meter replacement) consumption is
  *estimated* from the average consumption rate.  If there is not enough data,
  that rate is blended with a reference annual consumption (user supplied or a
  typical default value for the meter type).
* Days after "today" are flagged as *forecast*.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import pairwise
from typing import Any

MEASURED = "measured"
ESTIMATED = "estimated"
FORECAST = "forecast"

GRANULARITIES = ("day", "week", "month", "year")

# Monthly share of annual consumption (Jan..Dec), each profile sums up to 1.
PROFILES: dict[str, tuple[float, ...]] = {
    "flat": tuple([1 / 12] * 12),
    # Typical household heating curve (gas / district heating / heat pump).
    "heating": (
        0.17,
        0.15,
        0.13,
        0.09,
        0.05,
        0.03,
        0.02,
        0.02,
        0.04,
        0.08,
        0.11,
        0.11,
    ),
    # Roughly follows the German standard load profile H0 for households.
    "electricity": (
        0.095,
        0.085,
        0.088,
        0.080,
        0.078,
        0.072,
        0.073,
        0.075,
        0.076,
        0.087,
        0.092,
        0.099,
    ),
}

PROFILE_BY_TYPE = {
    "electricity": "electricity",
    "gas": "heating",
    "heat": "heating",
    "oil": "heating",
    "water": "flat",
    "other": "flat",
}

# Reference annual consumption used while there is not enough data.
# Keyed by (meter type, unit).  Values are typical for a 2-3 person household.
DEFAULT_ANNUAL: dict[tuple[str, str], float] = {
    ("electricity", "kWh"): 2500.0,
    ("gas", "m³"): 1200.0,
    ("gas", "kWh"): 12000.0,
    ("heat", "kWh"): 9000.0,
    ("heat", "MWh"): 9.0,
    ("water", "m³"): 90.0,
    ("water", "L"): 90000.0,
    ("oil", "L"): 1500.0,
}

# Weight (in days) of the reference value when blending with measured data.
PRIOR_DAYS = 30
# Measured data older than this (relative to the last reading) is ignored when
# calculating the average consumption rate.
RATE_WINDOW_DAYS = 730


def resolve_profile(meter_type: str, profile: str | None) -> tuple[float, ...]:
    """Return the monthly factors for a meter."""
    if profile and profile != "auto" and profile in PROFILES:
        return PROFILES[profile]
    return PROFILES[PROFILE_BY_TYPE.get(meter_type, "flat")]


def default_annual(meter_type: str, unit: str) -> float:
    """Return a typical annual consumption for the meter type."""
    return DEFAULT_ANNUAL.get((meter_type, unit), 0.0)


def day_weight(d: date, factors: tuple[float, ...]) -> float:
    """Approximate share of a whole year's consumption that falls on day ``d``.

    The monthly factors are interpreted as relative intensity, so every day of
    a month gets the same weight and the "flat" profile is exactly uniform
    per day (1/365).
    """
    return factors[d.month - 1] * 12 / 365


def add_months(d: date, months: int) -> date:
    """Add months to a date, clamping the day to the target month."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def daterange(start: date, end: date) -> Iterable[date]:
    """Iterate over all days from start to end (both inclusive)."""
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def parse_date(value: str | date) -> date:
    """Parse an ISO date."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


@dataclass(slots=True)
class Reading:
    """A meter reading at the end of ``day``."""

    day: date
    value: float
    reset: bool = False  # True: first reading of a new/replaced meter


@dataclass(slots=True)
class Interval:
    """Consumption between two readings (start exclusive, end inclusive)."""

    start: date
    end: date
    delta: float


@dataclass
class ConsumptionModel:
    """Daily consumption model of a single meter."""

    readings: list[Reading]
    factors: tuple[float, ...] = PROFILES["flat"]
    fallback_annual: float = 0.0
    intervals: list[Interval] = field(init=False, default_factory=list)
    measured: dict[date, float] = field(init=False, default_factory=dict)
    annual_rate: float = field(init=False, default=0.0)
    measured_annual_rate: float | None = field(init=False, default=None)
    measured_days: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.readings = sorted(self.readings, key=lambda r: (r.day, r.reset))
        self.intervals = build_intervals(self.readings)
        for interval in self.intervals:
            days = list(daterange(interval.start + timedelta(days=1), interval.end))
            total_weight = sum(day_weight(d, self.factors) for d in days)
            for d in days:
                self.measured[d] = interval.delta * day_weight(d, self.factors) / total_weight
        self.measured_days = len(self.measured)
        self._calculate_rate()

    def _calculate_rate(self) -> None:
        """Calculate the annualised consumption rate used for estimates."""
        if not self.intervals:
            self.annual_rate = self.fallback_annual
            return
        last = self.intervals[-1].end
        window_start = last - timedelta(days=RATE_WINDOW_DAYS)
        delta = 0.0
        weight = 0.0
        days = 0
        for interval in self.intervals:
            if interval.end <= window_start:
                continue
            delta += interval.delta
            for d in daterange(interval.start + timedelta(days=1), interval.end):
                weight += day_weight(d, self.factors)
                days += 1
        if weight <= 0:
            self.annual_rate = self.fallback_annual
            return
        measured_rate = delta / weight
        self.measured_annual_rate = measured_rate
        prior = PRIOR_DAYS if (self.fallback_annual > 0 and days < 365) else 0
        self.annual_rate = (measured_rate * days + self.fallback_annual * prior) / (days + prior)

    @property
    def first_day(self) -> date | None:
        """Day of the first reading."""
        return self.readings[0].day if self.readings else None

    @property
    def last_day(self) -> date | None:
        """Day of the last reading."""
        return self.readings[-1].day if self.readings else None

    @property
    def average_daily(self) -> float:
        """Average consumption per day (annual rate / 365)."""
        return self.annual_rate / 365.0

    def day(self, d: date, today: date) -> tuple[float, str]:
        """Return consumption and its kind for a single day."""
        if d in self.measured:
            return self.measured[d], MEASURED
        value = self.annual_rate * day_weight(d, self.factors)
        return value, (FORECAST if d > today else ESTIMATED)

    def series(self, start: date, end: date, today: date) -> list[tuple[date, float, str]]:
        """Return daily consumption for a date range."""
        return [(d, *self.day(d, today)) for d in daterange(start, end)]


def build_intervals(readings: list[Reading]) -> list[Interval]:
    """Build consumption intervals out of sorted readings.

    A reading flagged ``reset`` starts a new meter; the consumption between the
    previous reading and the reset is unknown and therefore estimated.  A
    decreasing value without reset is treated the same way (implausible data).
    """
    intervals: list[Interval] = []
    for prev, cur in pairwise(readings):
        if cur.reset or cur.day <= prev.day:
            continue
        delta = cur.value - prev.value
        if delta < 0:
            continue
        intervals.append(Interval(prev.day, cur.day, delta))
    return intervals


def bucket_start(d: date, granularity: str) -> date:
    """Return the first day of the bucket containing ``d``."""
    if granularity == "day":
        return d
    if granularity == "week":
        return d - timedelta(days=d.weekday())
    if granularity == "month":
        return d.replace(day=1)
    if granularity == "year":
        return d.replace(month=1, day=1)
    raise ValueError(f"Unknown granularity {granularity}")


def next_bucket(d: date, granularity: str) -> date:
    """Return the first day of the following bucket."""
    if granularity == "day":
        return d + timedelta(days=1)
    if granularity == "week":
        return d + timedelta(days=7)
    if granularity == "month":
        return add_months(d, 1)
    if granularity == "year":
        return d.replace(year=d.year + 1)
    raise ValueError(f"Unknown granularity {granularity}")


@dataclass(slots=True)
class Tariff:
    """Contract / tariff data relevant for calculations."""

    contract_id: str
    start: date
    end: date | None
    unit_price: float = 0.0  # currency per billing unit
    base_price: float = 0.0  # currency per month
    advance_payment: float = 0.0  # currency per month
    conversion_factor: float = 1.0  # billing units per meter unit
    billing_months: int = 12

    def covers(self, d: date) -> bool:
        """Return True if the tariff is valid on ``d``."""
        return self.start <= d and (self.end is None or d <= self.end)

    def day_cost(self, consumption: float) -> float:
        """Cost of one day with the given consumption (incl. base price)."""
        return consumption * self.conversion_factor * self.unit_price + self.base_price * 12 / 365


def find_tariff(tariffs: list[Tariff], d: date) -> Tariff | None:
    """Return the tariff valid on ``d`` (latest start wins)."""
    match = None
    for tariff in tariffs:
        if tariff.covers(d) and (match is None or tariff.start >= match.start):
            match = tariff
    return match


def aggregate(
    model: ConsumptionModel,
    start: date,
    end: date,
    granularity: str,
    today: date,
    tariffs: list[Tariff] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate daily consumption into buckets of the given granularity."""
    buckets: list[dict[str, Any]] = []
    cursor = bucket_start(start, granularity)
    while cursor <= end:
        nxt = next_bucket(cursor, granularity)
        b_start = max(cursor, start)
        b_end = min(nxt - timedelta(days=1), end)
        bucket: dict[str, Any] = {
            "key": cursor.isoformat(),
            "start": b_start.isoformat(),
            "end": b_end.isoformat(),
            "days": (b_end - b_start).days + 1,
            MEASURED: 0.0,
            ESTIMATED: 0.0,
            FORECAST: 0.0,
            "cost": None,
        }
        cost = 0.0
        has_cost = False
        for d, value, kind in model.series(b_start, b_end, today):
            bucket[kind] += value
            if tariffs and (tariff := find_tariff(tariffs, d)):
                cost += tariff.day_cost(value)
                has_cost = True
        bucket["total"] = bucket[MEASURED] + bucket[ESTIMATED] + bucket[FORECAST]
        if has_cost:
            bucket["cost"] = cost
        buckets.append(bucket)
        cursor = nxt
    return buckets


def summarize(buckets: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a list of buckets."""
    total = sum(b["total"] for b in buckets)
    days = sum(b["days"] for b in buckets)
    costs = [b["cost"] for b in buckets if b["cost"] is not None]
    return {
        "total": total,
        MEASURED: sum(b[MEASURED] for b in buckets),
        ESTIMATED: sum(b[ESTIMATED] for b in buckets),
        FORECAST: sum(b[FORECAST] for b in buckets),
        "days": days,
        "per_day": total / days if days else 0.0,
        "cost": sum(costs) if costs else None,
    }


def billing_periods(tariff: Tariff, today: date) -> list[tuple[date, date]]:
    """Return the billing periods of a contract.

    Open-ended contracts are expanded up to the period containing ``today``
    plus one following period.  At most 50 periods are returned.
    """
    periods: list[tuple[date, date]] = []
    months = max(1, tariff.billing_months)
    start = tariff.start
    index = 1
    while len(periods) < 50:
        end = add_months(tariff.start, months * index) - timedelta(days=1)
        if tariff.end is not None and end >= tariff.end:
            periods.append((start, tariff.end))
            break
        periods.append((start, end))
        start = end + timedelta(days=1)
        index += 1
        if tariff.end is None and end >= today and len(periods) >= 2 and periods[-2][1] >= today:
            break
    return periods


def current_period_index(periods: list[tuple[date, date]], today: date) -> int:
    """Return the index of the billing period containing ``today``."""
    for index, (start, end) in enumerate(periods):
        if start <= today <= end:
            return index
    if periods and today < periods[0][0]:
        return 0
    # Contract ended: show the last period.
    last = 0
    for index, (start, _end) in enumerate(periods):
        if start <= today:
            last = index
    return last


def payment_dates(start: date, end: date) -> list[date]:
    """Monthly advance payment dates within a billing period."""
    dates: list[date] = []
    index = 0
    while (pay := add_months(start, index)) <= end:
        dates.append(pay)
        index += 1
    return dates


def billing_forecast(
    model: ConsumptionModel,
    tariff: Tariff,
    period: tuple[date, date],
    today: date,
) -> dict[str, Any]:
    """Forecast the bill of a billing period.

    ``balance`` is positive if a refund is expected and negative if an
    additional payment is expected.
    """
    start, end = period
    consumption = {MEASURED: 0.0, ESTIMATED: 0.0, FORECAST: 0.0}
    energy_cost = 0.0
    for _d, value, kind in model.series(start, end, today):
        consumption[kind] += value
        energy_cost += value * tariff.conversion_factor * tariff.unit_price
    total = sum(consumption.values())
    days_total = (end - start).days + 1
    days_elapsed = max(0, min(days_total, (today - start).days + 1))
    payments = payment_dates(start, end)
    months = len(payments)
    base_cost = tariff.base_price * 12 / 365 * days_total
    total_cost = energy_cost + base_cost
    advance_total = tariff.advance_payment * months
    paid = tariff.advance_payment * sum(1 for p in payments if p <= today)
    balance = advance_total - total_cost
    if abs(balance) < 0.005:
        result = "even"
    elif balance > 0:
        result = "refund"
    else:
        result = "additional_payment"
    return {
        "contract_id": tariff.contract_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days_total": days_total,
        "days_elapsed": days_elapsed,
        "progress": days_elapsed / days_total if days_total else 0.0,
        "consumption": {**consumption, "total": total},
        "consumption_billing_unit": total * tariff.conversion_factor,
        "measured_share": consumption[MEASURED] / total if total else 0.0,
        "energy_cost": energy_cost,
        "base_cost": base_cost,
        "total_cost": total_cost,
        "advance_payment": tariff.advance_payment,
        "payments_count": months,
        "advance_total": advance_total,
        "paid_to_date": paid,
        "balance": balance,
        "result": result,
        "recommended_advance": total_cost / months if months else 0.0,
        "finished": today > end,
    }


def build_model(
    readings: Iterable[dict[str, Any]],
    meter: dict[str, Any],
) -> ConsumptionModel:
    """Build a consumption model from stored dicts."""
    annual = meter.get("annual_estimate")
    if not annual:
        annual = default_annual(meter.get("type", "other"), meter.get("unit", ""))
    return ConsumptionModel(
        readings=[Reading(parse_date(r["date"]), float(r["value"]), bool(r.get("reset"))) for r in readings],
        factors=resolve_profile(meter.get("type", "other"), meter.get("profile")),
        fallback_annual=float(annual or 0.0),
    )


def build_tariff(contract: dict[str, Any]) -> Tariff:
    """Build a tariff from a stored contract dict."""
    return Tariff(
        contract_id=contract["id"],
        start=parse_date(contract["start_date"]),
        end=parse_date(contract["end_date"]) if contract.get("end_date") else None,
        unit_price=float(contract.get("unit_price") or 0.0),
        base_price=float(contract.get("base_price") or 0.0),
        advance_payment=float(contract.get("advance_payment") or 0.0),
        conversion_factor=float(contract.get("conversion_factor") or 1.0),
        billing_months=int(contract.get("billing_months") or 12),
    )
