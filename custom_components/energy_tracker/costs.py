"""Cost history over several years (calendar or billing years).

Free of Home Assistant imports so that it can be unit tested in isolation.

Every day of a year gets its consumption and cost from one source:

* a recorded **bill** of the utility (takes precedence): the billed total is
  distributed over the days of the bill, the energy part by the daily
  consumption of the model (seasonal profile), the base price evenly;
* the own **calculation**: daily consumption of the model times the tariff
  valid on that day;
* nothing: before the first reading there is **no data**, days with data but
  without tariff have **no tariff**.  Such days are never counted as 0 EUR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Any

from .calc import (
    FORECAST,
    MEASURED,
    ConsumptionModel,
    Tariff,
    bill_result,
    daterange,
    find_tariff,
    nearest_tariff,
    parse_date,
    payment_schedule,
    period_label,
)

SOURCE_CALCULATED = "calculated"
SOURCE_BILL = "bill"
SOURCE_MIXED = "mixed"
SOURCE_BILL_EXTRAPOLATED = "bill_extrapolated"
GAP_NO_TARIFF = "no_tariff"
GAP_NO_DATA = "no_data"
STATUS_COMPLETE = "complete"
STATUS_PARTIAL = "partial"
STATUS_GAP = "gap"
MODES = ("calendar", "billing")


# Missing days at the beginning or end of a year (e.g. first reading on
# 01.01.) are estimated from the neighbouring days if there are at most so many.
MAX_EDGE_GAP_DAYS = 7
NEIGHBOUR_DAYS = 7

KIND_BILL = "bill"
KIND_OWN = "own"
KIND_NO_TARIFF = "no_tariff"
KIND_NO_DATA = "no_data"
KIND_ESTIMATED = "estimated"
KIND_BILL_EXTRAPOLATED = "bill_extrapolated"

# Days without tariff next to a bill (e.g. between the last reading of a bill
# and the billing date) are valued with the prices of that bill.
MAX_BILL_EXTRAPOLATION_DAYS = 45


@dataclass(slots=True)
class BillDay:
    """Share of a bill on one day.

    ``energy_cost``/``base_cost`` are None if the bill states neither a base
    price nor is the period fully covered by a tariff (split unknown).
    """

    bill_id: str
    total_cost: float
    energy_cost: float | None
    base_cost: float | None
    consumption: float
    consumption_billing: float
    # True: day outside the bill, valued with the prices of the bill
    extrapolated: bool = False
    measured: float = 0.0
    forecast: float = 0.0

    @property
    def split_known(self) -> bool:
        """True if energy and base cost are known separately."""
        return self.energy_cost is not None


def _num(value: Any) -> float | None:
    return None if value is None or value == "" else float(value)


@dataclass(slots=True)
class _BillPrices:
    """Prices derived from a bill, used for neighbouring days without tariff."""

    bill_id: str
    start: date
    end: date
    factor: float
    unit_price: float | None  # per billing unit, as stated on the bill
    base_price: float | None  # per month, as stated on the bill
    per_unit_total: float | None  # total cost / consumption (meter unit)
    per_unit_energy: float | None  # energy cost / consumption, if the split is known
    base_per_day: float | None

    def day(self, value: float, kind: str) -> BillDay:
        """Cost of a day with the given consumption (meter unit)."""
        if self.unit_price is not None and self.base_price is not None:
            energy: float | None = value * self.factor * self.unit_price
            base: float | None = self.base_price * 12 / 365
            total = energy + base  # type: ignore[operator]
        elif self.per_unit_energy is not None and self.base_per_day is not None:
            energy = value * self.per_unit_energy
            base = self.base_per_day
            total = energy + base
        else:
            energy = base = None
            total = value * (self.per_unit_total or 0.0)
        return BillDay(
            bill_id=self.bill_id,
            total_cost=total,
            energy_cost=energy,
            base_cost=base,
            consumption=value,
            consumption_billing=value * self.factor,
            extrapolated=True,
            measured=value if kind == MEASURED else 0.0,
            forecast=value if kind == FORECAST else 0.0,
        )


def bill_days(
    model: ConsumptionModel,
    tariffs: list[Tariff],
    bills: list[dict[str, Any]],
    today: date,
    extrapolate: bool = True,
) -> dict[date, BillDay]:
    """Distribute the recorded bills over their days.

    The energy part follows the daily consumption of the model (seasonal
    profile), the base part is spread evenly.  Bills without total cost are
    ignored.  If bills overlap, the later one (by end date) wins.

    With ``extrapolate`` days without tariff and without bill that lie at
    most MAX_BILL_EXTRAPOLATION_DAYS before or after a bill get the prices of
    the nearest bill (``extrapolated=True``).  Only days with consumption data.
    """
    result: dict[date, BillDay] = {}
    prices: list[_BillPrices] = []
    for bill in sorted(bills, key=lambda b: (b["end_date"], b["start_date"])):
        total = _num(bill.get("total_cost"))
        if total is None:
            continue
        start = parse_date(bill["start_date"])
        end = parse_date(bill["end_date"])
        series = model.series(start, end, today)
        days = len(series)
        own_total = math.fsum(value for _, value, _ in series)
        middle = start + (end - start) / 2
        near = nearest_tariff(tariffs, middle)
        factor = _num(bill.get("conversion_factor")) or (near.factor_at(middle) if near else 1.0)

        consumption = _num(bill.get("consumption"))
        if consumption is not None and bill.get("consumption_unit") == "billing":
            consumption = consumption / factor if factor else consumption

        base_price = _num(bill.get("base_price"))
        if base_price is not None:
            base_total: float | None = base_price * 12 / 365 * days
        elif series and all(find_tariff(tariffs, d) for d, _, _ in series):
            base_total = math.fsum(
                find_tariff(tariffs, d).phase_at(d).base_price * 12 / 365  # type: ignore[union-attr]
                for d, _, _ in series
            )
        else:
            base_total = None  # split into energy and base cost unknown

        for d, value, _kind in series:
            weight = value / own_total if own_total > 0 else 1 / days
            day_consumption = consumption * weight if consumption is not None else value
            if base_total is None:
                day_total = total * weight
                energy, base = None, None
            else:
                energy = (total - base_total) * weight
                base = base_total / days
                day_total = energy + base
            result[d] = BillDay(
                bill_id=bill["id"],
                total_cost=day_total,
                energy_cost=energy,
                base_cost=base,
                consumption=day_consumption,
                consumption_billing=day_consumption * factor,
                measured=day_consumption,
            )

        units = consumption if consumption is not None else own_total
        prices.append(
            _BillPrices(
                bill_id=bill["id"],
                start=start,
                end=end,
                factor=factor,
                unit_price=_num(bill.get("unit_price")),
                base_price=base_price,
                per_unit_total=total / units if units > 0 else None,
                per_unit_energy=(total - base_total) / units
                if units > 0 and base_total is not None
                else None,
                base_per_day=base_total / days if base_total is not None and days else None,
            )
        )

    if extrapolate and prices and model.first_day is not None:
        data_start = model.first_day + timedelta(days=1)
        nearest: dict[date, tuple[int, int, _BillPrices]] = {}
        for order, bill_prices in enumerate(prices):
            for offset in range(1, MAX_BILL_EXTRAPOLATION_DAYS + 1):
                for d in (
                    bill_prices.start - timedelta(days=offset),
                    bill_prices.end + timedelta(days=offset),
                ):
                    if d in result or d < data_start or find_tariff(tariffs, d) is not None:
                        continue
                    # nearest bill wins, on a tie the later one
                    candidate = (offset, -order, bill_prices)
                    if d not in nearest or candidate[:2] < nearest[d][:2]:
                        nearest[d] = candidate
        for d, (_offset, _order, bill_prices) in nearest.items():
            value, kind = model.day(d, today)
            result[d] = bill_prices.day(value, kind)
    return result


@dataclass(slots=True)
class _Day:
    """Consumption and cost of one day of a year."""

    kind: str
    total: float | None = None
    energy: float | None = None
    base: float | None = None
    consumption: float | None = None
    consumption_billing: float | None = None
    measured: float = 0.0
    forecast: float = 0.0
    bill_id: str | None = None

    @property
    def has_cost(self) -> bool:
        return self.total is not None


def _day_records(
    model: ConsumptionModel,
    tariffs: list[Tariff],
    shares: dict[date, BillDay],
    period: tuple[date, date],
    today: date,
    data_start: date | None,
) -> tuple[list[_Day], bool]:
    """One record per day of the period and whether a conversion factor is used."""
    records: list[_Day] = []
    uses_factor = False
    for d in daterange(*period):
        if (share := shares.get(d)) is not None:
            uses_factor = uses_factor or abs(share.consumption_billing - share.consumption) > 1e-9
            records.append(
                _Day(
                    kind=KIND_BILL_EXTRAPOLATED if share.extrapolated else KIND_BILL,
                    total=share.total_cost,
                    energy=share.energy_cost,
                    base=share.base_cost,
                    consumption=share.consumption,
                    consumption_billing=share.consumption_billing,
                    measured=share.measured,
                    forecast=share.forecast,
                    bill_id=share.bill_id,
                )
            )
            continue
        if data_start is None or d < data_start:
            records.append(_Day(kind=KIND_NO_DATA))  # neither readings nor a bill
            continue
        value, kind = model.day(d, today)
        tariff = find_tariff(tariffs, d)
        reference = tariff or nearest_tariff(tariffs, d)
        factor = reference.factor_at(d) if reference else 1.0
        uses_factor = uses_factor or factor != 1.0
        record = _Day(
            kind=KIND_NO_TARIFF,
            consumption=value,
            consumption_billing=value * factor,
            measured=value if kind == MEASURED else 0.0,
            forecast=value if kind == FORECAST else 0.0,
        )
        if tariff is not None:
            phase = tariff.phase_at(d)
            record.kind = KIND_OWN
            record.energy = value * phase.conversion_factor * phase.unit_price
            record.base = phase.base_price * 12 / 365
            record.total = record.energy + record.base
        records.append(record)
    return records, uses_factor


def _average(days: list[_Day], attr: str) -> float | None:
    values = [getattr(day, attr) for day in days]
    if not values or any(value is None for value in values):
        return None
    return math.fsum(values) / len(values)


def _fill_edge_gaps(records: list[_Day]) -> int:
    """Estimate up to MAX_EDGE_GAP_DAYS missing days at the start and end of a year.

    Missing means: no cost (no data or no tariff).  Only if there are no
    missing days in between.  The estimate is the daily average of the
    neighbouring known days.  Returns the number of estimated days.
    """
    missing = [i for i, day in enumerate(records) if not day.has_cost]
    if not missing or len(missing) == len(records):
        return 0
    lead = 0
    while lead < len(records) and not records[lead].has_cost:
        lead += 1
    trail = 0
    while trail < len(records) and not records[-1 - trail].has_cost:
        trail += 1
    if lead + trail != len(missing) or lead > MAX_EDGE_GAP_DAYS or trail > MAX_EDGE_GAP_DAYS:
        return 0
    groups = []
    if lead:
        groups.append((range(lead), records[lead : lead + NEIGHBOUR_DAYS]))
    if trail:
        groups.append((range(len(records) - trail, len(records)), records[-trail - NEIGHBOUR_DAYS : -trail]))
    for indexes, neighbours in groups:
        estimate = {
            attr: _average(neighbours, attr)
            for attr in ("total", "energy", "base", "consumption", "consumption_billing")
        }
        for index in indexes:
            day = records[index]
            # keep a known consumption (days without tariff), estimate the rest
            consumption = day.consumption if day.consumption is not None else estimate["consumption"]
            consumption_billing = (
                day.consumption_billing
                if day.consumption_billing is not None
                else estimate["consumption_billing"]
            )
            records[index] = _Day(
                kind=KIND_ESTIMATED,
                total=estimate["total"],
                energy=estimate["energy"],
                base=estimate["base"],
                consumption=consumption,
                consumption_billing=consumption_billing,
                forecast=day.forecast,
            )
    return lead + trail


def period_costs(
    model: ConsumptionModel,
    tariffs: list[Tariff],
    shares: dict[date, BillDay],
    period: tuple[date, date],
    today: date,
    data_start: date | None,
    meter_unit: str,
) -> dict[str, Any]:
    """Consumption and cost of one year (calendar or billing year)."""
    start, end = period
    records, uses_factor = _day_records(model, tariffs, shares, period, today, data_start)
    estimated_days = _fill_edge_gaps(records)

    days = len(records)
    cost_days = [r for r in records if r.has_cost]
    data_days = [r for r in records if r.consumption is not None]
    bill_count = sum(1 for r in records if r.kind == KIND_BILL)
    extrapolated_days = sum(1 for r in records if r.kind == KIND_BILL_EXTRAPOLATED)
    own_count = sum(1 for r in records if r.kind == KIND_OWN)
    if not cost_days:
        status = STATUS_GAP
    elif len(cost_days) < days:
        status = STATUS_PARTIAL
    else:
        status = STATUS_COMPLETE
    if not cost_days:
        source = None
    elif own_count and (bill_count or extrapolated_days):
        source = SOURCE_MIXED
    elif own_count:
        source = SOURCE_CALCULATED
    elif extrapolated_days:
        source = SOURCE_BILL_EXTRAPOLATED
    elif bill_count:
        source = SOURCE_BILL
    else:
        source = SOURCE_CALCULATED  # only estimated edge days

    total_cost = math.fsum(r.total for r in cost_days) if cost_days else None  # type: ignore[misc]
    split_known = bool(cost_days) and all(r.energy is not None for r in cost_days)
    energy = math.fsum(r.energy for r in cost_days) if split_known else None  # type: ignore[misc]
    base = math.fsum(r.base for r in cost_days) if split_known else None  # type: ignore[misc]
    consumption = math.fsum(r.consumption for r in data_days) if data_days else None  # type: ignore[misc]
    consumption_billing = (
        math.fsum(r.consumption_billing for r in data_days) if data_days else None  # type: ignore[misc]
    )
    measured = math.fsum(r.measured for r in records)
    forecast = math.fsum(r.forecast for r in records)

    # average price per unit including the base price
    avg_price = None
    if meter_unit in ("kWh", "MWh") or uses_factor:
        avg_unit = "ct/kWh"
        if total_cost is not None and consumption_billing:
            kwh = consumption_billing * (1000 if meter_unit == "MWh" else 1)
            avg_price = total_cost * 100 / kwh
    else:
        avg_unit = f"€/{meter_unit}"
        if total_cost is not None and consumption:
            avg_price = total_cost / consumption
    # only meaningful if cost and consumption cover the same (all) days
    if status != STATUS_COMPLETE:
        avg_price = None

    return {
        "label": period_label(start, end),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": days,
        "status": status,
        "gap_reason": (GAP_NO_TARIFF if data_days else GAP_NO_DATA) if status == STATUS_GAP else None,
        "source": source,
        "forecast": end > today,
        "estimated_days": estimated_days,
        "extrapolated_days": extrapolated_days,
        "consumption": consumption,
        "consumption_billing": consumption_billing,
        "consumption_forecast": forecast,
        "measured_share": measured / consumption if consumption else 0.0,
        "split_known": split_known,
        "energy_cost": energy,
        "base_cost": base,
        "total_cost": total_cost,
        "cost_coverage": len(cost_days) / days,
        "data_coverage": len(data_days) / days,
        "avg_price": avg_price,
        "avg_price_unit": avg_unit,
        "bill_ids": sorted({r.bill_id for r in records if r.bill_id}),
    }


def meter_cost_history(
    model: ConsumptionModel,
    tariffs: list[Tariff],
    bills: list[dict[str, Any]],
    periods: list[tuple[date, date]],
    today: date,
    meter_unit: str,
    billing_month: int,
    mode: str,
) -> list[dict[str, Any]]:
    """Cost history of one meter for the given periods."""
    shares = bill_days(model, tariffs, bills, today)
    data_start = model.first_day + timedelta(days=1) if model.first_day else None
    payments = [
        (pay_day, amount)
        for tariff in tariffs
        for pay_day, amount in payment_schedule(tariff, periods[-1][1], billing_month)
    ]
    years: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for start, end in periods:
        year = period_costs(model, tariffs, shares, (start, end), today, data_start, meter_unit)
        own_advances = [amount for day, amount in payments if start <= day <= end]
        year["advances"] = math.fsum(own_advances) if own_advances else None
        year["advances_source"] = SOURCE_CALCULATED if own_advances else None
        year["result"] = None
        year["result_source"] = None
        year["result_incomplete"] = False
        year["bill_count"] = 0
        if mode == "billing":
            # all bills ending in the period, e.g. annual bill + final bill on a change of supplier
            matching = [b for b in bills if start <= parse_date(b["end_date"]) <= end]
            year["bill_count"] = len(matching)
            if matching:
                paid = [_num(b.get("advances_paid")) for b in matching]
                results = [bill_result(b) for b in matching]
                if any(value is not None for value in paid):
                    year["advances"] = math.fsum(value for value in paid if value is not None)
                    year["advances_source"] = SOURCE_BILL
                if any(value is not None for value in results):
                    year["result"] = math.fsum(value for value in results if value is not None)
                    year["result_source"] = SOURCE_BILL
                    # some bills without payments or result: sum of the known values only
                    year["result_incomplete"] = any(value is None for value in paid + results)
            if year["result"] is None and year["advances"] is not None and year["status"] == STATUS_COMPLETE:
                year["result"] = year["advances"] - year["total_cost"]
                year["result_source"] = SOURCE_CALCULATED
        add_change(year, previous)
        years.append(year)
        previous = year
    return years


def add_change(year: dict[str, Any], previous: dict[str, Any] | None) -> None:
    """Change of the total cost compared to the previous year."""
    year["change"] = None
    year["change_pct"] = None
    if (
        previous is None
        or previous["total_cost"] is None
        or year["total_cost"] is None
        or previous["status"] != STATUS_COMPLETE
        or year["status"] != STATUS_COMPLETE
    ):
        return
    year["change"] = year["total_cost"] - previous["total_cost"]
    if previous["total_cost"]:
        year["change_pct"] = year["change"] / previous["total_cost"] * 100


def calendar_years(first: date, today: date) -> list[tuple[date, date]]:
    """Calendar years from ``first`` up to the year containing ``today``."""
    return [(date(y, 1, 1), date(y, 12, 31)) for y in range(first.year, today.year + 1)]


def sum_years(per_meter: list[tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    """Add up the cost of several meters per year label."""
    by_label: dict[str, dict[str, Any]] = {}
    for name, years in per_meter:
        for year in years:
            entry = by_label.setdefault(
                year["label"],
                {
                    "label": year["label"],
                    "start": year["start"],
                    "end": year["end"],
                    "energy_cost": 0.0,
                    "base_cost": 0.0,
                    "split_known": True,
                    "estimated_days": 0,
                    "total_cost": 0.0,
                    "advances": None,
                    "result": None,
                    "sources": set(),
                    "forecast": False,
                    "complete": [],
                    "incomplete": [],
                },
            )
            entry["start"] = min(entry["start"], year["start"])
            entry["end"] = max(entry["end"], year["end"])
            entry["forecast"] = entry["forecast"] or year["forecast"]
            if year["status"] == STATUS_COMPLETE:
                entry["complete"].append(name)
            else:
                entry["incomplete"].append(name)
            if year["total_cost"] is not None:
                if year["split_known"]:
                    entry["energy_cost"] += year["energy_cost"]
                    entry["base_cost"] += year["base_cost"]
                else:
                    entry["split_known"] = False
                entry["estimated_days"] = max(entry["estimated_days"], year.get("estimated_days", 0))
                entry["total_cost"] += year["total_cost"]
                entry["sources"].add(year["source"])
            for key in ("advances", "result"):
                if year[key] is not None:
                    entry[key] = (entry[key] or 0.0) + year[key]

    result: list[dict[str, Any]] = []
    previous = None
    for entry in sorted(by_label.values(), key=lambda e: e["start"]):
        sources = entry.pop("sources")
        has_cost = bool(sources)
        if not has_cost:
            status = STATUS_GAP
        elif entry["incomplete"]:
            status = STATUS_PARTIAL
        else:
            status = STATUS_COMPLETE
        year = {
            **entry,
            "status": status,
            "gap_reason": None,
            "source": (next(iter(sources)) if len(sources) == 1 else SOURCE_MIXED) if has_cost else None,
            "split_known": has_cost and entry["split_known"],
            "energy_cost": entry["energy_cost"] if has_cost and entry["split_known"] else None,
            "base_cost": entry["base_cost"] if has_cost and entry["split_known"] else None,
            "total_cost": entry["total_cost"] if has_cost else None,
            "consumption": None,
            "avg_price": None,
        }
        add_change(year, previous)
        result.append(year)
        previous = year
    return result
