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
import math
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
# Forecast methods
FORECAST_LAST_YEAR = "last_year"  # measured consumption of the last 365 days
FORECAST_AVERAGE = "average"  # average of the measurements of the last 2 years
FORECAST_METHODS = (FORECAST_LAST_YEAR, FORECAST_AVERAGE)
LAST_YEAR_DAYS = 365

# Default billing date ("Abrechnungsstichtag")
DEFAULT_BILLING_DAY = 30
DEFAULT_BILLING_MONTH = 9


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
    method: str = FORECAST_LAST_YEAR
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
        """Calculate the annualised consumption rate used for estimates.

        ``last_year``: measured consumption of the 365 days up to the last
        reading, divided by the profile weight of these days (seasonally
        weighted, so an incomplete year is extrapolated correctly).
        ``average``: all intervals of the last two years.
        """
        if not self.intervals:
            self.annual_rate = self.fallback_annual
            return
        last = self.intervals[-1].end
        delta = 0.0
        weight = 0.0
        days = 0
        if self.method == FORECAST_AVERAGE:
            window_start = last - timedelta(days=RATE_WINDOW_DAYS)
            for interval in self.intervals:
                if interval.end <= window_start:
                    continue
                delta += interval.delta
                for d in daterange(interval.start + timedelta(days=1), interval.end):
                    weight += day_weight(d, self.factors)
                    days += 1
            few_days = days < 365
        else:
            window_start = last - timedelta(days=LAST_YEAR_DAYS - 1)
            for d, value in self.measured.items():
                if window_start <= d <= last:
                    delta += value
                    weight += day_weight(d, self.factors)
                    days += 1
            few_days = self.measured_days < 365
        if weight <= 0:
            self.annual_rate = self.fallback_annual
            return
        measured_rate = delta / weight
        self.measured_annual_rate = measured_rate
        prior = PRIOR_DAYS if (self.fallback_annual > 0 and few_days) else 0
        self.annual_rate = (measured_rate * days + self.fallback_annual * prior) / (days + prior)

    def reading_at(self, day: date, today: date) -> float | None:
        """Meter value at the end of ``day``, interpolated between readings.

        Uses the daily values (seasonal profile), the same way a utility
        extrapolates a reading to the billing date.
        """
        if not self.readings:
            return None
        base = None
        for reading in self.readings:
            if reading.day <= day:
                base = reading
        if base is not None:
            return base.value + math.fsum(
                self.day(d, today)[0] for d in daterange(base.day + timedelta(days=1), day)
            )
        first = self.readings[0]
        return first.value - math.fsum(
            self.day(d, today)[0] for d in daterange(day + timedelta(days=1), first.day)
        )

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


@dataclass(slots=True, frozen=True)
class PricePhase:
    """Prices valid from ``start`` until the next price change."""

    start: date
    unit_price: float
    base_price: float
    conversion_factor: float
    note: str = ""


@dataclass(slots=True)
class PriceChange:
    """A price change within a contract; ``None`` keeps the previous value."""

    day: date
    unit_price: float | None = None
    base_price: float | None = None
    conversion_factor: float | None = None
    note: str = ""


