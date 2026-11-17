"""Energy Tracker: manual meter readings, consumption analysis and billing forecast."""

from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
import voluptuous as vol

from . import websocket
from .const import (
    ATTR_DATE,
    ATTR_METER,
    ATTR_NOTE,
    ATTR_RESET,
    ATTR_VALUE,
    CONF_PANEL_TITLE,
    CONF_SHOW_PANEL,
    DATA_STATISTICS,
    DOMAIN,
    NAME,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_URL_PATH,
    SERVICE_ADD_READING,
    SIGNAL_DATA_UPDATED,
    STATIC_URL,
)
from .energy_stats import StatisticsManager, async_clear_meters
from .photo import RecognizeView
from .store import TrackerError, TrackerStore

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_FILE = "energy-tracker-panel.js"

type EnergyTrackerConfigEntry = ConfigEntry[TrackerStore]

ADD_READING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_METER): cv.string,
        vol.Required(ATTR_VALUE): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional(ATTR_DATE): cv.date,
        vol.Optional(ATTR_RESET, default=False): cv.boolean,
        vol.Optional(ATTR_NOTE): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the parts that live independent of the config entry."""
    websocket.async_register(hass)
    hass.http.register_view(RecognizeView())
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), False)])

    async def add_reading(call: ServiceCall) -> ServiceResponse:
        store: TrackerStore | None = hass.data.get(DOMAIN)
        if store is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
        meter = store.find_meter(call.data[ATTR_METER])
        if meter is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="meter_not_found",
                translation_placeholders={"meter": call.data[ATTR_METER]},
            )
        day = call.data.get(ATTR_DATE) or dt_util.now().date()
        try:
            reading = store.save_reading(
                {
                    "meter_id": meter["id"],
                    "date": day.isoformat(),
                    "value": call.data[ATTR_VALUE],
                    "reset": call.data[ATTR_RESET],
                    "note": call.data.get(ATTR_NOTE, ""),
                }
            )
        except TrackerError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_reading",
                translation_placeholders={"message": str(err)},
            ) from err
        return {"reading": reading}

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_READING,
        add_reading,
        schema=ADD_READING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


def _file_hash(directory: Path) -> str:
    """Hash of all frontend modules (the panel imports price-format.js)."""
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.js")):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


async def _async_register_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    version = await hass.async_add_executor_job(_file_hash, FRONTEND_DIR)
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        module_url=f"{STATIC_URL}/{PANEL_FILE}?v={version}",
        sidebar_title=entry.options.get(CONF_PANEL_TITLE, NAME),
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        config={},
    )


async def async_setup_entry(hass: HomeAssistant, entry: EnergyTrackerConfigEntry) -> bool:
    """Set up Energy Tracker from a config entry."""
    store = TrackerStore(hass)
    await store.async_load()
    hass.data[DOMAIN] = store
    entry.runtime_data = store

    if entry.options.get(CONF_SHOW_PANEL, True):
        await _async_register_panel(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Statistics for the energy dashboard: after every change and once per
    # hour (to append the hours that have passed).
    stats = StatisticsManager(hass, store)
    hass.data[DATA_STATISTICS] = stats
    entry.async_on_unload(stats.async_shutdown)
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_DATA_UPDATED, stats.async_schedule))
    entry.async_on_unload(async_track_time_change(hass, stats.async_schedule, minute=1, second=0))
    stats.async_schedule()

    @callback
    def _new_day(_now: datetime) -> None:
        """Refresh values once a day (estimates and forecasts change)."""
        async_dispatcher_send(hass, SIGNAL_DATA_UPDATED)

    entry.async_on_unload(async_track_time_change(hass, _new_day, hour=0, minute=0, second=10))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EnergyTrackerConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
        await entry.runtime_data.async_flush()
        hass.data.pop(DOMAIN, None)
        hass.data.pop(DATA_STATISTICS, None)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete stored data and statistics when the integration is removed.

    Archived photos in the media directory are kept.
    """
    store = TrackerStore(hass)
    await store.async_load()
    async_clear_meters(hass, list(store.meters))
    await store.async_remove()
