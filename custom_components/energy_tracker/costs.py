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
GAP_NO_TARIFF = "no_tariff"
GAP_NO_DATA = "no_data"
STATUS_COMPLETE = "complete"
STATUS_PARTIAL = "partial"
STATUS_GAP = "gap"
MODES = ("calendar", "billing")


@dataclass(slots=True)
class BillDay:
    """Share of a bill on one day."""

    bill_id: str
    energy_cost: float
    base_cost: float
    consumption: float
    consumption_billing: float


def _num(value: Any) -> float | None:
    return None if value is None or value == "" else float(value)


def bill_days(
    model: ConsumptionModel, tariffs: list[Tariff], bills: list[dict[str, Any]], today: date
) -> dict[date, BillDay]:
    """Distribute the recorded bills over their days.

    Bills without total cost are ignored.  If bills overlap, the later one
    (by end date) wins.
    """
    result: dict[date, BillDay] = {}
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
        elif all(find_tariff(tariffs, d) for d, _, _ in series):
            base_total = math.fsum(
                find_tariff(tariffs, d).phase_at(d).base_price * 12 / 365  # type: ignore[union-attr]
                for d, _, _ in series
            )
        else:
            base_total = None
        energy_total = total - base_total if base_total is not None else total

        for d, value, _kind in series:
            weight = value / own_total if own_total > 0 else 1 / days
            day_consumption = consumption * weight if consumption is not None else value
            result[d] = BillDay(
                bill_id=bill["id"],
                energy_cost=energy_total * weight,
                base_cost=(base_total / days) if base_total is not None else 0.0,
                consumption=day_consumption,
                consumption_billing=day_consumption * factor,
            )
    return result


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
    energy = base = consumption = consumption_billing = measured = forecast = 0.0
    bill_count = own_count = no_tariff = 0
    bill_ids: set[str] = set()
    uses_factor = False
    for d in daterange(start, end):
        if (share := shares.get(d)) is not None:
            bill_count += 1
            bill_ids.add(share.bill_id)
            energy += share.energy_cost
            base += share.base_cost
            consumption += share.consumption
            consumption_billing += share.consumption_billing
            measured += share.consumption
            uses_factor = uses_factor or abs(share.consumption_billing - share.consumption) > 1e-9
            continue
        if data_start is None or d < data_start:
            continue  # no data: neither readings nor a bill
        value, kind = model.day(d, today)
        tariff = find_tariff(tariffs, d)
        reference = tariff or nearest_tariff(tariffs, d)
        factor = reference.factor_at(d) if reference else 1.0
        uses_factor = uses_factor or factor != 1.0
        consumption += value
        consumption_billing += value * factor
        if kind == MEASURED:
            measured += value
        elif kind == FORECAST:
            forecast += value
        if tariff is None:
            no_tariff += 1
            continue
        own_count += 1
        phase = tariff.phase_at(d)
        energy += value * phase.conversion_factor * phase.unit_price
        base += phase.base_price * 12 / 365

    days = (end - start).days + 1
    cost_days = bill_count + own_count
    data_days = cost_days + no_tariff
    if cost_days == 0:
        status = STATUS_GAP
    elif cost_days < days:
        status = STATUS_PARTIAL
    else:
        status = STATUS_COMPLETE
    if not cost_days:
        source = None
    elif not own_count:
        source = SOURCE_BILL
    elif not bill_count:
        source = SOURCE_CALCULATED
    else:
        source = SOURCE_MIXED
    total_cost = energy + base if cost_days else None

    # average price per unit including the base price
    if meter_unit in ("kWh", "MWh") or uses_factor:
        kwh = consumption_billing * (1000 if meter_unit == "MWh" else 1)
        avg_unit = "ct/kWh"
        avg_price = total_cost * 100 / kwh if total_cost is not None and kwh > 0 else None
    else:
        avg_unit = f"€/{meter_unit}"
        avg_price = total_cost / consumption if total_cost is not None and consumption > 0 else None
    # the average price is only meaningful if cost and consumption cover the same days
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
        "consumption": consumption if data_days else None,
        "consumption_billing": consumption_billing if data_days else None,
        "consumption_forecast": forecast,
        "measured_share": measured / consumption if consumption else 0.0,
        "energy_cost": energy if cost_days else None,
        "base_cost": base if cost_days else None,
        "total_cost": total_cost,
        "cost_coverage": cost_days / days,
        "data_coverage": data_days / days,
        "avg_price": avg_price,
        "avg_price_unit": avg_unit,
        "bill_ids": sorted(bill_ids),
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
        if mode == "billing":
            matching = [b for b in bills if start <= parse_date(b["end_date"]) <= end]
            if matching:
                bill = matching[-1]
                if bill.get("advances_paid") is not None:
                    year["advances"] = float(bill["advances_paid"])
                    year["advances_source"] = SOURCE_BILL
                if (result := bill_result(bill)) is not None:
                    year["result"] = result
                    year["result_source"] = SOURCE_BILL
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
                entry["energy_cost"] += year["energy_cost"]
                entry["base_cost"] += year["base_cost"]
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
            "energy_cost": entry["energy_cost"] if has_cost else None,
            "base_cost": entry["base_cost"] if has_cost else None,
            "total_cost": entry["total_cost"] if has_cost else None,
            "consumption": None,
            "avg_price": None,
        }
        add_change(year, previous)
        result.append(year)
        previous = year
    return result