@dataclass(slots=True)
class Tariff:
    """Contract / tariff data relevant for calculations.

    ``unit_price``, ``base_price`` and ``conversion_factor`` are the prices
    from the contract start; ``price_changes`` change them from a date on.
    """

    contract_id: str
    start: date
    end: date | None
    unit_price: float = 0.0  # currency per billing unit
    base_price: float = 0.0  # currency per month
    advance_payment: float = 0.0  # currency per payment
    conversion_factor: float = 1.0  # billing units per meter unit
    payments_per_year: int = 12  # 11: no payment in the month of the billing date
    payment_day: int = 1
    first_payment: date | None = None
    advance_changes: list[tuple[date, float]] = field(default_factory=list)
    provider: str = ""
    tariff: str = ""
    price_changes: list[PriceChange] = field(default_factory=list)
    phases: list[PricePhase] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        phase = PricePhase(self.start, self.unit_price, self.base_price, self.conversion_factor)
        self.phases = [phase]
        for change in sorted(self.price_changes, key=lambda c: c.day):
            phase = PricePhase(
                change.day,
                phase.unit_price if change.unit_price is None else change.unit_price,
                phase.base_price if change.base_price is None else change.base_price,
                phase.conversion_factor if change.conversion_factor is None else change.conversion_factor,
                change.note,
            )
            if change.day <= self.start:
                self.phases[0] = PricePhase(
                    self.start, phase.unit_price, phase.base_price, phase.conversion_factor, phase.note
                )
            else:
                self.phases.append(phase)

    def covers(self, d: date) -> bool:
        """Return True if the tariff is valid on ``d``."""
        return self.start <= d and (self.end is None or d <= self.end)

    def phase_at(self, d: date) -> PricePhase:
        """Prices valid on ``d``."""
        current = self.phases[0]
        for phase in self.phases[1:]:
            if phase.start > d:
                break
            current = phase
        return current

    def day_cost(self, consumption: float, d: date) -> float:
        """Cost of day ``d`` with the given consumption (incl. base price)."""
        phase = self.phase_at(d)
        return consumption * phase.conversion_factor * phase.unit_price + phase.base_price * 12 / 365

    def factor_at(self, d: date) -> float:
        """Conversion factor (billing units per meter unit) valid on ``d``."""
        return self.phase_at(d).conversion_factor

    def advance_at(self, d: date) -> float:
        """Advance payment amount valid on ``d``."""
        amount = self.advance_payment
        for since, value in sorted(self.advance_changes):
            if since <= d:
                amount = value
        return amount


def find_tariff(tariffs: list[Tariff], d: date) -> Tariff | None:
    """Return the tariff valid on ``d`` (latest start wins)."""
    match = None
    for tariff in tariffs:
        if tariff.covers(d) and (match is None or tariff.start >= match.start):
            match = tariff
    return match


def nearest_tariff(tariffs: list[Tariff], d: date) -> Tariff | None:
    """Return the tariff valid on ``d`` or the one closest in time."""
    if not tariffs:
        return None
    if tariff := find_tariff(tariffs, d):
        return tariff

    def distance(tariff: Tariff) -> int:
        if d < tariff.start:
            return (tariff.start - d).days
        return (d - tariff.end).days if tariff.end else 0

    return min(tariffs, key=distance)


