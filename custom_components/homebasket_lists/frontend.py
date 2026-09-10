"""Serve the dashboard card from inside the integration.

Shipping the card here means one HACS entry instead of two, no Lovelace
resource to add by hand, and no stale copy in a browser cache: the URL carries
the integration's version and the file is served without cache headers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "homebasket-lists-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"
_REGISTERED = f"{DOMAIN}_frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Publish the card and load it on every dashboard."""
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True

    path = Path(__file__).parent / "frontend" / CARD_FILE
    if not path.is_file():
        _LOGGER.error("The dashboard card is missing at %s", path)
        return

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(path), False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    _LOGGER.info(
        "Dashboard card registered at %s?v=%s - reload the page to pick it up",
        CARD_URL,
        VERSION,
    )
