"""Bridge to the HomeBasket integration.

HomeBasket owns the products; this integration owns the lists. When an item
turns up whose name matches a product HomeBasket knows, the item is linked to
it and the card can show its picture, category and nutrition without this
integration storing any of it.

HomeBasket is optional. Without it everything still works, items simply carry
no product.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DEPARTMENTS, HOMEBASKET_API, LOCAL_PREFIX, PRODUCT_KINDS
from .store import normalize_summary

_LOGGER = logging.getLogger(__name__)


def is_local(code: str | None) -> bool:
    """Return whether a product code is HomeBasket's own key, not a barcode.

    A product a list configured has no barcode until someone gives it one in
    the HomeBasket card.
    """
    return str(code or "").startswith(LOCAL_PREFIX)


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

    async def async_kind(self, code: str | None) -> str | None:
        """Return what a barcode is, as one of this list's kinds.

        HomeBasket binds a product to the database that knew its barcode: Open
        Food Facts means groceries, Open Pet Food Facts what the cat eats, Open
        Beauty Facts a cosmetic, Open Products Facts a thing. A list splits
        things more coarsely, so the four become shopping or a thing.

        A product saved before HomeBasket told one from the other has no kind;
        asking for its record settles it there too, once and for good.
        """
        if not code or (product := self.get(code)) is None:
            return None

        kind = product.get("kind")
        if not kind:
            kind = ((await self.async_details(code)) or {}).get("kind")
        return PRODUCT_KINDS.get(kind) if kind else None

    def department(self, code: str | None) -> str | None:
        """Return which kind of shop HomeBasket buys a barcode in.

        HomeBasket gives a product one from the database that knew the
        barcode, and the user can move it; either way it is the product's
        answer, not this list's.
        """
        if not code or (product := self.get(code)) is None:
            return None
        found = product.get("department")
        return found if found in DEPARTMENTS else None

    async def async_remember(
        self,
        summary: str,
        *,
        department: str | None = None,
        photo: str | None = None,
    ) -> str | None:
        """Hand something configured here over to HomeBasket, and return its code.

        HomeBasket owns the products; a list that configures one - a name, a
        picture, the kind of shop it comes from - should not be the only place
        that knows. What goes over has no barcode, and the HomeBasket card can
        give it one later, after which scanning finds the same product.

        Returns None when HomeBasket is not installed or is too old for this.
        """
        api = self.api
        if api is None or not hasattr(api, "async_remember_product"):
            return None

        try:
            product = await api.async_remember_product(
                summary, department=department, photo=photo
            )
        except Exception:  # noqa: BLE001 - a list works without HomeBasket
            _LOGGER.exception("HomeBasket would not keep '%s'", summary)
            return None
        return (product or {}).get("code")

    async def async_update_remembered(
        self,
        code: str | None,
        *,
        department: str | None = None,
        photo: str | None = None,
    ) -> None:
        """Pass a change to a product this side configured back to HomeBasket.

        Only for products HomeBasket has no barcode for, which are the ones a
        list made: what Open Food Facts named is not a list's to rewrite.
        """
        api = self.api
        if not code or api is None or not is_local(code):
            return

        try:
            if department:
                await api.async_set_department(code, department)
            if photo is not None and hasattr(api, "async_set_photo"):
                await api.async_set_photo(code, photo)
        except Exception:  # noqa: BLE001 - the list keeps its own copy anyway
            _LOGGER.exception("HomeBasket would not take the change to %s", code)

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
