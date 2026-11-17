"""Tests for the CSV import (iOS app "Energy Tracker" and simple format)."""

from datetime import date
from pathlib import Path

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.energy_tracker.const import DATA_STATISTICS, DOMAIN
from custom_components.energy_tracker.energy_stats import consumption_statistic_id
from custom_components.energy_tracker.importer import (
    build_preview,
    parse_csv,
    parse_datetime,
    parse_number,
    rows_to_import,
    suggest_meter,
)

FIXTURES = Path(__file__).parent / "fixtures" / "energy_tracker_ios"
STROM = "Nebenkosten___Strom_-_Za_hlersta_nde.csv"
GAS = "Nebenkosten___Gas_-_Za_hlersta_nde.csv"
WASSER = "Nebenkosten___Wasser_-_Za_hlersta_nde.csv"


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ------------------------------------------------------------------ parsing


@pytest.mark.parametrize(
    ("name", "lines", "days", "merged_lines", "first", "last_value"),
    [
        (STROM, 44, 41, 3, (date(2024, 1, 1), 29286.9), 39379.2),
        (GAS, 36, 36, 0, (date(2024, 1, 1), 9149.25), 10915.83),
        (WASSER, 38, 37, 1, (date(2024, 1, 1), 483.0), 748.0),
    ],
)
def test_ios_export_files(name, lines, days, merged_lines, first, last_value) -> None:
    """The original export files of the iOS app are read completely."""
    parsed = parse_csv(_text(name))
    assert parsed.header is True
    assert parsed.delimiter == ";"
    assert parsed.rejected == []
    assert parsed.data_lines == lines
    assert len(parsed.rows) == days
    assert sum(m["count"] - 1 for m in parsed.merged) == merged_lines
    assert (parsed.rows[0].day, parsed.rows[0].value) == first
    assert parsed.rows[-1].day == date(2026, 11, 2)
    assert parsed.rows[-1].value == last_value
    # ascending, one row per day, never decreasing in these files
    days_seen = [row.day for row in parsed.rows]
    assert days_seen == sorted(set(days_seen))
    preview = build_preview(parsed, [], False)
    assert preview["flagged"] == []
    assert preview["new"] == days
    assert preview["start"] == "2024-01-01"
    assert preview["end"] == "2026-11-02"


def test_same_day_latest_time_wins() -> None:
    """Morning and evening readings: the evening value is used."""
    parsed = parse_csv(_text(STROM))
    by_day = {row.day: row.value for row in parsed.rows}
    assert by_day[date(2024, 7, 1)] == 30833.6  # 18:33, not 07:50
    assert by_day[date(2024, 7, 2)] == 30842.6  # 20:02, not 08:09
    assert by_day[date(2024, 7, 3)] == 30851.1  # 20:01, not 08:03
    assert by_day[date(2024, 7, 4)] == 30854.0
    assert [m["date"] for m in parsed.merged] == ["2024-07-01", "2024-07-02", "2024-07-03"]
    assert parsed.merged[0] == {
        "date": "2024-07-01",
        "count": 2,
        "kept": 30833.6,
        "dropped": [30829.2],
    }
    # identical duplicate lines in the water file
    water = parse_csv(_text(WASSER))
    assert water.merged == [{"date": "2025-09-08", "count": 2, "kept": 623.0, "dropped": [623.0]}]


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("Nebenkosten / Strom - Zählerstände.csv", ("Strom", "electricity", "kWh")),
        (STROM, ("Strom", "electricity", "kWh")),
        (GAS, ("Gas", "gas", "m³")),
        (WASSER, ("Wasser", "water", "m³")),
        ("Nebenkosten__Wasser_-_Za_hlersta_nde.csv", ("Wasser", "water", "m³")),
        ("Haus / Wärmepumpe Wärme - Zählerstände.csv", ("Wärmepumpe Wärme", "heat", "kWh")),
        ("Haus___Heizo_l_-_Za_hlersta_nde.csv", ("Heizo l", "oil", "L")),
        ("Heizöl.csv", ("Heizöl", "oil", "L")),
        ("werte.csv", ("werte", "other", "kWh")),
    ],
)
def test_suggest_meter(filename, expected) -> None:
    """Name, type and unit are derived from the file name."""
    suggestion = suggest_meter(filename)
    assert (suggestion["name"], suggestion["type"], suggestion["unit"]) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("39379,2", 39379.2),
        ("748", 748.0),
        ("10915,83", 10915.83),
        ("10.915,83", 10915.83),
        ("10,915.83", 10915.83),
        ("1.234.567", 1234567.0),
        ("12 345,6", 12345.6),
        ("abc", None),
        ("", None),
        ("12,3,4x", None),
    ],
)
def test_parse_number(text, expected) -> None:
    """Numbers with decimal comma or point."""
    assert parse_number(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-11-02 17:36:10", "2026-11-02T17:36:10"),
        ("2026-11-02T17:36:10+01:00", "2026-11-02T17:36:10"),
        ("2026-11-02", "2026-11-02T00:00:00"),
        ("02.11.2026 17:36", "2026-11-02T17:36:00"),
        ("2.1.2026", "2026-01-02T00:00:00"),
        ("2026-02-30", None),
        ("Datum", None),
    ],
)
def test_parse_datetime(text, expected) -> None:
    """Dates with and without time."""
    result = parse_datetime(text)
    assert (f"{result[0].isoformat()}T{result[1].isoformat()}" if result else None) == expected


