"""Appliance Energy Monitor."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.loader import async_get_integration

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

JS_FILENAME = "appliance-energy-card.js"
JS_URL_PATH = f"/{DOMAIN}_files/{JS_FILENAME}"
_FRONTEND_REGISTERED = "_frontend_registered"
_RESOURCE_DONE = "_resource_done"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Pubblica il file JS della card e prova a registrarla come vera risorsa Lovelace."""
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_FRONTEND_REGISTERED):
        return True
    hass.data[DOMAIN][_FRONTEND_REGISTERED] = True
    hass.data[DOMAIN][_RESOURCE_DONE] = False

    local_path = str(Path(__file__).parent / "www" / JS_FILENAME)

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(JS_URL_PATH, local_path, False)]
        )
    except ImportError:
        hass.http.register_static_path(JS_URL_PATH, local_path, cache_headers=False)

    integration = await async_get_integration(hass, DOMAIN)
    versioned_url = f"{JS_URL_PATH}?v={integration.version}"

    # Meccanismo 1, sempre attivo (confermato funzionante da browser):
    # iniezione diretta nello scheletro HTML del frontend.
    add_extra_js_url(hass, versioned_url)
    add_extra_js_url(hass, versioned_url, es5=True)

    # Meccanismo 2: registrarla anche come vera voce in "Gestisci le
    # risorse" (lo stesso sistema di Tapparella/Pergola), per la massima
    # compatibilità con client come la WebView dell'app mobile.
    # Tentiamo in più momenti diversi, ognuno protetto da errori indipendenti,
    # così se uno dei modi di "capire quando è il momento giusto" sbaglia
    # (succede facilmente con le API interne di Home Assistant, che cambiano
    # da una versione all'altra), gli altri due restano di riserva.
    async def _try_register(label: str, _event=None) -> None:
        if hass.data[DOMAIN].get(_RESOURCE_DONE):
            return
        _LOGGER.warning("Card Elettrodomestici: tentativo registrazione risorsa (%s)", label)
        ok = await _async_ensure_lovelace_resource(hass, versioned_url)
        if ok:
            hass.data[DOMAIN][_RESOURCE_DONE] = True

    # Tentativo immediato
    hass.async_create_task(_try_register("immediato"))
    # Tentativo agli eventi di avvio (uno dei due sicuramente non è ancora passato)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, lambda e: hass.async_create_task(_try_register("evento start", e)))
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, lambda e: hass.async_create_task(_try_register("evento started", e)))
    # Tentativi ritardati, nel caso Lovelace non fosse ancora pronto nei punti sopra
    for delay in (10, 30, 60):
        async_call_later(hass, delay, lambda _now, d=delay: hass.async_create_task(_try_register(f"ritardo {d}s")))

    return True


async def _async_ensure_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Ritorna True se la risorsa risulta registrata (già presente o appena creata)."""
    try:
        lovelace_data = hass.data.get("lovelace")
        if lovelace_data is None:
            _LOGGER.warning("Card Elettrodomestici: 'lovelace' non ancora in hass.data, riprovo più tardi.")
            return False

        resources = getattr(lovelace_data, "resources", None)
        if resources is None and isinstance(lovelace_data, dict):
            resources = lovelace_data.get("resources")
        if resources is None:
            _LOGGER.warning(
                "Card Elettrodomestici: impossibile trovare le risorse Lovelace (struttura dati non riconosciuta): %r",
                type(lovelace_data),
            )
            return False

        await resources.async_get_info()
        base_url = url.split("?")[0]
        items = list(resources.async_items())

        for item in items:
            if base_url in item.get("url", ""):
                if item["url"] != url:
                    await resources.async_update_item(item["id"], {"url": url})
                _LOGGER.warning("Card Elettrodomestici: risorsa già presente, aggiornata se serviva.")
                return True

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.warning("Card Elettrodomestici: risorsa Lovelace creata con successo.")
        return True

    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "Card Elettrodomestici: tentativo di registrazione risorsa fallito con eccezione."
        )
        return False


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
