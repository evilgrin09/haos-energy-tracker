"""External long-term statistics for the Home Assistant energy dashboard.

For every meter an external statistic ``energy_tracker:<meter_id>_consumption``
is written (and ``energy_tracker:<meter_id>_cost`` if the meter has a
contract).  The daily values of the consumption model (measured and estimated,
never future days) are spread evenly over the hours of the local day; ``sum``
is the running total since the first reading.

Daily values only depend on the stored data, so after a change the series is
compared with what was written before and rewritten from the first day that
differs.  If rows would have to disappear (the series starts later or a unit
changed) the statistic is cleared and written again completely.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
import logging
import math
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.util import dt as dt_util

from .calc import find_tariff
from .const import DOMAIN
from .costs import bill_days
from .store import TrackerStore

_LOGGER = logging.getLogger(__name__)

SYNC_COOLDOWN = 2.0
UNIT_CLASSES = {"kWh": "energy", "MWh": "energy", "m³": "volume", "L": "volume"}
HOUR = timedelta(hours=1)


def consumption_statistic_id(meter_id: str) -> str:
    """Statistic id of the consumption of a meter."""
    return f"{DOMAIN}:{meter_id}_consumption"


def cost_statistic_id(meter_id: str) -> str:
    """Statistic id of the cost of a meter."""
    return f"{DOMAIN}:{meter_id}_cost"


def meter_statistic_ids(meter_id: str) -> list[str]:
    """All statistic ids belonging to a meter."""
    return [consumption_statistic_id(meter_id), cost_statistic_id(meter_id)]


def day_hours(day: date, tz: tzinfo) -> list[datetime]:
    """Return the UTC start times of all hours of a local day (23-25 hours)."""
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    # time zones with 30/45 minute offsets: align to the full (UTC) hour
    start = start.replace(minute=0, second=0, microsecond=0)
    end = end.replace(minute=0, second=0, microsecond=0)
    hours = []
    while start < end:
        hours.append(start)
        start += HOUR
    return hours


def build_rows(
    start_day: date,
    values: list[float],
    first_index: int,
    tz: tzinfo,
    limit: datetime,
) -> list[dict[str, Any]]:
    """Build hourly statistic rows for ``values[first_index:]``.

    ``values[i]`` is the value of day ``start_day + i``.  Only hours that start
    before ``limit`` are returned.  ``sum`` continues the total of all days
    before ``first_index``.
    """
    total = math.fsum(values[:first_index])
    rows: list[dict[str, Any]] = []
    for index in range(first_index, len(values)):
        hours = day_hours(start_day + timedelta(days=index), tz)
        per_hour = values[index] / len(hours)
        for hour in hours:
            if hour >= limit:
                return rows
            total += per_hour
            rows.append({"start": hour, "state": per_hour, "sum": total})
    return rows


def daily_values(
    store: TrackerStore, meter_id: str, today: date
) -> tuple[date, list[float], list[float] | None] | None:
    """Return start day, daily consumption and daily cost of a meter.

    The series starts on the day after the first reading and ends today.
    For days covered by a recorded bill the cost comes from the bill (the
    same distribution as in the cost history), otherwise from the tariff.
    Cost is None if the meter has neither a contract nor a bill with cost.
    """
    model = store.model(meter_id)
    if model.first_day is None:
        return None
    start = model.first_day + timedelta(days=1)
    if start > today:
        return None
    tariffs = store.tariffs(meter_id)
    shares = bill_days(model, tariffs, store.meter_bills(meter_id), today)
    consumption: list[float] = []
    cost: list[float] = []
    for day, value, _kind in model.series(start, today, today):
        consumption.append(value)
        if (share := shares.get(day)) is not None:
            cost.append(share.total_cost)
            continue
        tariff = find_tariff(tariffs, day) if tariffs else None
        cost.append(tariff.day_cost(value, day) if tariff else 0.0)
    return start, consumption, (cost if tariffs or shares else None)


@dataclass(slots=True)
class _Written:
    """What is known to be stored in the recorder for a statistic."""

    start_day: date | None = None  # None: nothing stored
    values: list[float] | None = None
    until: datetime | None = None  # start of the first hour not written yet
    name: str | None = None
    unit: str | None = None


def _first_difference(old: list[float], new: list[float]) -> int:
    """Index of the first day whose value changed (len(old) if only appended)."""
    for index, (a, b) in enumerate(zip(old, new, strict=False)):
        if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9):
            return index
    return min(len(old), len(new))


class StatisticsManager:
    """Keeps the external statistics in sync with the stored data."""

    def __init__(self, hass: HomeAssistant, store: TrackerStore) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.store = store
        self._written: dict[str, _Written] = {}
        self._known_meters: set[str] = set(store.meters)
        self._debouncer = Debouncer(
            hass,
            _LOGGER,
            cooldown=SYNC_COOLDOWN,
            immediate=False,
            function=self.async_sync,
            background=True,
        )

    @property
    def enabled(self) -> bool:
        """Statistics need the recorder."""
        return "recorder" in self.hass.config.components

    @callback
    def async_schedule(self, *_: Any) -> None:
        """Schedule a sync (several changes in a row are combined)."""
        if self.enabled:
            self._debouncer.async_schedule_call()

    @callback
    def async_shutdown(self) -> None:
        """Cancel pending work."""
        self._debouncer.async_shutdown()

    async def async_sync(self) -> None:
        """Bring the statistics of all meters up to date."""
        if not self.enabled:
            return
        from homeassistant.components.recorder import get_instance

        now = dt_util.utcnow()
        limit = now.replace(minute=0, second=0, microsecond=0)
        today = dt_util.as_local(now).date()
        german = self.hass.config.language.startswith("de")

        removed = self._known_meters - set(self.store.meters)
        if removed:
            ids = [sid for meter_id in removed for sid in meter_statistic_ids(meter_id)]
            get_instance(self.hass).async_clear_statistics(ids)
            for sid in ids:
                self._written.pop(sid, None)
        self._known_meters = set(self.store.meters)

        for meter_id, meter in list(self.store.meters.items()):
            data = daily_values(self.store, meter_id, today)
            start, consumption, cost = data if data else (None, None, None)
            name = str(meter.get("name") or meter_id)
            unit = str(meter.get("unit") or "")
            await self._sync_series(
                consumption_statistic_id(meter_id),
                f"{name} {'Verbrauch' if german else 'consumption'}",
                unit,
                UNIT_CLASSES.get(unit),
                start,
                consumption,
                limit,
            )
            await self._sync_series(
                cost_statistic_id(meter_id),
                f"{name} {'Kosten' if german else 'cost'}",
                self.hass.config.currency,
                None,
                start,
                cost,
                limit,
            )

    async def _sync_series(
        self,
        statistic_id: str,
        name: str,
        unit: str,
        unit_class: str | None,
        start_day: date | None,
        values: list[float] | None,
        limit: datetime,
    ) -> None:
        """Write the rows of one statistic that are missing or changed."""
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.models import (
            StatisticMeanType,
        )
        from homeassistant.components.recorder.statistics import (
            async_add_external_statistics,
            get_last_statistics,
        )

        hass = self.hass
        recorder = get_instance(hass)
        tz = dt_util.get_default_time_zone()
        written = self._written.get(statistic_id)

        if start_day is None or not values:
            # nothing to show: remove whatever is stored
            if written is None or written.start_day is not None:
                recorder.async_clear_statistics([statistic_id])
            self._written[statistic_id] = _Written()
            return

        first_index = 0
        clear = False
        if written is None:
            # First sync after a start: trust the stored rows if their total
            # matches what would be written now, then only append.
            last = await recorder.async_add_executor_job(
                get_last_statistics, hass, 1, statistic_id, False, {"sum"}
            )
            if rows := last.get(statistic_id):
                all_rows = await hass.async_add_executor_job(build_rows, start_day, values, 0, tz, limit)
                last_start = dt_util.utc_from_timestamp(rows[0]["start"])
                expected = next((r for r in all_rows if r["start"] == last_start), None)
                stored_sum = rows[0].get("sum") or 0.0
                if expected is not None and math.isclose(
                    expected["sum"], stored_sum, rel_tol=1e-6, abs_tol=1e-6
                ):
                    first_index = max(0, (dt_util.as_local(last_start).date() - start_day).days)
                else:
                    clear = True
        elif written.start_day is None:
            pass  # known to be empty: write everything
        elif start_day > written.start_day or unit != written.unit:
            clear = True
        elif start_day < written.start_day:
            pass  # series starts earlier: all totals change
        else:
            old = written.values or []
            if len(values) < len(old):
                clear = True
            else:
                first_index = _first_difference(old, values)
                if written.until is not None:
                    until_index = (dt_util.as_local(written.until).date() - start_day).days
                    first_index = min(first_index, max(0, until_index))
                if name != written.name:
                    # rewrite at least one day so that the metadata is updated
                    first_index = min(first_index, len(values) - 1)
                first_index = min(first_index, len(values) - 1)

        if clear:
            recorder.async_clear_statistics([statistic_id])
            first_index = 0

        rows = await hass.async_add_executor_job(build_rows, start_day, values, first_index, tz, limit)
        if rows:
            async_add_external_statistics(
                hass,
                {
                    "source": DOMAIN,
                    "statistic_id": statistic_id,
                    "name": name,
                    "unit_of_measurement": unit or None,
                    "unit_class": unit_class,
                    "has_sum": True,
                    "mean_type": StatisticMeanType.NONE,
                },
                rows,
            )
            _LOGGER.debug(
                "Wrote %s rows of %s from %s (clear=%s)",
                len(rows),
                statistic_id,
                rows[0]["start"],
                clear,
            )
        self._written[statistic_id] = _Written(
            start_day=start_day,
            values=list(values),
            until=rows[-1]["start"] + HOUR if rows else (written.until if written else None),
            name=name,
            unit=unit,
        )


@callback
def async_clear_meters(hass: HomeAssistant, meter_ids: list[str]) -> None:
    """Remove all statistics of the given meters."""
    if "recorder" not in hass.config.components or not meter_ids:
        return
    from homeassistant.components.recorder import get_instance

    get_instance(hass).async_clear_statistics(
        [sid for meter_id in meter_ids for sid in meter_statistic_ids(meter_id)]
    )
