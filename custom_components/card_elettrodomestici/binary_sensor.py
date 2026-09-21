"""Binary sensor 'in funzione' con debounce sullo spegnimento."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DEBOUNCE_OFF_S,
    CONF_IMAGE_OFF,
    CONF_IMAGE_ON,
    CONF_NAME,
    CONF_POWER_ENTITY,
    CONF_THRESHOLD_W,
    DOMAIN,
    signal_active_on,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    async_add_entities([ApplianceActiveBinarySensor(hass, entry)])


class ApplianceActiveBinarySensor(BinarySensorEntity, RestoreEntity):
    """True se la potenza supera la soglia; torna False solo dopo N secondi sotto soglia."""

    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._name = entry.data[CONF_NAME]
        self._power_entity = entry.data[CONF_POWER_ENTITY]
        self._threshold = float(entry.data[CONF_THRESHOLD_W])
        self._debounce_s = int(entry.data[CONF_DEBOUNCE_OFF_S])
        self._image_off = entry.data.get(CONF_IMAGE_OFF) or None
        self._image_on = entry.data.get(CONF_IMAGE_ON) or None

        self._attr_unique_id = f"{entry.entry_id}_active"
        self._attr_name = f"{self._name} attiva"
        self._attr_is_on = False
        self._off_timer = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._name,
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Espone tutto il necessario alla card: immagini e entità sorelle create da questa integrazione."""
        reg = er.async_get(self._hass)
        entry_id = self._entry.entry_id

        def _find(unique_id: str) -> str | None:
            return reg.async_get_entity_id("sensor", DOMAIN, unique_id)

        attrs = {
            "power_entity": self._power_entity,
            "cycles_day_entity": _find(f"{entry_id}_cicli_day"),
            "cycles_week_entity": _find(f"{entry_id}_cicli_week"),
            "cycles_month_entity": _find(f"{entry_id}_cicli_month"),
            "cost_entity": _find(f"{entry_id}_costo"),
        }
        if self._image_off:
            attrs["image_off"] = self._image_off
        if self._image_on:
            attrs["image_on"] = self._image_on
        return attrs

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

        self.async_on_remove(
            async_track_state_change_event(
                self._hass, [self._power_entity], self._handle_power_change
            )
        )

    @callback
    def _handle_power_change(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        try:
            power = float(new_state.state)
        except (TypeError, ValueError):
            return

        if power > self._threshold:
            # Sopra soglia: annulla un eventuale timer di spegnimento e accendi subito.
            if self._off_timer is not None:
                self._off_timer()
                self._off_timer = None
            if not self._attr_is_on:
                self._attr_is_on = True
                self.async_write_ha_state()
                async_dispatcher_send(self._hass, signal_active_on(self._entry.entry_id))
        else:
            # Sotto soglia: non spegnere subito, aspetta il debounce.
            if self._attr_is_on and self._off_timer is None:
                self._off_timer = async_call_later(
                    self._hass, self._debounce_s, self._debounced_off
                )

    @callback
    def _debounced_off(self, _now) -> None:
        self._off_timer = None
        self._attr_is_on = False
        self.async_write_ha_state()
