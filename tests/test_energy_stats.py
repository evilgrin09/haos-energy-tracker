"""Tests for the external statistics (energy dashboard)."""

from datetime import UTC, date, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    list_statistic_ids,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_tracker.const import DATA_STATISTICS, DOMAIN
from custom_components.energy_tracker.energy_stats import (
    StatisticsManager,
    build_rows,
    consumption_statistic_id,
    cost_statistic_id,
    day_hours,
)

BERLIN = ZoneInfo("Europe/Berlin")


def test_day_hours_handles_dst() -> None:
    """Local days have 23, 24 or 25 hours and start at local midnight."""
    normal = day_hours(date(2025, 6, 21), BERLIN)
    assert len(normal) == 24
    assert normal[0] == datetime(2025, 6, 20, 22, tzinfo=UTC)
    assert len(day_hours(date(2025, 3, 30), BERLIN)) == 23
    assert len(day_hours(date(2025, 10, 26), BERLIN)) == 25
    # half-hour time zones are aligned to the full hour
    india = day_hours(date(2025, 6, 21), ZoneInfo("Asia/Kolkata"))
    assert len(india) == 24
    assert all(h.minute == 0 for h in india)


def test_build_rows_distribution_and_sum() -> None:
    """Daily values are spread evenly and summed up continuously."""
    limit = datetime(2030, 1, 1, tzinfo=UTC)
    rows = build_rows(date(2025, 3, 29), [24.0, 23.0, 48.0], 0, BERLIN, limit)
    assert len(rows) == 24 + 23 + 24
    assert rows[0]["state"] == pytest.approx(1.0)
    assert rows[23]["sum"] == pytest.approx(24.0)
    assert rows[24]["state"] == pytest.approx(1.0)  # 23 kWh on the 23 hour day
    assert rows[46]["sum"] == pytest.approx(47.0)
    assert rows[-1]["state"] == pytest.approx(2.0)
    assert rows[-1]["sum"] == pytest.approx(95.0)
    # continuing from the third day keeps the running total
    tail = build_rows(date(2025, 3, 29), [24.0, 23.0, 48.0], 2, BERLIN, limit)
    assert tail == rows[47:]
    # nothing at or after the limit (no future values)
    cut = build_rows(date(2025, 3, 29), [24.0, 23.0, 48.0], 0, BERLIN, rows[30]["start"])
    assert cut == rows[:30]


@pytest.fixture
async def store(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
):
    """Set up recorder and integration, return the store."""
    freezer.move_to("2025-07-01 12:30:00+00:00")
    await hass.config.async_set_time_zone("Europe/Berlin")
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, options={"show_panel": False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield hass.data[DOMAIN]
    await hass.config_entries.async_unload(entry.entry_id)


async def _sync(hass: HomeAssistant) -> None:
    await hass.data[DATA_STATISTICS].async_sync()
    await async_wait_recording_done(hass)


async def _rows(hass: HomeAssistant, statistic_id: str) -> list[dict]:
    await async_wait_recording_done(hass)
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utc_from_timestamp(0),
        None,
        {statistic_id},
        "hour",
        None,
        {"sum", "state"},
    )
    return result.get(statistic_id, [])


def _meter(store) -> dict:
    """Meter using 24 kWh per day in measurement and estimate."""
    meter = store.save_meter(
        {"name": "Strom", "type": "electricity", "unit": "kWh", "profile": "flat", "annual_estimate": 8760}
    )
    store.save_reading({"meter_id": meter["id"], "date": "2025-06-20", "value": 100})
    store.save_reading({"meter_id": meter["id"], "date": "2025-06-25", "value": 220})
    return meter


def _assert_continuous(rows: list[dict]) -> None:
    """No gaps, no duplicates, sum is the running total of state."""
    total = 0.0
    for previous, row in pairwise(rows):
        assert row["start"] - previous["start"] == 3600
    for row in rows:
        assert row["state"] >= 0
        total += row["state"]
        assert row["sum"] == pytest.approx(total)