def aggregate(
    model: ConsumptionModel,
    start: date,
    end: date,
    granularity: str,
    today: date,
    tariffs: list[Tariff] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate daily consumption into buckets of the given granularity.

    ``cost`` only contains days covered by a tariff, ``cost_days`` counts them.
    """
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
            "cost_days": 0,
        }
        cost = 0.0
        for d, value, kind in model.series(b_start, b_end, today):
            bucket[kind] += value
            if tariffs and (tariff := find_tariff(tariffs, d)):
                cost += tariff.day_cost(value, d)
                bucket["cost_days"] += 1
        bucket["total"] = bucket[MEASURED] + bucket[ESTIMATED] + bucket[FORECAST]
        if bucket["cost_days"]:
            bucket["cost"] = cost
        buckets.append(bucket)
        cursor = nxt
    return buckets


def summarize(buckets: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a list of buckets."""
    total = sum(b["total"] for b in buckets)
    days = sum(b["days"] for b in buckets)
    costs = [b["cost"] for b in buckets if b["cost"] is not None]
    cost_days = sum(b.get("cost_days", 0) for b in buckets)
    return {
        "total": total,
        MEASURED: sum(b[MEASURED] for b in buckets),
        ESTIMATED: sum(b[ESTIMATED] for b in buckets),
        FORECAST: sum(b[FORECAST] for b in buckets),
        "days": days,
        "per_day": total / days if days else 0.0,
        "cost": sum(costs) if costs else None,
        "cost_coverage": cost_days / days if days else 0.0,
    }


# ---------------------------------------------------------------- billing


def billing_date(year: int, day: int, month: int) -> date:
    """Billing date ("Stichtag") of a year, clamped to the month length."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def billing_period_for(d: date, day: int, month: int) -> tuple[date, date]:
    """Billing period (day after the previous billing date .. billing date) containing ``d``."""
    end = billing_date(d.year, day, month)
    if d > end:
        end = billing_date(d.year + 1, day, month)
    start = billing_date(end.year - 1, day, month) + timedelta(days=1)
    return start, end


def billing_periods(first: date, last: date, day: int, month: int) -> list[tuple[date, date]]:
    """All billing periods from the one containing ``first`` to the one containing ``last``."""
    periods = [billing_period_for(first, day, month)]
    while periods[-1][1] < last and len(periods) < 100:
        periods.append(billing_period_for(periods[-1][1] + timedelta(days=1), day, month))
    return periods


def period_label(start: date, end: date) -> str:
    """Label of a billing period: "2025/26" or "2025" for calendar years."""
    if start.year == end.year:
        return str(start.year)
    return f"{start.year}/{end.year % 100:02d}"


def period_index(periods: list[tuple[date, date]], d: date) -> int:
    """Index of the period containing ``d`` (first/last period if outside)."""
    for index, (start, end) in enumerate(periods):
        if start <= d <= end:
            return index
    return 0 if periods and d < periods[0][0] else max(0, len(periods) - 1)


def payment_schedule(tariff: Tariff, until: date, billing_month: int) -> list[tuple[date, float]]:
    """Monthly advance payments of a contract up to ``until``.

    Payments start with ``first_payment`` (default: first payment day on or
    after the contract start) and are due on ``payment_day`` every month
    while the contract runs.  With 11 payments per year there is no payment
    in the month of the billing date.  Amounts follow ``advance_changes``.
    """
    day = max(1, min(int(tariff.payment_day or 1), 31))
    if tariff.first_payment:
        current = tariff.first_payment
    else:
        current = date(
            tariff.start.year,
            tariff.start.month,
            min(day, calendar.monthrange(tariff.start.year, tariff.start.month)[1]),
        )
        if current < tariff.start:
            current = add_months(current.replace(day=1), 1)
            current = current.replace(day=min(day, calendar.monthrange(current.year, current.month)[1]))
    payments: list[tuple[date, float]] = []
    month_start = current.replace(day=1)
    while current <= until and (tariff.end is None or current <= tariff.end):
        if not (tariff.payments_per_year == 11 and current.month == billing_month):
            amount = tariff.advance_at(current)
            if amount > 0:
                payments.append((current, amount))
        month_start = add_months(month_start, 1)
        current = month_start.replace(
            day=min(day, calendar.monthrange(month_start.year, month_start.month)[1])
        )
    return payments


def billing_forecast(
    model: ConsumptionModel,
    tariffs: list[Tariff],
    period: tuple[date, date],
    today: date,
    billing_month: int = DEFAULT_BILLING_MONTH,
) -> dict[str, Any]:
    """Calculate (or forecast) the bill of a billing period.

    Several tariffs within the period are applied day by day.  Costs only
    contain days covered by a tariff (see ``cost_coverage``).  ``balance`` is
    positive if a refund is expected and negative for an additional payment.
    """
    start, end = period
    consumption = {MEASURED: 0.0, ESTIMATED: 0.0, FORECAST: 0.0}
    billed = 0.0
    energy_cost = 0.0
    base_cost = 0.0
    full_cost = 0.0  # including days without tariff (nearest tariff)
    covered = 0
    segments: list[dict[str, Any]] = []
    for d, value, kind in model.series(start, end, today):
        consumption[kind] += value
        tariff = find_tariff(tariffs, d)
        if tariff is None:
            near = nearest_tariff(tariffs, d)
            billed += value * (near.factor_at(d) if near else 1.0)
            if near:
                full_cost += near.day_cost(value, d)
            continue
        covered += 1
        phase = tariff.phase_at(d)
        day_energy = value * phase.conversion_factor * phase.unit_price
        day_base = phase.base_price * 12 / 365
        billed += value * phase.conversion_factor
        energy_cost += day_energy
        base_cost += day_base
        full_cost += day_energy + day_base
        # one segment per contract and price phase
        if (
            not segments
            or segments[-1]["contract_id"] != tariff.contract_id
            or segments[-1]["phase_start"] != phase.start.isoformat()
        ):
            segments.append(
                {
                    "contract_id": tariff.contract_id,
                    "phase_start": phase.start.isoformat(),
                    "provider": tariff.provider,
                    "tariff": tariff.tariff,
                    "start": d.isoformat(),
                    "end": d.isoformat(),
                    "days": 0,
                    "consumption": 0.0,
                    "consumption_billing_unit": 0.0,
                    "unit_price": phase.unit_price,
                    "base_price": phase.base_price,
                    "conversion_factor": phase.conversion_factor,
                    "note": phase.note,
                    "energy_cost": 0.0,
                    "base_cost": 0.0,
                }
            )
        segment = segments[-1]
        segment["end"] = d.isoformat()
        segment["days"] += 1
        segment["consumption"] += value
        segment["consumption_billing_unit"] += value * phase.conversion_factor
        segment["energy_cost"] += day_energy
        segment["base_cost"] += day_base

    total = sum(consumption.values())
    days_total = (end - start).days + 1
    days_elapsed = max(0, min(days_total, (today - start).days + 1))
    total_cost = energy_cost + base_cost
    payments = sorted(
        (pay_day, amount)
        for tariff in tariffs
        for pay_day, amount in payment_schedule(tariff, end, billing_month)
        if start <= pay_day <= end
    )
    advance_total = math.fsum(amount for _, amount in payments)
    paid = math.fsum(amount for pay_day, amount in payments if pay_day <= today)
    balance = advance_total - total_cost
    if not covered and not payments:
        result = "no_tariff"
    elif abs(balance) < 0.005:
        result = "even"
    elif balance > 0:
        result = "refund"
    else:
        result = "additional_payment"
    last_tariff = nearest_tariff(tariffs, end)
    per_year = last_tariff.payments_per_year if last_tariff else 12
    return {
        "label": period_label(start, end),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days_total": days_total,
        "days_elapsed": days_elapsed,
        "progress": days_elapsed / days_total if days_total else 0.0,
        "finished": today > end,
        "consumption": {**consumption, "total": total},
        "consumption_billing_unit": billed,
        "measured_share": consumption[MEASURED] / total if total else 0.0,
        "reading_start": model.reading_at(start - timedelta(days=1), today),
        "reading_end": model.reading_at(end, today),
        # "measured": the billing date lies between two readings (interpolated)
        "reading_start_kind": reading_kind(model, start - timedelta(days=1), today),
        "reading_end_kind": reading_kind(model, end, today),
        "energy_cost": energy_cost,
        "base_cost": base_cost,
        "total_cost": total_cost,
        "cost_coverage": covered / days_total if days_total else 0.0,
        "segments": segments,
        "payments": [
            {"date": pay_day.isoformat(), "amount": amount, "paid": pay_day <= today}
            for pay_day, amount in payments
        ],
        "payments_count": len(payments),
        "advance_total": advance_total,
        "paid_to_date": paid,
        "balance": balance,
        "result": result,
        "payments_per_year": per_year,
        "recommended_advance": full_cost / per_year if per_year and tariffs else 0.0,
    }


def reading_kind(model: ConsumptionModel, day: date, today: date) -> str | None:
    """How the meter value at the end of ``day`` is known.

    ``reading``: there is a reading, ``interpolated``: between two readings,
    ``estimated``: in the past but outside the readings, ``forecast``: future.
    """
    if not model.readings:
        return None
    if any(r.day == day for r in model.readings):
        return "reading"
    if model.first_day < day < model.last_day:
        return "interpolated"
    return "forecast" if day > today else "estimated"


def compare_bill(bill: dict[str, Any], own: dict[str, Any]) -> dict[str, Any]:
    """Compare a bill of the utility with the own calculation of its period."""

    def deviation(actual: float | None, calculated: float | None) -> dict[str, Any] | None:
        if actual is None or calculated is None:
            return None
        diff = actual - calculated
        return {
            "bill": actual,
            "own": calculated,
            "diff": diff,
            "pct": diff / calculated * 100 if calculated else None,
        }

    in_billing_unit = bill.get("consumption_unit") == "billing"
    plausibility = bill_plausibility(bill, own)
    own_consumption = own["consumption_billing_unit"] if in_billing_unit else own["consumption"]["total"]
    has_cost = own["cost_coverage"] > 0
    bill_balance = bill_result(bill)
    return {
        "consumption": deviation(_float(bill.get("consumption")), own_consumption),
        "total_cost": deviation(_float(bill.get("total_cost")), own["total_cost"] if has_cost else None),
        "advances": deviation(
            _float(bill.get("advances_paid")), own["advance_total"] if own["payments"] else None
        ),
        "balance": deviation(bill_balance, own["balance"] if has_cost else None),
        "cost_coverage": own["cost_coverage"],
        "plausibility": plausibility,
    }


# A billed consumption that differs more than this from the own readings is
# reported (the bill can still be saved).
PLAUSIBILITY_MAX_DEVIATION_PCT = 25.0
# The own readings must cover most of the bill period for the check.
PLAUSIBILITY_MIN_MEASURED_SHARE = 0.8


def bill_plausibility(bill: dict[str, Any], own: dict[str, Any]) -> dict[str, Any]:
    """Compare the billed consumption with the own readings (meter unit).

    A consumption in the billing unit (e.g. kWh for gas) is converted with
    the conversion factor of the bill or, if missing, the one of the tariffs.
    The check needs a measured share of at least 80 % in the bill period.
    """
    result: dict[str, Any] = {
        "checked": False,
        "warning": False,
        "bill": None,
        "own": own["consumption"]["total"],
        "pct": None,
        "measured_share": own["measured_share"],
        "max_pct": PLAUSIBILITY_MAX_DEVIATION_PCT,
    }
    consumption = _float(bill.get("consumption"))
    if consumption is None:
        return result
    if bill.get("consumption_unit") == "billing":
        factor = _float(bill.get("conversion_factor"))
        if not factor and own["consumption"]["total"]:
            factor = own["consumption_billing_unit"] / own["consumption"]["total"]
        consumption = consumption / factor if factor else consumption
    result["bill"] = consumption
    own_total = own["consumption"]["total"]
    if own_total <= 0 or own["measured_share"] < PLAUSIBILITY_MIN_MEASURED_SHARE:
        return result
    pct = (consumption - own_total) / own_total * 100
    result.update(checked=True, pct=pct, warning=abs(pct) > PLAUSIBILITY_MAX_DEVIATION_PCT)
    return result


def _float(value: Any) -> float | None:
    return None if value is None or value == "" else float(value)


def bill_result(bill: dict[str, Any]) -> float | None:
    """Result of a bill (positive: refund), calculated if not given."""
    if bill.get("balance") is not None:
        return float(bill["balance"])
    cost = _float(bill.get("total_cost"))
    paid = _float(bill.get("advances_paid"))
    if cost is None or paid is None:
        return None
    return paid - cost


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
        method=meter.get("forecast_method") or FORECAST_LAST_YEAR,
    )


def build_tariff(contract: dict[str, Any], extra_changes: Iterable[tuple[date, float]] = ()) -> Tariff:
    """Build a tariff from a stored contract dict.

    ``extra_changes`` are advance changes from bills ("new advance from").
    Changes stored with the contract win on the same day.
    """
    changes: dict[date, float] = {}
    for since, amount in extra_changes:
        changes[since] = float(amount)
    for change in contract.get("advance_changes") or []:
        changes[parse_date(change["date"])] = float(change["amount"])
    return Tariff(
        contract_id=contract["id"],
        start=parse_date(contract["start_date"]),
        end=parse_date(contract["end_date"]) if contract.get("end_date") else None,
        unit_price=float(contract.get("unit_price") or 0.0),
        base_price=float(contract.get("base_price") or 0.0),
        advance_payment=float(contract.get("advance_payment") or 0.0),
        conversion_factor=float(contract.get("conversion_factor") or 1.0),
        payments_per_year=int(contract.get("payments_per_year") or 12),
        payment_day=int(contract.get("payment_day") or 1),
        first_payment=parse_date(contract["first_payment"]) if contract.get("first_payment") else None,
        advance_changes=sorted(changes.items()),
        provider=contract.get("provider") or "",
        tariff=contract.get("tariff") or "",
        price_changes=[
            PriceChange(
                day=parse_date(change["date"]),
                unit_price=_float(change.get("unit_price")),
                base_price=_float(change.get("base_price")),
                conversion_factor=_float(change.get("conversion_factor")),
                note=change.get("note") or "",
            )
            for change in contract.get("price_changes") or []
        ],
    )
