"""WebSocket API used by the Energy Tracker panel."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util
import voluptuous as vol

from . import analysis
from .calc import GRANULARITIES
from .const import DOMAIN, METER_TYPES, PROFILES
from .photo import PHOTO_ID_RE, async_archive_photo, async_discard_photo
from .store import TrackerError, TrackerStore

_DATE = vol.All(cv.string, cv.date)
_OPT_FLOAT = vol.Any(None, vol.Coerce(float))
_OPT_STR = vol.Any(None, cv.string)

METER_SCHEMA = {
    vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=100)),
    # "type" is reserved by the websocket protocol
    vol.Optional("meter_type"): vol.In(METER_TYPES),
    vol.Optional("unit"): vol.All(cv.string, vol.Length(min=1, max=20)),
    vol.Optional("profile"): vol.In(PROFILES),
    vol.Optional("annual_estimate"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
    vol.Optional("number"): _OPT_STR,
    vol.Optional("icon"): _OPT_STR,
}

READING_SCHEMA = {
    vol.Optional("meter_id"): cv.string,
    vol.Optional("date"): _DATE,
    vol.Optional("value"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("reset"): cv.boolean,
    vol.Optional("note"): _OPT_STR,
}

CONTRACT_SCHEMA = {
    vol.Optional("meter_id"): cv.string,
    vol.Optional("provider"): _OPT_STR,
    vol.Optional("tariff"): _OPT_STR,
    vol.Optional("customer_number"): _OPT_STR,
    vol.Optional("start_date"): _DATE,
    vol.Optional("end_date"): vol.Any(None, "", _DATE),
    vol.Optional("billing_months"): vol.All(vol.Coerce(int), vol.Range(min=1, max=36)),
    vol.Optional("unit_price"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("base_price"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("advance_payment"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("conversion_factor"): vol.All(vol.Coerce(float), vol.Range(min=0.0001)),
    vol.Optional("notice_period"): _OPT_STR,
    vol.Optional("note"): _OPT_STR,
}


def _store(hass: HomeAssistant) -> TrackerStore:
    store: TrackerStore | None = hass.data.get(DOMAIN)
    if store is None:
        raise TrackerError("not_loaded", "Energy Tracker is not set up")
    return store


def _dates_to_str(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in data.items()
        if key not in ("id", "type")
    }


def _handler(func: Callable[..., Any]) -> Callable[..., None]:
    """Wrap a handler so that tracker errors become websocket errors."""

    @wraps(func)
    def wrapper(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
        try:
            result = func(hass, _store(hass), msg)
        except TrackerError as err:
            connection.send_error(msg["id"], err.code, str(err))
            return
        connection.send_result(msg["id"], result)

    return wrapper


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/data"})
@callback
@_handler
def ws_data(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Return all stored data."""
    return {
        "meters": list(store.meters.values()),
        "readings": sorted(store.readings.values(), key=lambda r: r["date"]),
        "contracts": list(store.contracts.values()),
        "currency": hass.config.currency,
        "photo_available": "ai_task" in hass.config.components,
        "statistics_available": "recorder" in hass.config.components,
        "today": dt_util.now().date().isoformat(),
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/overview"})
@callback
@_handler
def ws_overview(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Return key figures of all meters."""
    return analysis.overview(store, dt_util.now().date())


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/meter/save",
        vol.Optional("meter_id"): cv.string,
        **METER_SCHEMA,
    }
)
@websocket_api.require_admin
@callback
@_handler
def ws_meter_save(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Create or update a meter."""
    data = _dates_to_str(msg)
    meter_id = data.pop("meter_id", None)
    if "meter_type" in data:
        data["type"] = data.pop("meter_type")
    if not meter_id:
        for key in ("name", "type", "unit"):
            if key not in data:
                raise TrackerError("invalid_format", f"Missing field {key}")
    return store.save_meter(data, meter_id)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/meter/delete", vol.Required("meter_id"): cv.string}
)
@websocket_api.require_admin
@callback
@_handler
def ws_meter_delete(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> None:
    """Delete a meter."""
    store.delete_meter(msg["meter_id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/reading/save",
        vol.Optional("reading_id"): cv.string,
        vol.Optional("force", default=False): cv.boolean,
        vol.Optional("photo_id"): vol.All(cv.string, vol.Match(PHOTO_ID_RE)),
        **READING_SCHEMA,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_reading_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Create or update a reading, optionally archiving its photo."""
    data = _dates_to_str(msg)
    reading_id = data.pop("reading_id", None)
    force = data.pop("force", False)
    photo_id = data.pop("photo_id", None)
    try:
        store = _store(hass)
        if not reading_id:
            for key in ("meter_id", "date", "value"):
                if key not in data:
                    raise TrackerError("invalid_format", f"Missing field {key}")
        reading = store.save_reading(data, reading_id, force)
        if photo_id:
            await async_archive_photo(hass, store, photo_id, reading)
    except TrackerError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], reading)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/photo/discard",
        vol.Required("photo_id"): vol.All(cv.string, vol.Match(PHOTO_ID_RE)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_photo_discard(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete an uploaded photo that was not used."""
    try:
        await async_discard_photo(hass, msg["photo_id"])
    except TrackerError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/reading/import",
        vol.Required("meter_id"): cv.string,
        vol.Optional("replace", default=False): cv.boolean,
        vol.Required("readings"): [
            {
                vol.Required("date"): _DATE,
                vol.Required("value"): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional("reset", default=False): cv.boolean,
                vol.Optional("note"): _OPT_STR,
            }
        ],
    }
)
@websocket_api.require_admin
@callback
@_handler
def ws_reading_import(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, int]:
    """Import several readings at once."""
    return store.import_readings(msg["meter_id"], msg["readings"], msg["replace"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/reading/delete", vol.Required("reading_id"): cv.string}
)
@websocket_api.require_admin
@callback
@_handler
def ws_reading_delete(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> None:
    """Delete a reading."""
    store.delete_reading(msg["reading_id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/contract/save",
        vol.Optional("contract_id"): cv.string,
        **CONTRACT_SCHEMA,
    }
)
@websocket_api.require_admin
@callback
@_handler
def ws_contract_save(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Create or update a contract."""
    data = _dates_to_str(msg)
    contract_id = data.pop("contract_id", None)
    if data.get("end_date") == "":
        data["end_date"] = None
    if not contract_id:
        for key in ("meter_id", "start_date"):
            if key not in data:
                raise TrackerError("invalid_format", f"Missing field {key}")
    return store.save_contract(data, contract_id)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/contract/delete", vol.Required("contract_id"): cv.string}
)
@websocket_api.require_admin
@callback
@_handler
def ws_contract_delete(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> None:
    """Delete a contract."""
    store.delete_contract(msg["contract_id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/statistics",
        vol.Required("meter_id"): cv.string,
        vol.Required("start"): _DATE,
        vol.Required("end"): _DATE,
        vol.Required("granularity"): vol.In(GRANULARITIES),
        vol.Optional("compare_start"): _DATE,
        vol.Optional("compare_end"): _DATE,
    }
)
@callback
@_handler
def ws_statistics(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Return aggregated consumption."""
    return analysis.statistics(
        store,
        msg["meter_id"],
        msg["start"],
        msg["end"],
        msg["granularity"],
        dt_util.now().date(),
        msg.get("compare_start"),
        msg.get("compare_end"),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/billing",
        vol.Required("contract_id"): cv.string,
        vol.Optional("period_index"): vol.Coerce(int),
    }
)
@callback
@_handler
def ws_billing(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Return the billing forecast of a contract."""
    return analysis.contract_billing(store, msg["contract_id"], dt_util.now().date(), msg.get("period_index"))


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register all websocket commands."""
    for command in (
        ws_data,
        ws_overview,
        ws_meter_save,
        ws_meter_delete,
        ws_reading_save,
        ws_photo_discard,
        ws_reading_import,
        ws_reading_delete,
        ws_contract_save,
        ws_contract_delete,
        ws_statistics,
        ws_billing,
    ):
        websocket_api.async_register_command(hass, command)
