"""Two-way sync between one of our lists and the built-in to-do lists.

Our list is the hub. Every linked to-do list is a spoke, and the hub keeps a
mirror of what each spoke looked like the last time it was read, so a change
can be told apart from the state we ourselves wrote.

    add in a spoke      -> the hub, then every other spoke
    tick in a spoke     -> the hub, then every other spoke
    delete in a spoke   -> gone everywhere
    anything in the hub -> every spoke

Items are matched by name, because the same item has a different uid in every
list. That also means a rename is seen as a delete plus an add, which is why
renames are reconciled on the periodic pass rather than instantly.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import CONF_LINK_PRODUCTS, CONF_LINKED_LISTS, DEFAULT_LINK_PRODUCTS
from .options import apply_type, buyable_type, fill_amount
from .products import ProductLink
from .store import (
    STATUS_COMPLETED,
    STATUS_NEEDS_ACTION,
    ListStore,
    normalize_summary,
)

_LOGGER = logging.getLogger(__name__)

# Renames and description edits do not change a to-do entity's state, so a
# slow pass catches what the state listener cannot see.
RECONCILE_INTERVAL = timedelta(minutes=5)


class ListSync:
    """Keeps one of our lists and its linked lists in step."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: ListStore,
        products: ProductLink,
    ) -> None:
        """Initialise the engine."""
        self.hass = hass
        self.entry = entry
        self.store = store
        self.products = products
        self._lock = asyncio.Lock()
        self._unsubscribes: list[Any] = []
        self._on_change: Any = None

    @property
    def linked_lists(self) -> list[str]:
        """Return the to-do entities this list is linked to."""
        value = self.entry.options.get(
            CONF_LINKED_LISTS, self.entry.data.get(CONF_LINKED_LISTS, [])
        )
        if isinstance(value, str):
            value = [value]
        return [entity_id for entity_id in value or [] if entity_id]

    @property
    def link_products(self) -> bool:
        """Return whether item names are matched against HomeBasket."""
        return self.entry.options.get(
            CONF_LINK_PRODUCTS,
            self.entry.data.get(CONF_LINK_PRODUCTS, DEFAULT_LINK_PRODUCTS),
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self, on_change: Any) -> None:
        """Start watching the linked lists."""
        self._on_change = on_change
        await self.store.async_forget_mirrors(self.linked_lists)

        if self.linked_lists:
            self._unsubscribes.append(
                async_track_state_change_event(
                    self.hass, self.linked_lists, self._async_spoke_changed
                )
            )
            self._unsubscribes.append(
                async_track_time_interval(
                    self.hass, self._async_reconcile, RECONCILE_INTERVAL
                )
            )

    async def async_unload(self) -> None:
        """Stop watching."""
        while self._unsubscribes:
            self._unsubscribes.pop()()

    @callback
    def _async_spoke_changed(self, event: Event) -> None:
        self.hass.async_create_task(self.async_sync())

    async def _async_reconcile(self, _now: Any) -> None:
        await self.async_sync()

    # ------------------------------------------------------------------
    # Reading and writing a linked list
    # ------------------------------------------------------------------
    async def _async_read(self, entity_id: str) -> dict[str, dict[str, Any]] | None:
        """Return a linked list's items keyed by uid, or None when unreadable."""
        try:
            response = await self.hass.services.async_call(
                "todo",
                "get_items",
                {},
                target={"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
        except Exception:  # noqa: BLE001 - a missing list must not break the rest
            _LOGGER.debug("Could not read %s", entity_id, exc_info=True)
            return None

        items = (response or {}).get(entity_id, {}).get("items", [])
        return {
            item["uid"]: {
                "summary": item.get("summary", ""),
                "status": item.get("status", STATUS_NEEDS_ACTION),
            }
            for item in items
            if item.get("uid")
        }

    async def _async_call(self, service: str, entity_id: str, data: dict) -> None:
        try:
            await self.hass.services.async_call(
                "todo", service, data, target={"entity_id": entity_id}, blocking=True
            )
        except Exception:  # noqa: BLE001 - report and carry on with the others
            _LOGGER.warning("todo.%s failed on %s", service, entity_id, exc_info=True)

    # ------------------------------------------------------------------
    # The sync itself
    # ------------------------------------------------------------------
    async def async_sync(self) -> None:
        """Pull every linked list in, then push the result back out."""
        if not self.linked_lists:
            return

        async with self._lock:
            changed = False
            live: dict[str, dict[str, dict[str, Any]]] = {}

            for entity_id in self.linked_lists:
                if (items := await self._async_read(entity_id)) is None:
                    continue
                live[entity_id] = items
                changed |= await self._async_pull(entity_id, items)

            await self._async_push(live)

            if changed and self._on_change is not None:
                self._on_change()

    async def _async_pull(
        self, entity_id: str, items: dict[str, dict[str, Any]]
    ) -> bool:
        """Apply what changed in one linked list to our list."""
        mirror = self.store.mirror(entity_id)
        first_time = not mirror
        changed = False

        for uid, item in items.items():
            previous = mirror.get(uid)
            summary = item["summary"]
            if not summary.strip():
                continue

            ours = self.store.find_by_summary(summary)
            if ours is None:
                # Only something genuinely new to the spoke is adopted. An item
                # the spoke still holds from last time but we no longer have is
                # one we just deleted - re-adding it here would undo that
                # before the push could carry the deletion across.
                if previous is not None:
                    continue

                # A line from a plain to-do list arrives as what it is: a
                # product HomeBasket knows brings its kind with it, and a list
                # fixed to one kind gives that to everything it adopts.
                code = self._match_product(summary)
                adopted = apply_type(
                    self.entry,
                    {
                        "summary": summary,
                        "status": item["status"],
                        "product_code": code,
                        "type": await self._async_kind(code),
                    },
                )
                await self.store.async_add(
                    **fill_amount(adopted, adopted.get("type"), self.hass)
                )
                changed = True
                continue

            # Only mirror a status the other side actually changed, so a tick
            # here is not undone by a stale spoke.
            if previous is not None and previous["status"] != item["status"]:
                if ours["status"] != item["status"]:
                    await self.store.async_update(ours["uid"], status=item["status"])
                    changed = True
            elif first_time and ours["status"] != item["status"]:
                await self.store.async_update(ours["uid"], status=item["status"])
                changed = True

        # Anything that was there last time and is gone now was deleted.
        for uid, previous in mirror.items():
            if uid in items:
                continue
            if (ours := self.store.find_by_summary(previous["summary"])) is not None:
                await self.store.async_remove([ours["uid"]])
                changed = True

        await self.store.async_set_mirror(entity_id, items)
        return changed

    async def _async_push(self, live: dict[str, dict[str, dict[str, Any]]]) -> None:
        """Make every linked list look like ours."""
        wanted = {
            normalize_summary(item["summary"]): item
            for item in self.store.items
            if item["summary"].strip()
        }

        for entity_id in self.linked_lists:
            items = live.get(entity_id)
            if items is None:
                continue

            seen: set[str] = set()
            for uid, item in items.items():
                key = normalize_summary(item["summary"])
                seen.add(key)

                if (ours := wanted.get(key)) is None:
                    await self._async_call("remove_item", entity_id, {"item": uid})
                    continue

                if ours["status"] != item["status"]:
                    await self._async_call(
                        "update_item", entity_id, {"item": uid, "status": ours["status"]}
                    )

            for key, ours in wanted.items():
                if key in seen:
                    continue
                await self._async_call("add_item", entity_id, {"item": ours["summary"]})
                if ours["status"] == STATUS_COMPLETED:
                    await self._async_call(
                        "update_item",
                        entity_id,
                        {"item": ours["summary"], "status": STATUS_COMPLETED},
                    )

            # Re-read so the mirror matches what the list now holds, instead of
            # what we asked for.
            if (fresh := await self._async_read(entity_id)) is not None:
                await self.store.async_set_mirror(entity_id, fresh)

    def _match_product(self, summary: str) -> str | None:
        """Return the HomeBasket product an item name refers to, if any."""
        if not self.link_products:
            return None
        product = self.products.match(summary)
        return product["code"] if product else None

    async def _async_kind(self, code: str | None) -> str | None:
        """Return what HomeBasket says a barcode is, for this list.

        Something HomeBasket knows is something you buy, so even a product
        none of the databases will name gets the list's first buyable kind
        rather than no kind at all.
        """
        if code is None:
            return None
        return await self.products.async_kind(code) or buyable_type(self.entry)

    async def async_link_products(self) -> int:
        """Attach products to items that have none, and kinds to go with them.

        An item that came from a to-do list is only a name, so what it turns
        out to be is settled here. Returns how many items changed.
        """
        if not self.link_products or not self.products.available:
            return 0

        changed = 0
        for item in list(self.store.items):
            code = item.get("product_code") or self._match_product(item["summary"])
            if code is None:
                continue

            changes: dict[str, Any] = {}
            if not item.get("product_code"):
                changes["product_code"] = code
            if not item.get("type") and (kind := await self._async_kind(code)):
                changes["type"] = kind
            if changes:
                changes = apply_type(self.entry, changes)
                # Something that turns out to be shopping is one of it - but
                # only where the item says nothing, so "2 kg" is left alone.
                have = {"quantity": item.get("quantity"), "unit": item.get("unit")}
                filled = fill_amount(have, changes.get("type") or item.get("type"), self.hass)
                changes.update({k: v for k, v in filled.items() if have[k] in (None, "")})
                await self.store.async_update(item["uid"], **changes)
                changed += 1
        return changed
