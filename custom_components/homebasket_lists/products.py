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

    def search(self, text: str, limit: int = 6) -> list[dict[str, Any]]:
        """Return the products whose name, brand or category matches `text`.

        Unlike `match`, this is for offering choices to a person, so a partial
        match is what is wanted.
        """
        if (api := self.api) is None or not str(text or "").strip():
            return []
        return api.find(text)[:limit]

    async def async_details(self, code: str | None) -> dict[str, Any] | None:
        """Return the cached Open Food Facts record for a product."""
        if not code or (api := self.api) is None:
            return None
        return await api.async_get_details(code)

    async def async_scan(self, code: str) -> dict[str, Any] | None:
        """Run a barcode through HomeBasket and return what it is.

        HomeBasket resolves the code the way its own scanner does - the local
        dictionary first, then the Open Food Facts family, remembering what it
        finds - but nothing is put on HomeBasket's own list: what to do with
        the answer is this list's business.

        Returns None when HomeBasket is not installed.
        """
        if (api := self.api) is None:
            return None
        return await api.async_resolve(code, add_to_list=False, source="homebasket_lists")

    async def async_photo(self, code: str | None) -> str | None:
        """Return a photo stored for a product, as a data URL."""
        if not code or (api := self.api) is None:
            return None
        return await api.async_get_photo(code)
