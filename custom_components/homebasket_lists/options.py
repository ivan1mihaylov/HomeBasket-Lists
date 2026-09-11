"""Reading a list's settings.

A setting lives in the config entry's options once it has been changed, and in
its data until then, so everything that reads one goes through here rather than
remembering to look in both places.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_DEPARTMENT_ZONES,
    CONF_DUPLICATES,
    CONF_ITEM_TYPES,
    DEFAULT_DUPLICATES,
    DEFAULT_ITEM_TYPES,
    DEFAULT_QUANTITY,
    DEFAULT_UNITS,
    DUPLICATES,
    ITEM_TYPES,
    TYPE_FOOD,
    TYPE_PRODUCT,
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
    scan.
    """
    kinds = allowed_types(entry)
    return kinds[0] if len(kinds) == 1 else None


def types_are_fixed(entry: ConfigEntry) -> bool:
    """Return whether the list decides an item's kind instead of the item."""
    return len(allowed_types(entry)) <= 1


def coerce_type(entry: ConfigEntry, kind: str | None) -> str | None:
    """Return the kind an item may actually have on this list.

    One allowed kind means every item is that; none means every item is a plain
    line. With several allowed, a kind the list takes is kept - and so is no
    kind at all - while anything else becomes the first kind allowed.
    """
    allowed = allowed_types(entry)
    if not allowed:
        return None
    if len(allowed) == 1:
        return allowed[0]
    if kind is None or kind in allowed:
        return kind
    return allowed[0]


def apply_type(entry: ConfigEntry, fields: dict[str, Any]) -> dict[str, Any]:
    """Return the fields with a kind this list allows.

    Only what has to change is touched, so an item whose kind the list takes
    passes through exactly as it came.
    """
    wanted = coerce_type(entry, fields.get("type"))
    if "type" in fields and fields["type"] == wanted:
        return fields
    if "type" not in fields and wanted is None:
        return fields
    return {**fields, "type": wanted}


def buyable_type(entry: ConfigEntry) -> str | None:
    """Return the kind this list gives something to buy that it cannot place.

    Something HomeBasket knows is something you buy, even when none of the
    databases will say which kind - a list would rather have it as shopping
    than as a line with no kind at all.
    """
    return next(
        (kind for kind in allowed_types(entry) if kind in (TYPE_FOOD, TYPE_PRODUCT)),
        None,
    )


def default_amount(kind: str | None, hass: Any = None) -> dict[str, Any]:
    """Return the quantity something lands with when nobody gave one.

    Something to buy is one of it, counted in pieces - "1 бр.", "1 pcs" - in
    the language the house speaks. A task has nothing to count, and neither
    has a plain line.
    """
    if kind not in (TYPE_FOOD, TYPE_PRODUCT):
        return {}

    language = str(getattr(getattr(hass, "config", None), "language", "") or "en")
    unit = DEFAULT_UNITS.get(language.split("-")[0].lower(), DEFAULT_UNITS["en"])
    return {"quantity": DEFAULT_QUANTITY, "unit": unit}


def fill_amount(fields: dict[str, Any], kind: str | None, hass: Any = None) -> dict[str, Any]:
    """Return the fields with a quantity and unit where they were left empty.

    Only what is missing is filled, so "2 kg" stays two kilograms and "kg"
    alone becomes one kilogram rather than one piece.
    """
    filled = dict(fields)
    for key, value in default_amount(kind, hass).items():
        if filled.get(key) in (None, ""):
            filled[key] = value
    return filled


def department_zones(entry: ConfigEntry, department: str | None) -> list[str]:
    """Return the zones one kind of shop is worth a reminder in.

    Empty means everywhere, which is what everything did before departments
    existed and what a department nobody has configured keeps doing.
    """
    if not department:
        return []
    configured = option(entry, CONF_DEPARTMENT_ZONES, {}) or {}
    if not isinstance(configured, dict):
        return []
    zones = configured.get(department) or []
    if isinstance(zones, str):
        zones = [zones]
    return [zone for zone in zones if zone]


def duplicates(entry: ConfigEntry) -> str:
    """Return what this list does with something it already has.

    "count" adds to the quantity, "ignore" keeps the one that is there, and
    "allow" writes a second line.
    """
    value = option(entry, CONF_DUPLICATES, DEFAULT_DUPLICATES)
    return value if value in DUPLICATES else DEFAULT_DUPLICATES