def test_simple_format_and_rejections() -> None:
    """Text field format: optional header, time, BOM; bad lines are reported."""
    text = (
        "﻿date;value;reset;note\r\n"
        "2025-01-01 08:00;100,5;0;Start\r\n"
        "01.02.2025;120;;\r\n"
        "15.03.2025;0;wechsel;neuer Zähler\r\n"
        "2025-04-01;abc;0;\r\n"
        "gestern;5;0;\r\n"
        "2025-05-01;;0;\r\n"
        "2025-06-01;-3;0;\r\n"
        "nur eine spalte\r\n"
    )
    parsed = parse_csv(text)
    assert parsed.header is True
    assert [(r.day.isoformat(), r.value, r.reset, r.note) for r in parsed.rows] == [
        ("2025-01-01", 100.5, False, "Start"),
        ("2025-02-01", 120.0, False, ""),
        ("2025-03-15", 0.0, True, "neuer Zähler"),
    ]
    assert [(r["line"], r["reason"]) for r in parsed.rejected] == [
        (5, "invalid_value"),
        (6, "invalid_date"),
        (7, "missing_value"),
        (8, "negative_value"),
        (9, "too_few_columns"),
    ]
    assert parsed.data_lines == 8

    # without header, tab and comma separated, third column as note
    assert [r.value for r in parse_csv("2025-01-01\t5,5\n2025-01-02\t6").rows] == [5.5, 6.0]
    assert [r.value for r in parse_csv("2025-01-01,5.5\n2025-01-02,6").rows] == [5.5, 6.0]
    row = parse_csv("2025-01-01;7;Keller").rows[0]
    assert (row.reset, row.note) == (False, "Keller")
    assert parse_csv("").rows == []


def test_preview_against_existing_readings() -> None:
    """Existing dates are skipped, implausible values are flagged."""
    parsed = parse_csv("2025-01-01;100\n2025-02-01;150\n2025-03-01;90\n2025-04-01;120\n2025-05-01;400")
    existing = [
        {"date": "2025-02-01", "value": 150.0, "reset": False},
        {"date": "2025-04-15", "value": 130.0, "reset": False},
    ]
    preview = build_preview(parsed, existing, False)
    assert preview["skipped_existing"] == ["2025-02-01"]
    assert preview["new"] == 4
    assert [(f["date"], f["reason"], f["other_date"]) for f in preview["flagged"]] == [
        ("2025-03-01", "lower_than_previous", "2025-02-01"),
    ]

    # nothing is imported without a decision for the flagged value
    rows, undecided = rows_to_import(parsed, existing, False, {})
    assert undecided == ["2025-03-01"]

    rows, undecided = rows_to_import(parsed, existing, False, {"2025-03-01": "reset"})
    assert undecided == []
    assert [(r["date"], r["reset"]) for r in rows] == [
        ("2025-01-01", False),
        ("2025-03-01", True),
        ("2025-04-01", False),
        ("2025-05-01", False),
    ]
    rows, _ = rows_to_import(parsed, existing, False, {"2025-03-01": "skip"})
    assert [r["date"] for r in rows] == ["2025-01-01", "2025-04-01", "2025-05-01"]
    rows, _ = rows_to_import(parsed, existing, False, {"2025-03-01": "keep"})
    assert [(r["date"], r["reset"]) for r in rows][1] == ("2025-03-01", False)

    # a new value above the following stored reading is flagged as well
    preview = build_preview(parse_csv("2025-04-10;500"), existing, False)
    assert [(f["date"], f["reason"]) for f in preview["flagged"]] == [("2025-04-10", "higher_than_next")]

    # replacing ignores the stored readings
    preview = build_preview(parsed, existing, True)
    assert preview["skipped_existing"] == []
    assert preview["new"] == 5
    assert preview["replaced"] == 2


# ----------------------------------------------------------------- websocket


