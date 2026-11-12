"""Read meter number and meter reading from a photo.

The image recognition itself is done by the AI Task integration of Home
Assistant (any provider that supports attachments).  Assigning the photo to a
meter is done here by comparing the recognised meter number with the meter
numbers stored for the configured meters.
"""

from __future__ import annotations

import asyncio
from difflib import SequenceMatcher
from http import HTTPStatus
import logging
import mimetypes
from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

from aiohttp import web
from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.util import slugify
import voluptuous as vol

from .const import CONF_AI_TASK_ENTITY, DOMAIN
from .store import TrackerError, TrackerStore

_LOGGER = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
RECOGNITION_TIMEOUT = 120
MEDIA_SUBDIR = DOMAIN
TMP_SUBDIR = "tmp"
TMP_MAX_AGE = 24 * 3600
PHOTO_ID_RE = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{2,5}$")

# Folder / file names of the photo archive per energy carrier
CARRIER_NAMES = {
    "de": {
        "electricity": "strom",
        "gas": "gas",
        "water": "wasser",
        "heat": "waerme",
        "oil": "heizoel",
        "other": "sonstiges",
    },
    "en": {
        "electricity": "electricity",
        "gas": "gas",
        "water": "water",
        "heat": "heat",
        "oil": "oil",
        "other": "other",
    },
}

MATCH_EXACT = "exact"
MATCH_PARTIAL = "partial"
MATCH_FUZZY = "fuzzy"
MATCH_SINGLE = "single"
MATCH_NONE = "none"

MIN_PARTIAL_LENGTH = 5
FUZZY_THRESHOLD = 0.85

INSTRUCTIONS = """\
The attached photo shows a household utility meter (electricity, gas, water, \
heat or similar). Read the following from the photo:

- meter_number: the serial number / meter number printed or engraved on the \
meter. It is often next to a barcode or labelled "Nr.", "No.", "Zähler-Nr.", \
"Eigentumsnummer" or "Serial". Return it exactly as printed, without spaces. \
Do not return type designations, approval marks or the year of manufacture.
- value: the current meter reading as a decimal number using "." as decimal \
separator and no thousands separator. Read every digit of the register, \
including leading zeros. Digits shown in red, inside a red frame or after a \
comma are decimal places. Small dial pointers are decimal places as well and \
may be ignored. On digital electricity meters use the total import register \
(OBIS 1.8.0), never the current power (W) or the export register (2.8.0).
- unit: the unit of the reading as printed on the meter, e.g. kWh, m³, MWh.

Only report what is visible. If something cannot be read reliably, return an \
empty string for it.
"""


def normalize_number(number: str | None) -> str:
    """Reduce a meter number to upper case letters and digits."""
    return re.sub(r"[^0-9A-Z]", "", str(number or "").upper())


def match_meter(meters: list[dict[str, Any]], number: str | None) -> tuple[dict[str, Any] | None, str]:
    """Find the meter belonging to a recognised meter number.

    Returns the meter (or None) and how it was matched.
    """
    wanted = normalize_number(number)
    numbered = [(m, normalize_number(m.get("number"))) for m in meters]
    numbered = [(m, n) for m, n in numbered if n]

    if wanted:
        exact = [m for m, n in numbered if n == wanted]
        if len(exact) == 1:
            return exact[0], MATCH_EXACT

        # The photo often shows only a part of the number (or additional
        # prefixes such as the manufacturer code).
        partial = [
            m
            for m, n in numbered
            if min(len(n), len(wanted)) >= MIN_PARTIAL_LENGTH and (n in wanted or wanted in n)
        ]
        if len(partial) == 1:
            return partial[0], MATCH_PARTIAL

        # Tolerate single misread characters (0/O, 1/I, 8/B ...).
        scored = sorted(
            ((SequenceMatcher(None, n, wanted).ratio(), m) for m, n in numbered),
            key=lambda item: item[0],
            reverse=True,
        )
        if scored and scored[0][0] >= FUZZY_THRESHOLD:
            runner_up = scored[1][0] if len(scored) > 1 else 0.0
            if scored[0][0] - runner_up >= 0.05:
                return scored[0][1], MATCH_FUZZY

    if len(meters) == 1:
        return meters[0], MATCH_SINGLE
    return None, MATCH_NONE


