"""Costanti per Appliance Energy Monitor."""

DOMAIN = "card_elettrodomestici"

CONF_NAME = "name"
CONF_POWER_ENTITY = "power_entity"
CONF_ENERGY_ENTITY = "energy_entity"
CONF_PRICE_ENTITY = "price_entity"
CONF_THRESHOLD_W = "threshold_w"
CONF_DEBOUNCE_OFF_S = "debounce_off_s"

DEFAULT_THRESHOLD_W = 15
DEFAULT_DEBOUNCE_OFF_S = 180

PLATFORMS = ["binary_sensor", "sensor"]


def signal_active_on(entry_id: str) -> str:
    """Nome del segnale dispatcher inviato quando l'elettrodomestico si accende (dopo debounce)."""
    return f"{DOMAIN}_{entry_id}_active_on"
