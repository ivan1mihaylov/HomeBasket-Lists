"""Ties one list's storage, sync engine and entity together."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .arrivals import ArrivalWatcher
from .images import ImageStore
from .const import (
    ADDED,
    CONF_STORES,
    COUNTED,
    DUPLICATE_COUNT,
    DUPLICATE_IGNORE,
    EVENT_UPDATED,
    KEPT,
    PRODUCT_KINDS,
    SIGNAL_UPDATED,
    TYPE_TASK,
)
from .options import (
    allowed_types,
    apply_type,
    buyable_type,
    coerce_type,
    duplicates,
    forced_type,
)
from .products import ProductLink
from .store import STATUS_NEEDS_ACTION as STATUS_OPEN, ListStore
from .sync import ListSync


class ListRuntime:
    """Everything one list needs while Home Assistant is running."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the runtime."""
        self.hass = hass
        self.entry = entry
        self.store = ListStore(hass, entry.entry_id)
        self.images = ImageStore(hass, entry.entry_id)
        self.products = ProductLink(hass)
        self.sync = ListSync(hass, entry, self.store, self.products)
        self.arrivals = ArrivalWatcher(hass, self)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def _option(self, key: str, default: Any) -> Any:
        return self.entry.options.get(key, self.entry.data.get(key, default))

    @property
    def name(self) -> str:
        """Return the list's name."""
        return self.entry.title

    @property
    def stores(self) -> list[str]:
        """Return the zones that count as shops for this list."""
        value = self._option(CONF_STORES, [])
        if isinstance(value, str):
            value = [value]
        return [entity_id for entity_id in value or [] if entity_id]

    @property
    def item_types(self) -> list[str]:
        """Return the kinds an item on this list may have."""
        return allowed_types(self.entry)

    @property
    def forced_type(self) -> str | None:
        """Return the kind this list gives every item, or None when it is free."""
        return forced_type(self.entry)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Load the list and start watching the linked ones."""
        await self.store.async_load()
        await self.images.async_load()
        await self.sync.async_setup(self.async_notify)
        await self.arrivals.async_setup()
        await self.async_enforce_types()

    async def async_start(self) -> None:
        """Do the first sync, once the entity exists."""
        await self.sync.async_sync()
        await self.async_forget_stale_photos()
        if await self.sync.async_link_products():
            self.async_notify()

    async def async_unload(self) -> None:
        """Stop watching."""
        await self.sync.async_unload()
        await self.arrivals.async_unload()

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------
    async def async_add_item(self, summary: str, **fields: Any) -> dict[str, Any]:
        """Add an item, the way every way in should.

        The card, an action, a voice assistant and a scan all end up here, so a
        product is recognised, a shop is guessed and the list's own kind is
        applied exactly once, wherever the item came from.
        """
        item, _ = await self.async_add_or_increase(summary, **fields)
        return item

    async def async_add_or_increase(
        self, summary: str, **fields: Any
    ) -> tuple[dict[str, Any], str]:
        """Add an item, and say what that meant for a list that already has it.

        The list decides: count it up - the second bottle of milk is two
        bottles, not two lines - keep the one that is there, or write a second
        line anyway. Returns the item and one of "added", "counted" or "kept".
        """
        # A caller may speak HomeBasket's kinds rather than the list's.
        if fields.get("type") in PRODUCT_KINDS:
            fields["type"] = PRODUCT_KINDS[fields["type"]]

        existing = self.store.find_by_summary(summary, status=STATUS_OPEN)
        if existing is not None:
            mode = duplicates(self.entry)
            if mode == DUPLICATE_IGNORE:
                return existing, KEPT
            if mode == DUPLICATE_COUNT:
                # A task has no quantity to raise, so there the one already on
                # the list stands; everything else counts up.
                if existing.get("type") == TYPE_TASK:
                    return existing, KEPT
                return await self._async_increase(existing, fields), COUNTED
            # "allow" falls through and writes a second line.

        if not fields.get("product_code") and (product := self.products.match(summary)):
            fields["product_code"] = product["code"]

        # An item that arrives without a kind asks HomeBasket what the product
        # turned out to be, rather than landing without one.
        if not fields.get("type") and fields.get("product_code"):
            fields["type"] = await self.products.async_kind(
                fields["product_code"]
            ) or buyable_type(self.entry)

        if not fields.get("store"):
            guess = await self.async_guess_store(fields.get("product_code"))
            if guess is not None:
                fields["store"] = guess

        fields = apply_type(self.entry, fields)
        item = await self.store.async_add(summary=summary, **fields)
        await self.async_changed()
        return item, ADDED

    async def _async_increase(
        self, item: dict[str, Any], fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Add to what is already on the list rather than repeating it."""
        more = fields.get("quantity")
        more = 1.0 if more in (None, "") else float(more)
        have = item.get("quantity")
        have = 1.0 if have in (None, "") else float(have)

        changes: dict[str, Any] = {"quantity": have + more}
        # A line that never had a kind takes the one the scan brought with it.
        if not item.get("type") and (kind := coerce_type(self.entry, fields.get("type"))):
            changes["type"] = kind
        # A unit only arrives with the first one; keep whatever the item has.
        if not item.get("unit") and fields.get("unit"):
            changes["unit"] = fields["unit"]
        # A scan knows the product even when the line was typed by hand.
        if not item.get("product_code") and fields.get("product_code"):
            changes["product_code"] = fields["product_code"]

        updated = await self.store.async_update(item["uid"], **changes)
        await self.async_changed()
        return updated or item

    async def async_remove_items(self, uids: list[str]) -> list[dict[str, Any]]:
        """Delete items, and the photos that belonged to them."""
        removed = await self.store.async_remove(uids)
        for item in removed:
            await self.images.async_delete(item["uid"])
        if removed:
            await self.async_changed()
        return removed

    async def async_forget_stale_photos(self) -> int:
        """Drop photos of items that are no longer on the list."""
        return await self.images.async_keep_only(
            [item["uid"] for item in self.store.items]
        )

    async def async_update_item(self, uid: str, **fields: Any) -> dict[str, Any] | None:
        """Change an item, keeping the kind the list requires."""
        if "type" in fields:
            fields = apply_type(self.entry, fields)
        item = await self.store.async_update(uid, **fields)
        if item is None:
            return None
        await self.async_changed()
        return item

    async def async_enforce_types(self) -> int:
        """Give every item a kind the list allows. Returns how many changed.

        Run at startup, which is also after the settings change, so narrowing a
        list to tasks turns what is already on it into tasks rather than
        leaving a mixture behind.
        """
        changed = 0
        for item in list(self.store.items):
            wanted = coerce_type(self.entry, item.get("type"))
            if item.get("type") != wanted:
                await self.store.async_update(item["uid"], type=wanted)
                changed += 1
        if changed:
            self.async_notify()
        return changed

    # ------------------------------------------------------------------
    # Shops
    # ------------------------------------------------------------------
    def zone_name(self, entity_id: str) -> str:
        """Return what a zone is called, for matching and for display."""
        if (state := self.hass.states.get(entity_id)) is not None:
            if friendly := state.attributes.get("friendly_name"):
                return str(friendly)
        return entity_id.split(".", 1)[-1].replace("_", " ")

    async def async_guess_store(self, product_code: str | None) -> str | None:
        """Return the shop Open Food Facts says sells this product.

        Only the zones configured as shops for this list are considered, so a
        product sold in fifty places still picks the one you actually visit.
        Returns None when nothing matches, leaving the shop for the user.
        """
        zones = self.stores
        if not product_code or not zones:
            return None

        details = await self.products.async_details(product_code)
        listed = [
            name.casefold()
            for name in (details or {}).get("stores") or []
            if isinstance(name, str) and name.strip()
        ]
        if not listed:
            return None

        for zone in zones:
            name = self.zone_name(zone).casefold().strip()
            if not name:
                continue
            for shop in listed:
                # A short name matching as a substring would catch anything,
                # so only names with something to them are matched loosely.
                if name == shop or (len(name) > 2 and (name in shop or shop in name)):
                    return zone
        return None

    # ------------------------------------------------------------------
    # Changes
    # ------------------------------------------------------------------
    async def async_changed(self) -> None:
        """Called after this list changed here: tell everyone, then push."""
        self.async_notify()
        await self.sync.async_sync()

    @callback
    def async_notify(self) -> None:
        """Refresh the entity and the dashboard card."""
        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATED}_{self.entry.entry_id}")
        self.hass.bus.async_fire(EVENT_UPDATED, {"entry_id": self.entry.entry_id})