def parse_reading_value(value: Any) -> float | None:
    """Parse a reading returned by the model ("012345,6", "12 345.6 kWh")."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    text = re.sub(r"[^0-9.,]", "", str(value))
    if not text:
        return None
    if "," in text and "." in text:
        # the last separator is the decimal separator
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    if text.count(".") > 1:
        head, _, tail = text.rpartition(".")
        text = head.replace(".", "") + "." + tail
    try:
        return float(text)
    except ValueError:
        return None


def build_instructions(store: TrackerStore) -> str:
    """Build the task instructions including the known meters as a hint."""
    lines = []
    for meter in store.meters.values():
        readings = store.meter_readings(meter["id"])
        last = readings[-1] if readings else None
        parts = [
            f"meter number {meter['number']}" if meter.get("number") else "unknown number",
            str(meter.get("type")),
            f"unit {meter.get('unit')}",
        ]
        if last:
            parts.append(f"last reading {last['value']} on {last['date']}")
        lines.append("- " + ", ".join(parts))
    if not lines:
        return INSTRUCTIONS
    return (
        INSTRUCTIONS + "\nKnown meters of this household. Use them only to check plausibility "
        "(a new reading is normally slightly higher than the last one, which helps "
        "to place the decimal point). Always report what the photo shows:\n" + "\n".join(lines)
    )


STRUCTURE = vol.Schema(
    {
        vol.Optional(
            "meter_number", description="Meter / serial number as printed on the meter"
        ): selector.TextSelector(),
        vol.Optional(
            "value", description="Meter reading as decimal number with '.' as separator"
        ): selector.TextSelector(),
        vol.Optional("unit", description="Unit of the reading, e.g. kWh or m³"): selector.TextSelector(),
    }
)


def _write_image(directory: Path, name: str, content: bytes) -> Path:
    """Store an uploaded photo temporarily and drop forgotten uploads."""
    directory.mkdir(parents=True, exist_ok=True)
    limit = time.time() - TMP_MAX_AGE
    for old in directory.iterdir():
        if old.is_file() and old.stat().st_mtime < limit:
            old.unlink(missing_ok=True)
    path = directory / name
    path.write_bytes(content)
    return path


def media_root(hass: HomeAssistant) -> tuple[str, Path]:
    """Return id and path of the media directory used for photos."""
    media_dirs = hass.config.media_dirs
    dir_id = "local" if "local" in media_dirs else next(iter(media_dirs), None)
    if dir_id is None:
        raise TrackerError("no_media_dir", "No media directory is configured")
    return dir_id, Path(media_dirs[dir_id])


def archive_relative_path(
    meter: dict[str, Any],
    meters: list[dict[str, Any]],
    reading: dict[str, Any],
    extension: str,
    language: str,
) -> str:
    """Path of an archived photo below the media directory.

    ``energy_tracker/<carrier>/<year>/<month>/<yyyymmdd>-<carrier>.<ext>``.
    If there are several meters of the same kind the meter name is appended.
    """
    names = CARRIER_NAMES["de" if language.startswith("de") else "en"]
    meter_type = meter.get("type", "other")
    carrier = names.get(meter_type, names["other"])
    day = str(reading["date"])
    name = f"{day.replace('-', '')}-{carrier}"
    if sum(1 for m in meters if m.get("type") == meter_type) > 1:
        name += f"-{slugify(str(meter.get('name') or meter['id']), separator='-')}"
    if reading.get("reset"):
        name += "-wechsel" if language.startswith("de") else "-replaced"
    return f"{MEDIA_SUBDIR}/{carrier}/{day[0:4]}/{day[5:7]}/{name}{extension}"


def _move_photo(source: Path, target: Path) -> bool:
    if not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)
    return True


async def async_archive_photo(
    hass: HomeAssistant, store: TrackerStore, photo_id: str, reading: dict[str, Any]
) -> str | None:
    """Move an uploaded photo into the archive and link it to the reading."""
    if not PHOTO_ID_RE.match(photo_id):
        raise TrackerError("invalid_format", "Invalid photo id")
    dir_id, root = media_root(hass)
    meter = store.meters[reading["meter_id"]]
    relative = archive_relative_path(
        meter,
        list(store.meters.values()),
        reading,
        Path(photo_id).suffix,
        hass.config.language,
    )
    source = root / MEDIA_SUBDIR / TMP_SUBDIR / photo_id
    if not await hass.async_add_executor_job(_move_photo, source, root / relative):
        return None
    media_id = f"media-source://media_source/{dir_id}/{relative}"
    store.set_reading_photo(reading["id"], media_id)
    return media_id


async def async_discard_photo(hass: HomeAssistant, photo_id: str) -> None:
    """Delete an uploaded photo that is not needed any more."""
    if not PHOTO_ID_RE.match(photo_id):
        return
    _dir_id, root = media_root(hass)
    path = root / MEDIA_SUBDIR / TMP_SUBDIR / photo_id
    await hass.async_add_executor_job(lambda: path.unlink(missing_ok=True))


def _configured_entity(hass: HomeAssistant) -> str | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entity_id := entry.options.get(CONF_AI_TASK_ENTITY):
            return entity_id
    return None


async def async_recognize(
    hass: HomeAssistant, store: TrackerStore, content: bytes, content_type: str
) -> dict[str, Any]:
    """Recognise meter number and reading on a photo and match the meter."""
    if "ai_task" not in hass.config.components:
        raise TrackerError("ai_task_missing", "The AI Task integration is not set up")
    try:
        from homeassistant.components import ai_task
    except ImportError as err:
        raise TrackerError("ai_task_missing", "AI Task is not available") from err

    dir_id, root = media_root(hass)
    extension = mimetypes.guess_extension(content_type, strict=False) or ".jpg"
    if not re.fullmatch(r"\.[a-z0-9]{2,5}", extension):
        extension = ".jpg"
    name = f"{uuid4().hex}{extension}"
    directory = root / MEDIA_SUBDIR / TMP_SUBDIR
    keep = False
    path = await hass.async_add_executor_job(_write_image, directory, name, content)
    try:
        async with asyncio.timeout(RECOGNITION_TIMEOUT):
            result = await ai_task.async_generate_data(
                hass,
                task_name="Energy Tracker meter photo",
                entity_id=_configured_entity(hass),
                instructions=build_instructions(store),
                structure=STRUCTURE,
                attachments=[
                    {
                        "media_content_id": f"media-source://media_source/{dir_id}/{MEDIA_SUBDIR}/{TMP_SUBDIR}/{name}",
                        "media_content_type": content_type,
                    }
                ],
            )
        keep = True
    except TimeoutError as err:
        raise TrackerError("recognition_failed", "The AI model did not answer in time") from err
    except HomeAssistantError as err:
        code = "no_ai_entity" if "entity" in str(err).lower() else "recognition_failed"
        raise TrackerError(code, str(err)) from err
    finally:
        if not keep:
            await hass.async_add_executor_job(lambda: path.unlink(missing_ok=True))

    data = result.data if isinstance(result.data, dict) else {}
    _LOGGER.debug("Meter photo recognised: %s", data)
    number = str(data.get("meter_number") or "").strip()
    meter, match = match_meter(list(store.meters.values()), number)
    return {
        "meter_number": number,
        "value": parse_reading_value(data.get("value")),
        "unit": str(data.get("unit") or "").strip(),
        "meter_id": meter["id"] if meter else None,
        "match": match,
        # The photo is kept until the reading is saved (then it is archived)
        # or the dialog is cancelled.
        "photo_id": name,
    }


class RecognizeView(HomeAssistantView):
    """Receive a meter photo and return what was recognised."""

    url = f"/api/{DOMAIN}/recognize"
    name = f"api:{DOMAIN}:recognize"

    async def post(self, request: web.Request) -> web.Response:
        """Handle the photo upload (raw image as request body)."""
        hass = request.app[KEY_HASS]
        store: TrackerStore | None = hass.data.get(DOMAIN)
        if store is None:
            return self._error("not_loaded", "Energy Tracker is not set up", HTTPStatus.NOT_FOUND)
        if not request[KEY_HASS_USER].is_admin:
            return self._error("unauthorized", "Admin access required", HTTPStatus.FORBIDDEN)
        content_type = request.content_type or ""
        if not content_type.startswith("image/"):
            return self._error("invalid_image", "Request body must be an image")
        if (request.content_length or 0) > MAX_IMAGE_BYTES:
            return self._error("invalid_image", "Image is too large")
        content = await request.read()
        if not content or len(content) > MAX_IMAGE_BYTES:
            return self._error("invalid_image", "Image is empty or too large")
        try:
            return self.json(await async_recognize(hass, store, content, content_type))
        except TrackerError as err:
            return self._error(err.code, str(err))

    def _error(self, code: str, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> web.Response:
        return self.json({"code": code, "message": message}, status_code=status)