async def test_statistics_written(recorder_mock, hass: HomeAssistant, store) -> None:
    """Hourly rows from the day after the first reading up to the last full hour."""
    meter = _meter(store)
    sid = consumption_statistic_id(meter["id"])
    await _sync(hass)
    rows = await _rows(hass, sid)

    # 2025-06-21 00:00 Berlin .. 2025-07-01 12:00 UTC (exclusive)
    assert rows[0]["start"] == datetime(2025, 6, 20, 22, tzinfo=UTC).timestamp()
    assert rows[-1]["start"] == datetime(2025, 7, 1, 11, tzinfo=UTC).timestamp()
    assert len(rows) == 10 * 24 + 14
    assert all(row["state"] == pytest.approx(1.0) for row in rows)
    assert rows[119]["sum"] == pytest.approx(120.0)  # measured part
    assert rows[-1]["sum"] == pytest.approx(254.0)  # plus estimates until now
    _assert_continuous(rows)

    meta = await get_instance(hass).async_add_executor_job(list_statistic_ids, hass, {sid})
    assert meta[0]["statistics_unit_of_measurement"] == "kWh"
    assert meta[0]["unit_class"] == "energy"
    assert meta[0]["has_sum"] is True
    assert meta[0]["source"] == DOMAIN
    assert meta[0]["name"] == "Strom consumption"

    # no contract: no cost statistic
    assert await _rows(hass, cost_statistic_id(meter["id"])) == []


async def test_retroactive_reading(recorder_mock, hass: HomeAssistant, store) -> None:
    """A reading in the past rewrites the rows from the first affected day."""
    meter = _meter(store)
    sid = consumption_statistic_id(meter["id"])
    await _sync(hass)

    store.save_reading({"meter_id": meter["id"], "date": "2025-06-22", "value": 190})
    await _sync(hass)
    rows = await _rows(hass, sid)
    assert len(rows) == 254
    assert rows[0]["state"] == pytest.approx(45 / 24)
    assert rows[47]["sum"] == pytest.approx(90.0)
    assert rows[48]["state"] == pytest.approx(10 / 24)
    assert rows[119]["sum"] == pytest.approx(120.0)
    assert rows[-1]["sum"] == pytest.approx(254.0)
    _assert_continuous(rows)


async def test_meter_replacement(recorder_mock, hass: HomeAssistant, store) -> None:
    """A meter replacement does not create negative values or jumps."""
    meter = _meter(store)
    sid = consumption_statistic_id(meter["id"])
    await _sync(hass)

    store.save_reading({"meter_id": meter["id"], "date": "2025-06-28", "value": 300})
    store.save_reading({"meter_id": meter["id"], "date": "2025-06-28", "value": 0, "reset": True})
    store.save_reading({"meter_id": meter["id"], "date": "2025-06-30", "value": 48})
    await _sync(hass)
    rows = await _rows(hass, sid)
    assert len(rows) == 254
    # 120 + 80 + 48 measured until the end of 2025-06-30 (local)
    assert rows[10 * 24 - 1]["sum"] == pytest.approx(248.0)
    _assert_continuous(rows)


async def test_first_reading_removed(recorder_mock, hass: HomeAssistant, store) -> None:
    """If the series starts later the old rows disappear."""
    meter = _meter(store)
    sid = consumption_statistic_id(meter["id"])
    store.save_reading({"meter_id": meter["id"], "date": "2025-06-27", "value": 268})
    await _sync(hass)
    assert len(await _rows(hass, sid)) == 254

    first = store.meter_readings(meter["id"])[0]
    store.delete_reading(first["id"])
    await _sync(hass)
    rows = await _rows(hass, sid)
    assert rows[0]["start"] == datetime(2025, 6, 25, 22, tzinfo=UTC).timestamp()
    assert len(rows) == 5 * 24 + 14
    assert rows[47]["sum"] == pytest.approx(48.0)
    _assert_continuous(rows)

    # without any reading nothing is left
    for reading in store.meter_readings(meter["id"]):
        store.delete_reading(reading["id"])
    await _sync(hass)
    assert await _rows(hass, sid) == []


async def test_cost_statistic(recorder_mock, hass: HomeAssistant, store) -> None:
    """With a contract the cumulated cost is written as well."""
    meter = _meter(store)
    contract = store.save_contract(
        {"meter_id": meter["id"], "start_date": "2025-06-23", "unit_price": 0.5, "base_price": 0}
    )
    await _sync(hass)
    rows = await _rows(hass, cost_statistic_id(meter["id"]))
    assert len(rows) == 254
    assert rows[47]["sum"] == pytest.approx(0.0)  # before the contract
    assert rows[48]["state"] == pytest.approx(0.5)
    assert rows[-1]["sum"] == pytest.approx((254 - 48) * 0.5)
    meta = await get_instance(hass).async_add_executor_job(
        list_statistic_ids, hass, {cost_statistic_id(meter["id"])}
    )
    assert meta[0]["statistics_unit_of_measurement"] == hass.config.currency

    store.save_contract({"unit_price": 1.0}, contract["id"])
    await _sync(hass)
    rows = await _rows(hass, cost_statistic_id(meter["id"]))
    assert rows[-1]["sum"] == pytest.approx(254 - 48)
    _assert_continuous(rows)

    store.delete_contract(contract["id"])
    await _sync(hass)
    assert await _rows(hass, cost_statistic_id(meter["id"])) == []


