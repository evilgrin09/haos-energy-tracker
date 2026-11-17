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

from . import analysis, importer
from .calc import FORECAST_METHODS, GRANULARITIES
from .const import DOMAIN, METER_TYPES, PROFILES
from .photo import PHOTO_ID_RE, async_archive_photo, async_discard_photo
from .store import TrackerError, TrackerStore

_DATE = vol.All(cv.string, cv.date)
_OPT_FLOAT = vol.Any(None, vol.Coerce(float))
_OPT_STR = vol.Any(None, cv.string)
# empty: keep the previous price
_OPT_PRICE = vol.Any(None, "", vol.Coerce(float))

METER_SCHEMA = {
    vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=100)),
    # "type" is reserved by the websocket protocol
    vol.Optional("meter_type"): vol.In(METER_TYPES),
    vol.Optional("unit"): vol.All(cv.string, vol.Length(min=1, max=20)),
    vol.Optional("profile"): vol.In(PROFILES),
    vol.Optional("annual_estimate"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
    vol.Optional("number"): _OPT_STR,
    vol.Optional("icon"): _OPT_STR,
    vol.Optional("billing_day"): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
    vol.Optional("billing_month"): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
    vol.Optional("forecast_method"): vol.In(FORECAST_METHODS),
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
    vol.Optional("unit_price"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("base_price"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("advance_payment"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("conversion_factor"): vol.All(vol.Coerce(float), vol.Range(min=0.0001)),
    vol.Optional("payments_per_year"): vol.All(vol.Coerce(int), vol.In([11, 12])),
    vol.Optional("payment_day"): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
    vol.Optional("first_payment"): vol.Any(None, "", _DATE),
    vol.Optional("advance_changes"): [
        {
            vol.Required("date"): _DATE,
            vol.Required("amount"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        }
    ],
    vol.Optional("price_changes"): [
        {
            vol.Required("date"): _DATE,
            vol.Optional("unit_price"): _OPT_PRICE,
            vol.Optional("base_price"): _OPT_PRICE,
            vol.Optional("conversion_factor"): _OPT_PRICE,
            vol.Optional("note"): _OPT_STR,
        }
    ],
    vol.Optional("notice_period"): _OPT_STR,
    vol.Optional("note"): _OPT_STR,
}

BILL_SCHEMA = {
    vol.Optional("meter_id"): cv.string,
    vol.Optional("start_date"): _DATE,
    vol.Optional("end_date"): _DATE,
    vol.Optional("consumption"): _OPT_FLOAT,
    vol.Optional("consumption_unit"): vol.In(["meter", "billing"]),
    vol.Optional("total_cost"): _OPT_FLOAT,
    vol.Optional("advances_paid"): _OPT_FLOAT,
    # positive: refund, negative: additional payment; None: calculated
    vol.Optional("balance"): _OPT_FLOAT,
    vol.Optional("new_advance"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
    vol.Optional("new_advance_from"): vol.Any(None, "", _DATE),
    # meter readings and prices according to the bill (information / control)
    vol.Optional("reading_start"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
    vol.Optional("reading_end"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
    # the end reading of the bill is an estimate of the utility: not taken over
    vol.Optional("reading_end_estimated"): cv.boolean,
    vol.Optional("unit_price"): _OPT_FLOAT,
    vol.Optional("base_price"): _OPT_FLOAT,
    vol.Optional("conversion_factor"): _OPT_FLOAT,
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
        "bills": list(store.bills.values()),
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


def _suggest_target(store: TrackerStore, name: str) -> dict[str, Any]:
    """Suggest name, type, unit and an existing meter for an import file."""
    suggestion: dict[str, Any] = importer.suggest_meter(name)
    meters = list(store.meters.values())
    wanted = suggestion["name"].casefold()
    match = [m for m in meters if str(m.get("name", "")).casefold() == wanted]
    if len(match) != 1 and suggestion["type"] != "other":
        match = [m for m in meters if m.get("type") == suggestion["type"]]
    suggestion["meter_id"] = match[0]["id"] if len(match) == 1 else None
    return suggestion


_IMPORT_TEXT = vol.All(cv.string, vol.Length(max=2_000_000))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/import/preview",
        vol.Required("text"): _IMPORT_TEXT,
        vol.Optional("name", default=""): cv.string,
        vol.Optional("meter_id"): vol.Any(None, cv.string),
        vol.Optional("suggest", default=False): cv.boolean,
        vol.Optional("replace", default=False): cv.boolean,
    }
)
@websocket_api.require_admin
@callback
@_handler
def ws_import_preview(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Analyse a CSV text and show what an import would do (changes nothing)."""
    suggestion = _suggest_target(store, msg["name"])
    meter_id = msg.get("meter_id")
    if msg["suggest"] and not meter_id:
        meter_id = suggestion["meter_id"]
    if meter_id and meter_id not in store.meters:
        raise TrackerError("not_found", f"Meter {meter_id} not found")
    parsed = importer.parse_csv(msg["text"])
    existing = store.meter_readings(meter_id) if meter_id else []
    return {
        "name": msg["name"],
        "meter_id": meter_id,
        "suggestion": suggestion,
        **importer.build_preview(parsed, existing, msg["replace"]),
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/import/commit",
        vol.Required("text"): _IMPORT_TEXT,
        vol.Optional("meter_id"): vol.Any(None, cv.string),
        vol.Optional("new_meter"): {
            vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=100)),
            vol.Required("meter_type"): vol.In(METER_TYPES),
            vol.Required("unit"): vol.All(cv.string, vol.Length(min=1, max=20)),
        },
        vol.Optional("replace", default=False): cv.boolean,
        vol.Optional("decisions", default=dict): {cv.string: vol.In(importer.DECISIONS)},
    }
)
@websocket_api.require_admin
@callback
@_handler
def ws_import_commit(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Import a CSV text into an existing or a new meter."""
    meter_id = msg.get("meter_id")
    new_meter = msg.get("new_meter")
    if not meter_id and not new_meter:
        raise TrackerError("invalid_format", "Either meter_id or new_meter is required")
    if meter_id and meter_id not in store.meters:
        raise TrackerError("not_found", f"Meter {meter_id} not found")
    parsed = importer.parse_csv(msg["text"])
    if not parsed.rows:
        raise TrackerError("import_empty", "No valid readings found")
    existing = store.meter_readings(meter_id) if meter_id else []
    rows, undecided = importer.rows_to_import(parsed, existing, msg["replace"], msg["decisions"])
    if undecided:
        raise TrackerError("import_undecided", f"Decision missing for: {', '.join(undecided)}")
    if not meter_id:
        meter_id = store.save_meter(
            {"name": new_meter["name"], "type": new_meter["meter_type"], "unit": new_meter["unit"]}
        )["id"]
    # import_readings notifies listeners, which also recalculates the
    # statistics for the energy dashboard
    skipped = len(importer.build_preview(parsed, existing, msg["replace"])["skipped_existing"])
    result = store.import_readings(meter_id, rows, msg["replace"])
    return {
        "meter_id": meter_id,
        "added": result["added"],
        # days that already had a reading (existing readings are kept)
        "skipped": skipped + result["skipped"],
        "merged_lines": sum(m["count"] - 1 for m in parsed.merged),
        "rejected": len(parsed.rejected),
    }


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
    for key in ("end_date", "first_payment"):
        if data.get(key) == "":
            data[key] = None
    if "advance_changes" in data:
        data["advance_changes"] = [
            {"date": c["date"].isoformat(), "amount": c["amount"]} for c in msg["advance_changes"]
        ]
    if "price_changes" in data:
        data["price_changes"] = [{**c, "date": c["date"].isoformat()} for c in msg["price_changes"]]
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
        vol.Required("type"): f"{DOMAIN}/bill/save",
        vol.Optional("bill_id"): cv.string,
        # store the meter readings of the bill as readings (where none exist)
        vol.Optional("take_readings", default=False): cv.boolean,
        **BILL_SCHEMA,
    }
)
@websocket_api.require_admin
@callback
@_handler
def ws_bill_save(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Create or update a bill of the utility."""
    data = _dates_to_str(msg)
    bill_id = data.pop("bill_id", None)
    take_readings = data.pop("take_readings", False)
    if data.get("new_advance_from") == "":
        data["new_advance_from"] = None
    if not bill_id:
        for key in ("meter_id", "start_date", "end_date"):
            if key not in data:
                raise TrackerError("invalid_format", f"Missing field {key}")
    bill = store.save_bill(data, bill_id)
    readings = store.readings_from_bill(bill) if take_readings else []
    return {**bill, "imported_readings": readings}


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/bill/delete", vol.Required("bill_id"): cv.string}
)
@websocket_api.require_admin
@callback
@_handler
def ws_bill_delete(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> None:
    """Delete a bill."""
    store.delete_bill(msg["bill_id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/billing",
        vol.Required("meter_id"): cv.string,
        vol.Optional("period_index"): vol.Coerce(int),
    }
)
@callback
@_handler
def ws_billing(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Return the billing periods of a meter and the calculation of one period."""
    return analysis.meter_billing(store, msg["meter_id"], dt_util.now().date(), msg.get("period_index"))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cost_history",
        vol.Optional("meter_id"): vol.Any(None, cv.string),
        vol.Optional("mode", default="calendar"): vol.In(["calendar", "billing"]),
    }
)
@callback
@_handler
def ws_cost_history(hass: HomeAssistant, store: TrackerStore, msg: dict[str, Any]) -> dict[str, Any]:
    """Return the cost development over the years."""
    return analysis.cost_history(store, dt_util.now().date(), msg.get("meter_id"), msg["mode"])


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
        ws_import_preview,
        ws_import_commit,
        ws_reading_delete,
        ws_contract_save,
        ws_contract_delete,
        ws_bill_save,
        ws_bill_delete,
        ws_statistics,
        ws_billing,
        ws_cost_history,
    ):
        websocket_api.async_register_command(hass, command)