@pytest.fixture
async def ws(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    hass_ws_client,
):
    """Set up recorder and integration, return a websocket helper."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, options={"show_panel": False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)

    async def call(msg_type: str, **data):
        await client.send_json_auto_id({"type": f"{DOMAIN}/{msg_type}", **data})
        return await client.receive_json()

    yield call
    await hass.config_entries.async_unload(entry.entry_id)


async def test_import_ios_files(recorder_mock, hass: HomeAssistant, ws) -> None:
    """Import the three files into new meters and check readings and statistics."""
    store = hass.data[DOMAIN]
    expected = {
        STROM: ("Strom", "electricity", "kWh", 41, 3, 39379.2),
        GAS: ("Gas", "gas", "m³", 36, 0, 10915.83),
        WASSER: ("Wasser", "water", "m³", 37, 1, 748.0),
    }
    meter_ids = {}
    for name, (meter_name, meter_type, unit, days, merged, last) in expected.items():
        msg = await ws("import/preview", name=name, text=_text(name), suggest=True)
        assert msg["success"], msg
        preview = msg["result"]
        assert preview["meter_id"] is None  # no meter yet: create one
        assert preview["suggestion"] == {
            "name": meter_name,
            "type": meter_type,
            "unit": unit,
            "meter_id": None,
        }
        assert (preview["days"], preview["new"], preview["merged_lines"]) == (days, days, merged)
        assert (preview["start"], preview["end"]) == ("2024-01-01", "2026-11-02")
        assert preview["last_value"] == last
        assert preview["rejected"] == []
        assert preview["flagged"] == []
        assert not store.meters or name != STROM  # preview changes nothing

        msg = await ws(
            "import/commit",
            text=_text(name),
            new_meter={"name": meter_name, "meter_type": meter_type, "unit": unit},
        )
        assert msg["success"], msg
        assert msg["result"]["added"] == days
        assert msg["result"]["skipped"] == 0
        assert msg["result"]["merged_lines"] == merged
        meter_ids[name] = msg["result"]["meter_id"]

        readings = store.meter_readings(meter_ids[name])
        assert len(readings) == days
        assert (readings[-1]["date"], readings[-1]["value"]) == ("2026-11-02", last)
        assert store.meters[meter_ids[name]]["unit"] == unit

    # importing the same file again: suggested meter is found, everything skipped
    msg = await ws("import/preview", name=STROM, text=_text(STROM), suggest=True)
    assert msg["result"]["meter_id"] == meter_ids[STROM]
    assert msg["result"]["new"] == 0
    assert len(msg["result"]["skipped_existing"]) == 41
    msg = await ws("import/commit", text=_text(STROM), meter_id=meter_ids[STROM])
    assert (msg["result"]["added"], msg["result"]["skipped"]) == (0, 41)

    # replace: same result, nothing doubled
    msg = await ws("import/preview", text=_text(STROM), meter_id=meter_ids[STROM], replace=True)
    assert (msg["result"]["new"], msg["result"]["replaced"]) == (41, 41)
    msg = await ws("import/commit", text=_text(STROM), meter_id=meter_ids[STROM], replace=True)
    assert msg["result"]["added"] == 41
    assert len(store.meter_readings(meter_ids[STROM])) == 41

    # statistics for the energy dashboard are recalculated from the import
    await hass.data[DATA_STATISTICS].async_sync()
    await async_wait_recording_done(hass)
    sid = consumption_statistic_id(meter_ids[STROM])
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utc_from_timestamp(0),
        None,
        {sid},
        "hour",
        None,
        {"sum"},
    )
    rows = stats[sid]
    # first hour: 2024-01-02 00:00 Berlin, measured total until 2026-11-02
    assert dt_util.utc_from_timestamp(rows[0]["start"]).isoformat() == "2024-01-01T23:00:00+00:00"
    end_of_measured = dt_util.parse_datetime("2026-11-02T22:00:00+00:00").timestamp()
    measured = next(r for r in rows if r["start"] == end_of_measured)
    assert measured["sum"] == pytest.approx(39379.2 - 29286.9)


async def test_import_needs_decision(recorder_mock, hass: HomeAssistant, ws) -> None:
    """Decreasing values are neither dropped nor imported without a decision."""
    text = (
        "Datum;Zählerstand;Beschreibung\n"
        "2025-03-01 10:00:00;20;neu\n"
        "2025-02-01 10:00:00;500;\n"
        "2025-01-01 10:00:00;450;\n"
    )
    msg = await ws("import/preview", name="Wasser.csv", text=text, suggest=True)
    assert [f["date"] for f in msg["result"]["flagged"]] == ["2025-03-01"]

    new_meter = {"name": "Wasser", "meter_type": "water", "unit": "m³"}
    msg = await ws("import/commit", text=text, new_meter=new_meter)
    assert not msg["success"]
    assert msg["error"]["code"] == "import_undecided"
    assert hass.data[DOMAIN].meters == {}

    msg = await ws("import/commit", text=text, new_meter=new_meter, decisions={"2025-03-01": "reset"})
    assert msg["success"], msg
    readings = hass.data[DOMAIN].meter_readings(msg["result"]["meter_id"])
    assert [(r["date"], r["value"], r["reset"], r["note"]) for r in readings] == [
        ("2025-01-01", 450.0, False, ""),
        ("2025-02-01", 500.0, False, ""),
        ("2025-03-01", 20.0, True, "neu"),
    ]

    msg = await ws("import/commit", text="nichts brauchbares", new_meter=new_meter)
    assert msg["error"]["code"] == "import_empty"
