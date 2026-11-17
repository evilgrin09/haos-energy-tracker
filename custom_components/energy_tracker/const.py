"""Constants for Energy Tracker."""

from __future__ import annotations

DOMAIN = "energy_tracker"
NAME = "Energy Tracker"
VERSION = "0.6.2"

STORAGE_KEY = f"{DOMAIN}.data"
STORAGE_VERSION = 4

PANEL_URL_PATH = "energy-tracker"
PANEL_COMPONENT = "energy-tracker-panel"
PANEL_ICON = "mdi:meter-electric-outline"
STATIC_URL = f"/{DOMAIN}_static"

CONF_SHOW_PANEL = "show_panel"
CONF_PANEL_TITLE = "panel_title"
CONF_AI_TASK_ENTITY = "ai_task_entity"

METER_TYPES = ["electricity", "gas", "water", "heat", "oil", "other"]
PROFILES = ["auto", "flat", "heating", "electricity"]
UNITS = ["kWh", "MWh", "m³", "L"]

SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"
DATA_STATISTICS = f"{DOMAIN}_statistics"

SERVICE_ADD_READING = "add_reading"
ATTR_METER = "meter"
ATTR_VALUE = "value"
ATTR_DATE = "date"
ATTR_RESET = "reset"
ATTR_NOTE = "note"
