"""Serve the dashboard card from inside the integration.

Shipping the card here means one HACS entry instead of two and no Lovelace
resource to add by hand. It is published two ways, because either can be the
one that works on a given installation:

- `add_extra_js_url` loads it on every dashboard;
- a Lovelace resource, which is how a card installed through HACS as a plugin
  gets loaded, for dashboards that only read the resource list.

Both point at the same versioned URL, so the browser fetches it once, and the
card guards its own `customElements.define` against being run twice anyway.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "homebasket-lists-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"
_REGISTERED = f"{DOMAIN}_frontend_registered"

# Safari - and therefore every iPhone - has no barcode reader of its own, so
# one is shipped here for the card to fall back to. It is served from this
# installation rather than a CDN: the camera is pointed at what is in your
# kitchen, and nothing about that should have to leave the house.
ZXING_FILE = "zxing.min.js"
ZXING_URL = f"/{DOMAIN}/{ZXING_FILE}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Publish the card and make the dashboards load it."""
    if hass.data.get(_REGISTERED):
        return

    path = Path(__file__).parent / "frontend" / CARD_FILE
    if not path.is_file():
        _LOGGER.error(
            "The dashboard card is missing at %s. If this came from HACS, "
            "redownload the integration",
            path,
        )
        return

    hass.data[_REGISTERED] = True
    versioned = f"{CARD_URL}?v={VERSION}"

    served = [StaticPathConfig(CARD_URL, str(path), False)]
    reader = path.parent / ZXING_FILE
    if reader.is_file():
        served.append(StaticPathConfig(ZXING_URL, str(reader), True))
    await hass.http.async_register_static_paths(served)
    add_extra_js_url(hass, versioned)
    as_resource = await _async_add_resource(hass, versioned)

    _LOGGER.info(
        "Dashboard card published at %s (Lovelace resource: %s). Reload the "
        "page to pick it up",
        versioned,
        "yes" if as_resource else "no, dashboards in YAML mode need it by hand",
    )


async def _async_add_resource(hass: HomeAssistant, url: str) -> bool:
    """Add the card to the Lovelace resource list, in storage mode.

    Returns False when the dashboards are configured in YAML, where the list is
    read-only and the user adds the resource themselves.
    """
    resources = _resources(hass)
    if resources is None:
        return False

    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        for item in resources.async_items():
            if str(item.get("url", "")).split("?")[0] != CARD_URL:
                continue
            # Ours already, from an earlier version: point it at this one.
            if item["url"] != url:
                await resources.async_update_item(item["id"], {"url": url})
            return True

        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception:  # noqa: BLE001 - the extra_js_url route may still work
        _LOGGER.debug("Could not add the Lovelace resource", exc_info=True)
        return False
    return True


def _resources(hass: HomeAssistant) -> Any | None:
    """Return Lovelace's resource collection, whichever shape it has."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return None

    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")

    # YAML mode has a collection without the create/update methods.
    if resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources
