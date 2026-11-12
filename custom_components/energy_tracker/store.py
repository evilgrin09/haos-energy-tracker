"""Persistent data handling for Energy Tracker."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .calc import ConsumptionModel, Tariff, build_model, build_tariff, parse_date
from .const import SIGNAL_DATA_UPDATED, STORAGE_KEY, STORAGE_VERSION


class TrackerError(Exception):
    """Validation error with a translatable code."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize the error."""
        super().__init__(message)
        self.code = code


METER_FIELDS = ("name", "type", "unit", "profile", "annual_estimate", "number", "icon")
READING_FIELDS = ("meter_id", "date", "value", "reset", "note")
CONTRACT_FIELDS = (
    "meter_id",
    "provider",
    "tariff",
    "customer_number",
    "start_date",
    "end_date",
    "billing_months",
    "unit_price",
    "base_price",
    "advance_payment",
    "conversion_factor",
    "notice_period",
    "note",
)


def _new_id() -> str:
    return uuid4().hex


class TrackerStore:
    """Holds meters, readings and contracts and persists them."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.meters: dict[str, dict[str, Any]] = {}
        self.readings: dict[str, dict[str, Any]] = {}
        self.contracts: dict[str, dict[str, Any]] = {}
        self._models: dict[str, ConsumptionModel] = {}

    async def async_load(self) -> None:
        """Load data from disk."""
        data = await self._store.async_load() or {}
        self.meters = {m["id"]: m for m in data.get("meters", [])}
        self.readings = {r["id"]: r for r in data.get("readings", [])}
        self.contracts = {c["id"]: c for c in data.get("contracts", [])}

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "meters": list(self.meters.values()),
            "readings": list(self.readings.values()),
            "contracts": list(self.contracts.values()),
        }

    @callback
    def _changed(self) -> None:
        """Persist and notify listeners."""
        self._models.clear()
        self._store.async_delay_save(self._data_to_save, 1)
        async_dispatcher_send(self.hass, SIGNAL_DATA_UPDATED)

    async def async_flush(self) -> None:
        """Write pending changes immediately."""
        await self._store.async_save(self._data_to_save())

    async def async_remove(self) -> None:
        """Remove the storage file."""
        await self._store.async_remove()

    # ------------------------------------------------------------------ meters

    @callback
    def save_meter(self, data: dict[str, Any], meter_id: str | None = None) -> dict[str, Any]:
        """Create or update a meter."""
        if meter_id:
            if meter_id not in self.meters:
                raise TrackerError("not_found", f"Meter {meter_id} not found")
            meter = self.meters[meter_id]
        else:
            meter = {"id": _new_id(), "created": date.today().isoformat()}
            self.meters[meter["id"]] = meter
        for key in METER_FIELDS:
            if key in data:
                meter[key] = data[key]
        meter.setdefault("profile", "auto")
        self._changed()
        return meter

    @callback
    def delete_meter(self, meter_id: str) -> None:
        """Delete a meter including readings and contracts."""
        if meter_id not in self.meters:
            raise TrackerError("not_found", f"Meter {meter_id} not found")
        del self.meters[meter_id]
        self.readings = {k: v for k, v in self.readings.items() if v["meter_id"] != meter_id}
        self.contracts = {k: v for k, v in self.contracts.items() if v["meter_id"] != meter_id}
        self._changed()

    @callback
    def find_meter(self, key: str) -> dict[str, Any] | None:
        """Find a meter by id, name or meter number (case insensitive)."""
        if key in self.meters:
            return self.meters[key]
        lowered = key.strip().lower()
        for meter in self.meters.values():
            if lowered in (
                str(meter.get("name", "")).lower(),
                str(meter.get("number") or "").lower(),
            ):
                return meter
        return None

    # ---------------------------------------------------------------- readings

    @callback
    def meter_readings(self, meter_id: str) -> list[dict[str, Any]]:
        """Return the readings of a meter sorted by date."""
        return sorted(
            (r for r in self.readings.values() if r["meter_id"] == meter_id),
            key=lambda r: (r["date"], bool(r.get("reset"))),
        )

    @callback
    def check_reading(
        self,
        meter_id: str,
        day: date,
        value: float,
        reset: bool,
        exclude_id: str | None = None,
    ) -> None:
        """Validate a reading against the existing ones."""
        others = [r for r in self.meter_readings(meter_id) if r["id"] != exclude_id]
        for other in others:
            if parse_date(other["date"]) == day and bool(other.get("reset")) == reset:
                raise TrackerError("duplicate_date", "There is already a reading for this date")
        key = (day, reset)
        previous = None
        following = None
        for other in others:
            other_key = (parse_date(other["date"]), bool(other.get("reset")))
            if other_key < key:
                previous = other
            elif following is None:
                following = other
        if not reset and previous is not None and value < float(previous["value"]):
            raise TrackerError(
                "value_too_low",
                f"Value is lower than the previous reading ({previous['value']} on {previous['date']})",
            )
        if following is not None and not following.get("reset") and value > float(following["value"]):
            raise TrackerError(
                "value_too_high",
                f"Value is higher than the next reading ({following['value']} on {following['date']})",
            )

    @callback
    def save_reading(
        self,
        data: dict[str, Any],
        reading_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Create or update a reading."""
        existing = self.readings.get(reading_id) if reading_id else None
        if reading_id and existing is None:
            raise TrackerError("not_found", f"Reading {reading_id} not found")
        merged = {**(existing or {}), **{k: data[k] for k in READING_FIELDS if k in data}}
        meter_id = merged.get("meter_id")
        if meter_id not in self.meters:
            raise TrackerError("not_found", f"Meter {meter_id} not found")
        day = parse_date(merged["date"])
        value = float(merged["value"])
        reset = bool(merged.get("reset", False))
        if force:
            for other in self.meter_readings(meter_id):
                if (
                    other["id"] != reading_id
                    and parse_date(other["date"]) == day
                    and bool(other.get("reset")) == reset
                ):
                    raise TrackerError("duplicate_date", "There is already a reading for this date")
        else:
            self.check_reading(meter_id, day, value, reset, reading_id)
        reading = existing or {"id": _new_id()}
        reading.update(
            {
                "meter_id": meter_id,
                "date": day.isoformat(),
                "value": value,
                "reset": reset,
                "note": merged.get("note") or "",
            }
        )
        self.readings[reading["id"]] = reading
        self._changed()
        return reading

    @callback
    def import_readings(
        self, meter_id: str, rows: list[dict[str, Any]], replace: bool = False
    ) -> dict[str, int]:
        """Bulk import readings, skipping existing dates."""
        if meter_id not in self.meters:
            raise TrackerError("not_found", f"Meter {meter_id} not found")
        if replace:
            self.readings = {k: v for k, v in self.readings.items() if v["meter_id"] != meter_id}
        existing = {(r["date"], bool(r.get("reset"))) for r in self.meter_readings(meter_id)}
        added = skipped = 0
        for row in rows:
            day = parse_date(row["date"]).isoformat()
            reset = bool(row.get("reset", False))
            if (day, reset) in existing:
                skipped += 1
                continue
            reading = {
                "id": _new_id(),
                "meter_id": meter_id,
                "date": day,
                "value": float(row["value"]),
                "reset": reset,
                "note": row.get("note") or "",
            }
            self.readings[reading["id"]] = reading
            existing.add((day, reset))
            added += 1
        self._changed()
        return {"added": added, "skipped": skipped}

    @callback
    def delete_reading(self, reading_id: str) -> None:
        """Delete a reading."""
        if self.readings.pop(reading_id, None) is None:
            raise TrackerError("not_found", f"Reading {reading_id} not found")
        self._changed()

    # --------------------------------------------------------------- contracts

    @callback
    def meter_contracts(self, meter_id: str) -> list[dict[str, Any]]:
        """Return contracts of a meter sorted by start date."""
        return sorted(
            (c for c in self.contracts.values() if c["meter_id"] == meter_id),
            key=lambda c: c["start_date"],
        )

    @callback
    def save_contract(self, data: dict[str, Any], contract_id: str | None = None) -> dict[str, Any]:
        """Create or update a contract."""
        if contract_id:
            if contract_id not in self.contracts:
                raise TrackerError("not_found", f"Contract {contract_id} not found")
            contract = self.contracts[contract_id]
        else:
            contract = {"id": _new_id()}
        merged = {**contract, **{k: data[k] for k in CONTRACT_FIELDS if k in data}}
        if merged.get("meter_id") not in self.meters:
            raise TrackerError("not_found", f"Meter {merged.get('meter_id')} not found")
        start = parse_date(merged["start_date"])
        if merged.get("end_date") and parse_date(merged["end_date"]) < start:
            raise TrackerError("invalid_dates", "End date is before start date")
        contract.update(merged)
        self.contracts[contract["id"]] = contract
        self._changed()
        return contract

    @callback
    def delete_contract(self, contract_id: str) -> None:
        """Delete a contract."""
        if self.contracts.pop(contract_id, None) is None:
            raise TrackerError("not_found", f"Contract {contract_id} not found")
        self._changed()

    # ------------------------------------------------------------ calculations

    @callback
    def model(self, meter_id: str) -> ConsumptionModel:
        """Return the (cached) consumption model of a meter."""
        if meter_id not in self._models:
            self._models[meter_id] = build_model(self.meter_readings(meter_id), self.meters[meter_id])
        return self._models[meter_id]

    @callback
    def tariffs(self, meter_id: str) -> list[Tariff]:
        """Return the tariffs of a meter."""
        return [build_tariff(c) for c in self.meter_contracts(meter_id)]

    @callback
    def active_contract(self, meter_id: str, today: date) -> dict[str, Any] | None:
        """Return the contract valid today, or the most recent one."""
        contracts = self.meter_contracts(meter_id)
        if not contracts:
            return None
        valid = [
            c
            for c in contracts
            if parse_date(c["start_date"]) <= today
            and (not c.get("end_date") or parse_date(c["end_date"]) >= today)
        ]
        if valid:
            return valid[-1]
        started = [c for c in contracts if parse_date(c["start_date"]) <= today]
        return started[-1] if started else contracts[0]
