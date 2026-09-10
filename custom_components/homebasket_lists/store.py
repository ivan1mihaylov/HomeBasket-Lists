"""Persistent storage for one list.

A to-do item can only hold a summary, a status, a description and a due date.
Everything that makes the list richer - what type of thing it is, which shop it
belongs to, how many, which HomeBasket product it is - lives here, keyed by the
same uid, so the list can still be a plain to-do entity for voice assistants.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STORAGE_VERSION

STATUS_NEEDS_ACTION = "needs_action"
STATUS_COMPLETED = "completed"

# Fields a caller may set. Anything else is ignored.
EDITABLE = (
    "summary",
    "status",
    "type",
    "product_code",
    "store",
    "quantity",
    "unit",
    "note",
    "due",
    "duration",
    "duration_unit",
    "tools",
)


# "2 бр." and the like, from when a quantity was one free-text field.
LEGACY_QUANTITY = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(.*)$")


def split_quantity(value: Any) -> tuple[float | None, str | None]:
    """Split a written quantity into a number and a unit.

    "2 бр." becomes (2, "бр."), "малко" becomes (None, "малко").
    """
    if isinstance(value, (int, float)):
        return float(value), None
    text = str(value or "").strip()
    if not text:
        return None, None

    if (match := LEGACY_QUANTITY.match(text)) is None:
        return None, text
    amount = float(match.group(1).replace(",", "."))
    return amount, match.group(2).strip() or None


def normalize_summary(summary: Any) -> str:
    """Return a comparable form of an item name.

    Items are matched across lists by their name, since every list gives the
    same item a different uid.
    """
    return " ".join(str(summary or "").split()).casefold()


class ListStore:
    """The items of one list, and their extra fields."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise the store."""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}"
        )
        self._items: list[dict[str, Any]] = []
        # The last seen items of every linked list, so a change can be diffed.
        self._mirrors: dict[str, dict[str, dict[str, Any]]] = {}

    async def async_load(self) -> None:
        """Read the list from disk."""
        data = await self._store.async_load() or {}
        self._items = list(data.get("items") or [])
        self._mirrors = dict(data.get("mirrors") or {})

        # A quantity used to be one free-text field; it is a number and a unit
        # now, so anything written the old way is split on the way in.
        migrated = False
        for item in self._items:
            item.setdefault("unit", None)
            if isinstance(item.get("quantity"), str):
                item["quantity"], unit = split_quantity(item["quantity"])
                item["unit"] = item["unit"] or unit
                migrated = True
        if migrated:
            await self.async_save()

    async def async_save(self) -> None:
        """Write the list to disk."""
        await self._store.async_save({"items": self._items, "mirrors": self._mirrors})

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------
    @property
    def items(self) -> list[dict[str, Any]]:
        """Return every item, in list order."""
        return self._items

    def get(self, uid: str) -> dict[str, Any] | None:
        """Return one item by uid."""
        return next((item for item in self._items if item["uid"] == uid), None)

    def find_by_summary(
        self, summary: str, *, status: str | None = None
    ) -> dict[str, Any] | None:
        """Return the item with this name, optionally only in one status."""
        wanted = normalize_summary(summary)
        for item in self._items:
            if normalize_summary(item["summary"]) != wanted:
                continue
            if status is None or item["status"] == status:
                return item
        return None

    async def async_add(self, **fields: Any) -> dict[str, Any]:
        """Append an item and return it."""
        now = dt_util.utcnow().isoformat()
        item = {
            "uid": uuid4().hex,
            "summary": str(fields.get("summary") or "").strip(),
            "status": fields.get("status") or STATUS_NEEDS_ACTION,
            # No type is a valid choice: a plain line with a name and a note.
            "type": fields.get("type"),
            "product_code": fields.get("product_code"),
            # Left empty on purpose when an item arrives from another list;
            # a shop is something the user assigns later.
            "store": fields.get("store"),
            "quantity": fields.get("quantity"),
            "unit": fields.get("unit"),
            "note": fields.get("note"),
            "due": fields.get("due"),
            # How long the task takes, and what it needs.
            "duration": fields.get("duration"),
            "duration_unit": fields.get("duration_unit"),
            "tools": fields.get("tools"),
            "created": now,
            "updated": now,
        }
        self._items.append(item)
        await self.async_save()
        return item

    async def async_update(self, uid: str, **fields: Any) -> dict[str, Any] | None:
        """Change an item. Only known fields are touched."""
        if (item := self.get(uid)) is None:
            return None

        changed = False
        for key in EDITABLE:
            if key not in fields:
                continue
            value = fields[key]
            if key == "summary":
                value = str(value or "").strip()
                if not value:
                    continue
            if item.get(key) != value:
                item[key] = value
                changed = True

        if changed:
            item["updated"] = dt_util.utcnow().isoformat()
            await self.async_save()
        return item

    async def async_remove(self, uids: list[str]) -> list[dict[str, Any]]:
        """Delete items and return the ones that were there."""
        wanted = set(uids)
        removed = [item for item in self._items if item["uid"] in wanted]
        if removed:
            self._items = [item for item in self._items if item["uid"] not in wanted]
            await self.async_save()
        return removed

    async def async_move(self, uid: str, previous_uid: str | None) -> bool:
        """Move an item after `previous_uid`, or to the front when None."""
        if (item := self.get(uid)) is None:
            return False
        self._items.remove(item)

        if previous_uid is None:
            self._items.insert(0, item)
        else:
            index = next(
                (i for i, other in enumerate(self._items) if other["uid"] == previous_uid),
                len(self._items) - 1,
            )
            self._items.insert(index + 1, item)

        await self.async_save()
        return True

    # ------------------------------------------------------------------
    # Mirrors of the linked lists
    # ------------------------------------------------------------------
    def mirror(self, entity_id: str) -> dict[str, dict[str, Any]]:
        """Return the last seen items of a linked list, keyed by uid."""
        return self._mirrors.get(entity_id, {})

    async def async_set_mirror(
        self, entity_id: str, items: dict[str, dict[str, Any]]
    ) -> None:
        """Remember what a linked list looked like."""
        self._mirrors[entity_id] = items
        await self.async_save()

    async def async_forget_mirrors(self, keep: list[str]) -> None:
        """Drop the mirrors of lists that are no longer linked."""
        stale = [entity_id for entity_id in self._mirrors if entity_id not in keep]
        for entity_id in stale:
            del self._mirrors[entity_id]
        if stale:
            await self.async_save()
