"""Appliance Energy Monitor."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

JS_FILENAME = "appliance-energy-card.js"
JS_URL_PATH = f"/{DOMAIN}_files/{JS_FILENAME}"
_FRONTEND_REGISTERED = "_frontend_registered"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Pubblica il file JS della card e la registra come vera risorsa Lovelace."""
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_FRONTEND_REGISTERED):
        return True

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

    # Aspettiamo che Home Assistant abbia finito l'avvio (Lovelace incluso)
    # prima di provare a scrivere una risorsa vera nella sua lista risorse:
    # è lo stesso identico meccanismo di "Gestisci le risorse", ma lo facciamo
    # noi al posto dell'utente, così funziona anche dove l'iniezione
    # automatica lato frontend non arriva (es. alcune WebView mobile).
    async def _register_resource(_event) -> None:
        await _async_ensure_lovelace_resource(hass, versioned_url)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_resource)

    hass.data[DOMAIN][_FRONTEND_REGISTERED] = True
    return True


async def _async_ensure_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    try:
        lovelace_data = hass.data.get("lovelace")
        resources = getattr(lovelace_data, "resources", None) or lovelace_data["resources"]
        if resources is None:
            _LOGGER.warning(
                "Card Elettrodomestici: impossibile trovare le risorse Lovelace; "
                "aggiungi manualmente %s in Impostazioni > Dashboard > Risorse.",
                url,
            )
            return

        await resources.async_get_info()
        base_url = url.split("?")[0]
        already_present = any(
            base_url in item.get("url", "") for item in resources.async_items()
        )
        if already_present:
            # Aggiorna l'URL versionato se è cambiato (nuova release)
            for item in resources.async_items():
                if base_url in item.get("url", "") and item["url"] != url:
                    await resources.async_update_item(item["id"], {"url": url})
            return

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info("Card Elettrodomestici: risorsa Lovelace registrata automaticamente.")
    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "Card Elettrodomestici: registrazione automatica della risorsa fallita. "
            "Aggiungi manualmente %s in Impostazioni > Dashboard > Risorse (Modulo JavaScript).",
            url,
        )


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
