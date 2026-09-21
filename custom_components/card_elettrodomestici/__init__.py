"""Appliance Energy Monitor."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

JS_FILENAME = "appliance-energy-card.js"
JS_URL_PATH = f"/{DOMAIN}_files/{JS_FILENAME}"
_FRONTEND_REGISTERED = "_frontend_registered"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Chiamata una sola volta all'avvio: pubblica il file JS della card senza intervento manuale."""
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_FRONTEND_REGISTERED):
        return True

    local_path = str(Path(__file__).parent / "www" / JS_FILENAME)

    try:
        # API moderna (Home Assistant recenti)
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(JS_URL_PATH, local_path, False)]
        )
    except ImportError:
        # Fallback per versioni di Home Assistant meno recenti
        hass.http.register_static_path(JS_URL_PATH, local_path, cache_headers=False)

    add_extra_js_url(hass, JS_URL_PATH)
    hass.data[DOMAIN][_FRONTEND_REGISTERED] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
