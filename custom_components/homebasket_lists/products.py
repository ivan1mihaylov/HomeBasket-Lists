"""Bridge to the HomeBasket integration.

HomeBasket owns the products; this integration owns the lists. When an item
turns up whose name matches a product HomeBasket knows, the item is linked to
it and the card can show its picture, category and nutrition without this
integration storing any of it.

HomeBasket is optional. Without it everything still works, items simply carry
no product.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import HOMEBASKET_API
from .store import normalize_summary


class ProductLink:
    """Read-only access to HomeBasket, when it is installed."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise the bridge."""
        self.hass = hass

    @property
    def api(self) -> Any | None:
        """Return HomeBasket's API object, or None when it is not set up."""
        return self.hass.data.get(HOMEBASKET_API)

    @property
    def available(self) -> bool:
        """Return whether HomeBasket can be asked at all."""
        return self.api is not None

    def get(self, code: str | None) -> dict[str, Any] | None:
        """Return a product by any of its barcodes."""
        if not code or (api := self.api) is None:
            return None
        return api.get(code)

    def match(self, summary: str) -> dict[str, Any] | None:
        """Return the product an item name refers to, if any.

        Only an exact name match counts. A near match would silently attach
        the wrong nutrition to the wrong item, and the user can always link it
        by hand.
        """
        if (api := self.api) is None:
            return None

        wanted = normalize_summary(summary)
        if not wanted:
            return None

        for product in api.products:
            if normalize_summary(product.get("name")) == wanted:
                return product
        return None

    async def async_details(self, code: str | None) -> dict[str, Any] | None:
        """Return the cached Open Food Facts record for a product."""
        if not code or (api := self.api) is None:
            return None
        return await api.async_get_details(code)

    async def async_photo(self, code: str | None) -> str | None:
        """Return a photo stored for a product, as a data URL."""
        if not code or (api := self.api) is None:
            return None
        return await api.async_get_photo(code)