async def test_append_after_restart(
    recorder_mock, hass: HomeAssistant, store, freezer: FrozenDateTimeFactory
) -> None:
    """A new manager (restart) only appends the hours that have passed."""
    meter = _meter(store)
    sid = consumption_statistic_id(meter["id"])
    await _sync(hass)

    freezer.move_to("2025-07-01 15:30:00+00:00")
    manager = StatisticsManager(hass, store)
    cleared = []
    recorder = get_instance(hass)
    original = recorder.async_clear_statistics
    recorder.async_clear_statistics = lambda ids, **kw: cleared.extend(ids) or original(ids, **kw)
    try:
        await manager.async_sync()
    finally:
        recorder.async_clear_statistics = original
    rows = await _rows(hass, sid)
    assert sid not in cleared
    assert len(rows) == 257
    assert rows[-1]["sum"] == pytest.approx(257.0)
    _assert_continuous(rows)


async def test_inconsistent_rows_are_rebuilt(recorder_mock, hass: HomeAssistant, store) -> None:
    """If stored rows do not match the data after a restart they are rewritten."""
    meter = _meter(store)
    sid = consumption_statistic_id(meter["id"])
    await _sync(hass)
    # change data "behind the back" of the manager, then simulate a restart
    reading = store.meter_readings(meter["id"])[1]
    store.readings[reading["id"]]["value"] = 340
    store._models.clear()
    await StatisticsManager(hass, store).async_sync()
    rows = await _rows(hass, sid)
    assert rows[119]["sum"] == pytest.approx(240.0)
    assert len(rows) == 254
    _assert_continuous(rows)


async def test_meter_deleted(recorder_mock, hass: HomeAssistant, store) -> None:
    """Deleting a meter removes its statistics."""
    meter = _meter(store)
    store.save_contract({"meter_id": meter["id"], "start_date": "2025-06-01", "unit_price": 0.3})
    await _sync(hass)
    assert await _rows(hass, consumption_statistic_id(meter["id"]))
    assert await _rows(hass, cost_statistic_id(meter["id"]))

    store.delete_meter(meter["id"])
    await _sync(hass)
    assert await _rows(hass, consumption_statistic_id(meter["id"])) == []
    assert await _rows(hass, cost_statistic_id(meter["id"])) == []


async def test_cost_rewritten_for_historic_contract(recorder_mock, hass: HomeAssistant, store) -> None:
    """Adding an old contract later fills in the costs of the past."""
    meter = _meter(store)
    store.save_contract({"meter_id": meter["id"], "start_date": "2025-06-28", "unit_price": 1.0})
    await _sync(hass)
    rows = await _rows(hass, cost_statistic_id(meter["id"]))
    assert rows[7 * 24 - 1]["sum"] == pytest.approx(0.0)  # until 27.06. no tariff

    store.save_contract(
        {"meter_id": meter["id"], "start_date": "2025-01-01", "end_date": "2025-06-27", "unit_price": 0.5}
    )
    await _sync(hass)
    rows = await _rows(hass, cost_statistic_id(meter["id"]))
    assert len(rows) == 254
    assert rows[0]["state"] == pytest.approx(0.5)
    assert rows[7 * 24 - 1]["sum"] == pytest.approx(7 * 24 * 0.5)
    assert rows[-1]["sum"] == pytest.approx(7 * 24 * 0.5 + (254 - 7 * 24) * 1.0)
    _assert_continuous(rows)


async def test_cost_rewritten_after_price_change(recorder_mock, hass: HomeAssistant, store) -> None:
    """A price change rewrites the cost statistic from the day of the change."""
    meter = _meter(store)
    contract = store.save_contract({"meter_id": meter["id"], "start_date": "2025-01-01", "unit_price": 1.0})
    await _sync(hass)
    rows = await _rows(hass, cost_statistic_id(meter["id"]))
    assert rows[-1]["sum"] == pytest.approx(254.0)

    store.save_contract({"price_changes": [{"date": "2025-06-26", "unit_price": 2.0}]}, contract["id"])
    await _sync(hass)
    rows = await _rows(hass, cost_statistic_id(meter["id"]))
    # 21.-25.06. (5 days) unchanged, from 26.06. twice the price
    assert len(rows) == 254
    assert rows[5 * 24 - 1]["sum"] == pytest.approx(120.0)
    assert rows[5 * 24]["state"] == pytest.approx(2.0)
    assert rows[-1]["sum"] == pytest.approx(120.0 + (254 - 120) * 2.0)
    _assert_continuous(rows)
