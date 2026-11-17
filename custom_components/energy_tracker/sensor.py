"""Sensors of Energy Tracker (one device per meter)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import EnergyTrackerConfigEntry
from .analysis import meter_overview
from .const import DOMAIN, NAME, SIGNAL_DATA_UPDATED
from .store import TrackerStore

Overview = dict[str, Any]

UNIT_METER = "meter"
UNIT_METER_PER_DAY = "meter_per_day"
UNIT_CURRENCY = "currency"


@dataclass(frozen=True, kw_only=True)
class TrackerSensorDescription(SensorEntityDescription):
    """Describes an Energy Tracker sensor."""

    value_fn: Callable[[Overview], Any]
    attrs_fn: Callable[[Overview], dict[str, Any]] | None = None
    unit_kind: str | None = UNIT_METER


def _summary_attrs(key: str) -> Callable[[Overview], dict[str, Any]]:
    def attrs(ov: Overview) -> dict[str, Any]:
        summary = ov[key]
        return {
            "start": summary["start"],
            "end": summary["end"],
            "measured": round(summary["measured"], 3),
            "estimated": round(summary["estimated"], 3),
            "forecast": round(summary["forecast"], 3),
            "cost": round(summary["cost"], 2) if summary["cost"] is not None else None,
            # share of the days that are covered by a tariff (costs are partial below 100)
            "cost_coverage": round(summary["cost_coverage"] * 100, 1),
        }

    return attrs


def _r(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def _billing_attrs(ov: Overview) -> dict[str, Any]:
    billing = ov["billing"]
    if not billing:
        return {}
    segments = billing["segments"]
    return {
        "billing_year": billing["label"],
        "period_start": billing["start"],
        "period_end": billing["end"],
        "progress": round(billing["progress"] * 100, 1),
        "providers": sorted({seg["provider"] for seg in segments if seg["provider"]}),
        "consumption": round(billing["consumption"]["total"], 2),
        "measured_share": round(billing["measured_share"] * 100, 1),
        "reading_start": _r(billing["reading_start"]),
        "reading_end": _r(billing["reading_end"]),
        "total_cost": round(billing["total_cost"], 2),
        "cost_coverage": round(billing["cost_coverage"] * 100, 1),
        "advance_total": round(billing["advance_total"], 2),
        "payments_count": billing["payments_count"],
        "paid_to_date": round(billing["paid_to_date"], 2),
        "balance": round(billing["balance"], 2),
        "result": billing["result"],
        "recommended_advance": round(billing["recommended_advance"], 2),
    }


def _last_bill_attrs(ov: Overview) -> dict[str, Any]:
    details = ov["last_bill"]
    if not details:
        return {}
    bill = details["bill"]
    comparison = details["comparison"]

    def dev(key: str) -> tuple[float | None, float | None]:
        item = comparison[key]
        return (None, None) if item is None else (_r(item["diff"]), _r(item["pct"], 1))

    balance_eur, _balance_pct = dev("balance")
    cost_eur, cost_pct = dev("total_cost")
    consumption_abs, consumption_pct = dev("consumption")
    return {
        "billing_year": details["label"],
        "period_start": bill["start_date"],
        "period_end": bill["end_date"],
        "consumption": bill.get("consumption"),
        "total_cost": bill.get("total_cost"),
        "advances_paid": bill.get("advances_paid"),
        "new_advance": bill.get("new_advance"),
        "new_advance_from": bill.get("new_advance_from"),
        "forecast_balance": _r(details["own"]["balance"]) if comparison["balance"] else None,
        "deviation_balance": balance_eur,
        "deviation_cost": cost_eur,
        "deviation_cost_pct": cost_pct,
        "deviation_consumption": consumption_abs,
        "deviation_consumption_pct": consumption_pct,
        "cost_coverage": round(comparison["cost_coverage"] * 100, 1),
    }


def _last_reading_attrs(ov: Overview) -> dict[str, Any]:
    reading = ov["last_reading"]
    if not reading:
        return {}
    return {"date": reading["date"], "meter_replaced": reading.get("reset", False)}


def _billing_value(key: str) -> Callable[[Overview], Any]:
    return lambda ov: round(ov["billing"][key], 2) if ov["billing"] else None


SENSORS: tuple[TrackerSensorDescription, ...] = (
    TrackerSensorDescription(
        key="reading",
        translation_key="reading",
        # No state class on purpose: with one it could be picked in the energy
        # dashboard, which would book the whole consumption since the last
        # reading into a single hour.  Use the external statistics instead.
        suggested_display_precision=2,
        value_fn=lambda ov: ov["last_reading"]["value"] if ov["last_reading"] else None,
        attrs_fn=_last_reading_attrs,
    ),
    TrackerSensorDescription(
        key="consumption_month",
        translation_key="consumption_month",
        suggested_display_precision=1,
        value_fn=lambda ov: round(ov["month_to_date"]["total"], 3),
        attrs_fn=_summary_attrs("month_to_date"),
    ),
    TrackerSensorDescription(
        key="consumption_previous_month",
        translation_key="consumption_previous_month",
        suggested_display_precision=1,
        value_fn=lambda ov: round(ov["previous_month"]["total"], 3),
        attrs_fn=_summary_attrs("previous_month"),
    ),
    TrackerSensorDescription(
        key="consumption_year",
        translation_key="consumption_year",
        suggested_display_precision=1,
        value_fn=lambda ov: round(ov["year_to_date"]["total"], 3),
        attrs_fn=_summary_attrs("year_to_date"),
    ),
    TrackerSensorDescription(
        key="forecast_year",
        translation_key="forecast_year",
        suggested_display_precision=0,
        value_fn=lambda ov: round(ov["year_forecast"]["total"], 3),
        attrs_fn=_summary_attrs("year_forecast"),
    ),
    TrackerSensorDescription(
        key="average_daily",
        translation_key="average_daily",
        suggested_display_precision=2,
        unit_kind=UNIT_METER_PER_DAY,
        value_fn=lambda ov: round(ov["average_daily"], 4),
        attrs_fn=lambda ov: {
            "annual_rate": round(ov["annual_rate"], 2),
            "data_quality": ov["quality"],
            "measured_days": ov["measured_days"],
        },
    ),
    TrackerSensorDescription(
        key="billing_cost",
        translation_key="billing_cost",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        unit_kind=UNIT_CURRENCY,
        value_fn=_billing_value("total_cost"),
        attrs_fn=_billing_attrs,
    ),
    TrackerSensorDescription(
        key="billing_balance",
        translation_key="billing_balance",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        unit_kind=UNIT_CURRENCY,
        value_fn=_billing_value("balance"),
        attrs_fn=_billing_attrs,
    ),
    TrackerSensorDescription(
        key="last_bill",
        translation_key="last_bill",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        unit_kind=UNIT_CURRENCY,
        value_fn=lambda ov: _r(ov["last_bill"]["result"]) if ov["last_bill"] else None,
        attrs_fn=_last_bill_attrs,
    ),
)


def _reading_device_class(meter: dict[str, Any]) -> SensorDeviceClass | None:
    unit = meter.get("unit")
    meter_type = meter.get("type")
    if unit in ("kWh", "MWh"):
        return SensorDeviceClass.ENERGY
    if meter_type == "gas" and unit == "m³":
        return SensorDeviceClass.GAS
    if meter_type == "water" and unit in ("m³", "L"):
        return SensorDeviceClass.WATER
    return None


@callback
def _update_device_name(hass: HomeAssistant, meter_id: str, name: str | None) -> None:
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(identifiers={(DOMAIN, meter_id)})
    if device and name and device.name != name:
        dev_reg.async_update_device(device.id, name=name)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnergyTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors and keep them in sync with the configured meters."""
    store = entry.runtime_data
    entities: dict[str, list[TrackerSensor]] = {}

    @callback
    def _sync() -> None:
        new: list[TrackerSensor] = []
        today = dt_util.now().date()
        for meter_id in store.meters:
            overview = meter_overview(store, meter_id, today)
            if meter_id not in entities:
                entities[meter_id] = [
                    TrackerSensor(store, meter_id, description, overview) for description in SENSORS
                ]
                new.extend(entities[meter_id])
            else:
                _update_device_name(hass, meter_id, overview["meter"].get("name"))
                for entity in entities[meter_id]:
                    entity.update_overview(overview)

        removed = [meter_id for meter_id in entities if meter_id not in store.meters]
        if removed:
            ent_reg = er.async_get(hass)
            dev_reg = dr.async_get(hass)
            for meter_id in removed:
                for entity in entities.pop(meter_id):
                    if entity.registry_entry:
                        ent_reg.async_remove(entity.entity_id)
                    else:
                        hass.async_create_task(entity.async_remove())
                if device := dev_reg.async_get_device(identifiers={(DOMAIN, meter_id)}):
                    dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_DATA_UPDATED, _sync))


