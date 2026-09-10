"""Ties one list's storage, sync engine and entity together."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .arrivals import ArrivalWatcher
from .const import CONF_STORES, EVENT_UPDATED, SIGNAL_UPDATED
from .options import allowed_types, apply_type, forced_type
from .products import ProductLink
from .store import ListStore
from .sync import ListSync


class ListRuntime:
    """Everything one list needs while Home Assistant is running."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the runtime."""
        self.hass = hass
        self.entry = entry
        self.store = ListStore(hass, entry.entry_id)
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
        await self.sync.async_setup(self.async_notify)
        await self.arrivals.async_setup()
        await self.async_enforce_types()

    async def async_start(self) -> None:
        """Do the first sync, once the entity exists."""
        await self.sync.async_sync()
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

        The card, an action, a voice assistant and a linked list all end up
        here, so a product is recognised, a shop is guessed and the list's own
        kind is applied exactly once, wherever the item came from.
        """
        if not fields.get("product_code") and (product := self.products.match(summary)):
            fields["product_code"] = product["code"]

        if not fields.get("store"):
            guess = await self.async_guess_store(fields.get("product_code"))
            if guess is not None:
                fields["store"] = guess

        fields = apply_type(self.entry, fields)
        item = await self.store.async_add(summary=summary, **fields)
        await self.async_changed()
        return item

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
        """Give every item the kind the list requires. Returns how many changed.

        Run at startup, which is also after the settings change, so switching a
        list to tasks only turns what is already on it into tasks rather than
        leaving a mixture behind.
        """
        wanted = apply_type(self.entry, {})
        if "type" not in wanted:
            return 0

        changed = 0
        for item in list(self.store.items):
            if item.get("type") != wanted["type"]:
                await self.store.async_update(item["uid"], type=wanted["type"])
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
