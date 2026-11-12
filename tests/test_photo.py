"""Tests for reading meters from photos."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_tracker.const import DOMAIN
from custom_components.energy_tracker.photo import (
    archive_relative_path,
    match_meter,
    normalize_number,
    parse_reading_value,
)

METERS = [
    {"id": "el", "name": "Strom", "type": "electricity", "number": "1EMH00 1234 5678"},
    {"id": "gas", "name": "Gas", "type": "gas", "number": "7GKT-0098765"},
    {"id": "water", "name": "Wasser", "type": "water", "number": None},
]


def test_normalize_number() -> None:
    """Spaces, dashes and case are ignored."""
    assert normalize_number(" 1emh00 1234-5678 ") == "1EMH0012345678"
    assert normalize_number(None) == ""


@pytest.mark.parametrize(
    ("number", "meter_id", "match"),
    [
        ("1EMH0012345678", "el", "exact"),
        ("1emh 0012 3456 78", "el", "exact"),
        ("12345678", "el", "partial"),  # only a part is visible
        ("DE 7GKT0098765 2021", "gas", "partial"),  # additional characters
        ("7GKT0098766", "gas", "fuzzy"),  # one digit misread
        ("1EMHO012345678", "el", "fuzzy"),  # O instead of 0
        ("99999999", None, "none"),
        ("", None, "none"),
    ],
)
def test_match_meter(number: str, meter_id: str | None, match: str) -> None:
    """Meters are found by their number."""
    meter, how = match_meter(METERS, number)
    assert how == match
    assert (meter["id"] if meter else None) == meter_id


def test_match_single_meter() -> None:
    """With only one meter it is preselected even without number."""
    meter, how = match_meter([METERS[2]], "")
    assert meter["id"] == "water"
    assert how == "single"


def test_match_ambiguous_is_not_guessed() -> None:
    """Two equally similar meters are not matched."""
    meters = [{"id": "a", "number": "12345670"}, {"id": "b", "number": "12345671"}]
    assert match_meter(meters, "12345672") == (None, "none")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("012345.6", 12345.6),
        ("012345,6", 12345.6),
        ("12.345,67", 12345.67),
        ("12,345.67", 12345.67),
        ("1.234.567", 1234.567),
        ("25600 kWh", 25600.0),
        (345.2, 345.2),
        ("", None),
        ("unreadable", None),
        (None, None),
    ],
)
def test_parse_reading_value(raw, expected) -> None:
    """Readings are parsed tolerant to formatting."""
    assert parse_reading_value(raw) == expected


@pytest.fixture
async def client(hass: HomeAssistant, hass_client, enable_custom_integrations, tmp_path: Path):
    """Set up the integration with a meter and return an http client."""
    hass.config.media_dirs = {"local": str(tmp_path)}
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, options={"ai_task_entity": "ai_task.test"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    store = hass.data[DOMAIN]
    meter = store.save_meter(
        {"name": "Strom", "type": "electricity", "unit": "kWh", "number": "1EMH0012345678"}
    )
    store.save_meter({"name": "Gas", "type": "gas", "unit": "m³", "number": "7GKT0098765"})
    store.save_reading({"meter_id": meter["id"], "date": "2025-01-01", "value": 1000})
    return await hass_client(), meter, tmp_path


async def test_recognize_view(hass: HomeAssistant, client, hass_ws_client) -> None:
    """A photo is sent to AI Task and matched to the meter."""
    http, meter, tmp_path = client
    hass.config.components.add("ai_task")
    seen = {}

    async def generate(hass, **kwargs):
        seen.update(kwargs)
        media_id = kwargs["attachments"][0]["media_content_id"]
        seen["file_existed"] = (tmp_path / DOMAIN / "tmp" / media_id.rsplit("/", 1)[1]).is_file()
        return SimpleNamespace(data={"meter_number": "1EMH00 1234 5678", "value": "001234,5", "unit": "kWh"})

    with patch("homeassistant.components.ai_task.async_generate_data", side_effect=generate):
        resp = await http.post(
            f"/api/{DOMAIN}/recognize", data=b"\xff\xd8fake", headers={"Content-Type": "image/jpeg"}
        )
    assert resp.status == 200
    result = await resp.json()
    photo_id = result.pop("photo_id")
    assert result == {
        "meter_number": "1EMH00 1234 5678",
        "value": 1234.5,
        "unit": "kWh",
        "meter_id": meter["id"],
        "match": "exact",
    }
    assert seen["entity_id"] == "ai_task.test"
    assert seen["file_existed"]
    assert "1EMH0012345678" in seen["instructions"]
    assert "last reading 1000.0" in seen["instructions"]
    assert seen["attachments"][0]["media_content_id"] == (
        f"media-source://media_source/local/{DOMAIN}/tmp/{photo_id}"
    )
    # the photo is kept until the reading is saved or the dialog is cancelled
    tmp_file = tmp_path / DOMAIN / "tmp" / photo_id
    assert tmp_file.is_file()

    # saving the reading moves the photo into the archive
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reading/save",
            "meter_id": meter["id"],
            "date": "2025-03-07",
            "value": 1234.5,
            "photo_id": photo_id,
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    archived = tmp_path / DOMAIN / "electricity" / "2025" / "03" / "20250307-electricity.jpg"
    assert archived.is_file()
    assert not tmp_file.exists()
    reading = hass.data[DOMAIN].readings[msg["result"]["id"]]
    assert reading["photo"] == (
        f"media-source://media_source/local/{DOMAIN}/electricity/2025/03/20250307-electricity.jpg"
    )

    # a cancelled dialog discards the upload
    other = tmp_path / DOMAIN / "tmp" / ("a" * 32 + ".jpg")
    other.write_bytes(b"x")
    await ws.send_json_auto_id({"type": f"{DOMAIN}/photo/discard", "photo_id": other.name})
    assert (await ws.receive_json())["success"]
    assert not other.exists()

    # path traversal is rejected by the schema
    await ws.send_json_auto_id({"type": f"{DOMAIN}/photo/discard", "photo_id": "../../secrets.yaml"})
    assert not (await ws.receive_json())["success"]


def test_archive_path() -> None:
    """Photos are sorted by energy carrier, year and month."""
    strom = {"id": "a", "name": "Strom Haushalt", "type": "electricity"}
    waermepumpe = {"id": "b", "name": "Wärmepumpe", "type": "electricity"}
    gas = {"id": "c", "name": "Gas", "type": "gas"}
    reading = {"date": "2026-11-12", "reset": False}
    assert (
        archive_relative_path(gas, [strom, gas], reading, ".jpg", "de")
        == "energy_tracker/gas/2026/11/20261112-gas.jpg"
    )
    assert (
        archive_relative_path(strom, [strom, gas], reading, ".png", "de")
        == "energy_tracker/strom/2026/11/20261112-strom.png"
    )
    # several meters of one kind: the meter name keeps the files apart
    assert (
        archive_relative_path(waermepumpe, [strom, waermepumpe, gas], reading, ".jpg", "de")
        == "energy_tracker/strom/2026/11/20261112-strom-warmepumpe.jpg"
    )
    assert (
        archive_relative_path(gas, [gas], {"date": "2026-01-02", "reset": True}, ".jpg", "en")
        == "energy_tracker/gas/2026/01/20260102-gas-replaced.jpg"
    )


async def test_recognize_errors(hass: HomeAssistant, client) -> None:
    """Errors are reported with a code."""
    http, _meter, tmp_path = client
    url = f"/api/{DOMAIN}/recognize"

    resp = await http.post(url, data=b"x", headers={"Content-Type": "image/jpeg"})
    assert resp.status == 400
    assert (await resp.json())["code"] == "ai_task_missing"

    hass.config.components.add("ai_task")
    resp = await http.post(url, data=b"x", headers={"Content-Type": "text/plain"})
    assert (await resp.json())["code"] == "invalid_image"

    with patch(
        "homeassistant.components.ai_task.async_generate_data",
        AsyncMock(side_effect=HomeAssistantError("AI Task entity ai_task.test not found")),
    ):
        resp = await http.post(url, data=b"x", headers={"Content-Type": "image/png"})
    assert resp.status == 400
    assert (await resp.json())["code"] == "no_ai_entity"
    assert not list((tmp_path / DOMAIN / "tmp").iterdir())