class TrackerSensor(SensorEntity):
    """A sensor derived from the readings of a meter."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: TrackerSensorDescription

    def __init__(
        self,
        store: TrackerStore,
        meter_id: str,
        description: TrackerSensorDescription,
        overview: Overview,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._store = store
        self._meter_id = meter_id
        self._overview = overview
        self._attr_unique_id = f"{meter_id}_{description.key}"
        meter = overview["meter"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, meter_id)},
            name=meter.get("name"),
            manufacturer=NAME,
            model=meter.get("type"),
            serial_number=meter.get("number") or None,
            entry_type=DeviceEntryType.SERVICE,
        )
        if description.key == "reading":
            self._attr_device_class = _reading_device_class(meter)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit."""
        kind = self.entity_description.unit_kind
        unit = self._overview["meter"].get("unit")
        if kind == UNIT_METER:
            return unit
        if kind == UNIT_METER_PER_DAY:
            return f"{unit}/d"
        if kind == UNIT_CURRENCY:
            return self.hass.config.currency
        return None

    @property
    def available(self) -> bool:
        """Billing sensors need a tariff in the period, the last bill sensor a bill."""
        key = self.entity_description.key
        if key == "last_bill":
            last_bill = self._overview["last_bill"]
            return last_bill is not None and last_bill["result"] is not None
        if self.entity_description.unit_kind == UNIT_CURRENCY:
            billing = self._overview["billing"]
            return billing is not None and (billing["cost_coverage"] > 0 or billing["payments_count"] > 0)
        return True

    @property
    def native_value(self) -> Any:
        """Return the state."""
        return self.entity_description.value_fn(self._overview)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self._overview)

    @callback
    def update_overview(self, overview: Overview) -> None:
        """Receive new data."""
        self._overview = overview
        if self.hass is not None and self.entity_id:
            self.async_write_ha_state()
