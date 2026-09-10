"""Reading a list's settings.

A setting lives in the config entry's options once it has been changed, and in
its data until then, so everything that reads one goes through here rather than
remembering to look in both places.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_ITEM_TYPES,
    DEFAULT_ITEM_TYPES,
    ITEM_TYPES,
)


def option(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Return one setting of a list."""
    return entry.options.get(key, entry.data.get(key, default))


def allowed_types(entry: ConfigEntry) -> list[str]:
    """Return the kinds an item on this list may have.

    Both kinds is the usual case. One kind makes a list of only products or
    only tasks, and neither makes a list of plain lines with a name and a note.
    """
    value = option(entry, CONF_ITEM_TYPES, DEFAULT_ITEM_TYPES)
    if isinstance(value, str):
        value = [value]
    return [kind for kind in ITEM_TYPES if kind in (value or [])]


def forced_type(entry: ConfigEntry) -> str | None:
    """Return the one kind this list gives its items, or None when it is free.

    A list fixed to one kind gives that kind to everything that lands on it, no
    matter where it came from: the card, an action, a voice assistant, or a
    linked to-do list.
    """
    kinds = allowed_types(entry)
    return kinds[0] if len(kinds) == 1 else None


def types_are_fixed(entry: ConfigEntry) -> bool:
    """Return whether the list decides an item's kind instead of the item."""
    return len(allowed_types(entry)) < len(ITEM_TYPES)


def apply_type(entry: ConfigEntry, fields: dict[str, Any]) -> dict[str, Any]:
    """Return the fields with the kind this list requires.

    A list that allows both kinds leaves them alone. One that allows a single
    kind sets it, and one that allows none clears it, so an item cannot arrive
    as the wrong thing from a linked list or an action.
    """
    if not types_are_fixed(entry):
        return fields
    kinds = allowed_types(entry)
    return {**fields, "type": kinds[0] if kinds else None}
