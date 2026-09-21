"""Sensori cicli (giorno/settimana/mese) e costo stimato."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.util.dt as dt_util

from .const import (
    CONF_ENERGY_ENTITY,
    CONF_NAME,
    CONF_PRICE_ENTITY,
    DOMAIN,
    signal_active_on,
)


def _period_key(period: str, now: datetime) -> str:
    if period == "day":
        return now.date().isoformat()
    if period == "week":
        iso = now.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if period == "month":
        return f"{now.year}-{now.month:02d}"
    raise ValueError(period)


class _CycleCounterSensor(SensorEntity, RestoreEntity):
    """Contatore cicli con reset automatico a inizio giorno/settimana/mese."""

    _attr_should_poll = False
    _attr_native_unit_of_measurement = "cicli"
    _attr_state_class = SensorStateClass.TOTAL

    _LABELS = {"day": "oggi", "week": "settimana", "month": "mese"}

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, period: str) -> None:
        self._hass = hass
        self._entry = entry
        self._period = period
        self._name = entry.data[CONF_NAME]

        self._attr_unique_id = f"{entry.entry_id}_cicli_{period}"
        self._attr_name = f"{self._name} cicli {self._LABELS[period]}"
        self._count = 0
        self._current_key = _period_key(period, dt_util.now())

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)}, name=self._name)

    @property
    def native_value(self) -> int:
        return self._count

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            stored_key = last_state.attributes.get("period_key")
            if stored_key == self._current_key:
                try:
                    self._count = int(float(last_state.state))
                except (TypeError, ValueError):
                    self._count = 0

        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, signal_active_on(self._entry.entry_id), self._handle_cycle
            )
        )
        self.async_on_remove(
            async_track_time_interval(
                self._hass, self._check_rollover, timedelta(minutes=15)
            )
        )

    @property
    def extra_state_attributes(self) -> dict:
        return {"period_key": self._current_key}

    @callback
    def _maybe_reset(self) -> None:
        new_key = _period_key(self._period, dt_util.now())
        if new_key != self._current_key:
            self._current_key = new_key
            self._count = 0

    @callback
    def _handle_cycle(self) -> None:
        self._maybe_reset()
        self._count += 1
        self.async_write_ha_state()

    @callback
    def _check_rollover(self, _now) -> None:
        before = self._current_key
        self._maybe_reset()
        if self._current_key != before:
            self.async_write_ha_state()


class ApplianceCostSensor(SensorEntity):
    """Costo stimato = energia totale (kWh) x prezzo attuale (€/kWh)."""

    _attr_should_poll = False
    _attr_native_unit_of_measurement = "€"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._name = entry.data[CONF_NAME]
        self._energy_entity = entry.data.get(CONF_ENERGY_ENTITY)
        self._price_entity = entry.data.get(CONF_PRICE_ENTITY)

        self._attr_unique_id = f"{entry.entry_id}_costo"
        self._attr_name = f"{self._name} costo stimato"
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)}, name=self._name)

    @property
    def available(self) -> bool:
        return bool(self._energy_entity and self._price_entity)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if not self.available:
            return
        self._recompute()
        self.async_on_remove(
            async_track_state_change_event(
                self._hass,
                [self._energy_entity, self._price_entity],
                self._handle_change,
            )
        )

    @callback
    def _handle_change(self, _event) -> None:
        self._recompute()
        self.async_write_ha_state()

    @callback
    def _recompute(self) -> None:
        energy_state = self._hass.states.get(self._energy_entity)
        price_state = self._hass.states.get(self._price_entity)
        try:
            energy = float(energy_state.state)
            price = float(price_state.state)
        except (AttributeError, TypeError, ValueError):
            self._attr_native_value = None
            return
        self._attr_native_value = round(energy * price, 2)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    entities = [
        _CycleCounterSensor(hass, entry, "day"),
        _CycleCounterSensor(hass, entry, "week"),
        _CycleCounterSensor(hass, entry, "month"),
        ApplianceCostSensor(hass, entry),
    ]
    async_add_entities(entities)
