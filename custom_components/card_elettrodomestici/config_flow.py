"""Config flow per Appliance Energy Monitor."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_DEBOUNCE_OFF_S,
    CONF_ENERGY_ENTITY,
    CONF_IMAGE_OFF,
    CONF_IMAGE_ON,
    CONF_NAME,
    CONF_POWER_ENTITY,
    CONF_PRICE_ENTITY,
    CONF_THRESHOLD_W,
    DEFAULT_DEBOUNCE_OFF_S,
    DEFAULT_THRESHOLD_W,
    DOMAIN,
)


def _schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
            vol.Required(CONF_POWER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            vol.Optional(CONF_ENERGY_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Optional(CONF_PRICE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_THRESHOLD_W, default=defaults.get(CONF_THRESHOLD_W, DEFAULT_THRESHOLD_W)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=5000, unit_of_measurement="W")
            ),
            vol.Required(
                CONF_DEBOUNCE_OFF_S,
                default=defaults.get(CONF_DEBOUNCE_OFF_S, DEFAULT_DEBOUNCE_OFF_S),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1800, unit_of_measurement="s")
            ),
            vol.Optional(
                CONF_IMAGE_OFF, default=defaults.get(CONF_IMAGE_OFF, "")
            ): str,
            vol.Optional(
                CONF_IMAGE_ON, default=defaults.get(CONF_IMAGE_ON, "")
            ): str,
        }
    )


class ApplianceEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce la configurazione via UI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return ApplianceEnergyOptionsFlow(config_entry)


class ApplianceEnergyOptionsFlow(config_entries.OptionsFlow):
    """Permette di modificare soglia e debounce dopo la creazione."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self._config_entry, data=data)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init", data_schema=_schema(self._config_entry.data)
        )
