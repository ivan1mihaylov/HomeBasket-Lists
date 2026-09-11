"""Constants for HomeBasket Lists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

DOMAIN: Final = "homebasket_lists"

# Where the public API object is published for other integrations.
DATA_API: Final = "homebasket_lists_api"

# The integration HomeBasket publishes its own API under.
HOMEBASKET_API: Final = "homebasket_api"

# Config / options keys
CONF_NAME: Final = "name"
CONF_LINKED_LISTS: Final = "linked_lists"
CONF_STORES: Final = "stores"
CONF_ITEM_TYPES: Final = "item_types"
CONF_LINK_PRODUCTS: Final = "link_products"
CONF_DUPLICATES: Final = "duplicates"

# Reminding you what to buy when you reach a shop.
CONF_NOTIFY_ARRIVAL: Final = "notify_arrival"
CONF_NOTIFY_WATCH: Final = "notify_watch"
CONF_NOTIFY_DWELL: Final = "notify_dwell"
CONF_NOTIFY_UNASSIGNED: Final = "notify_unassigned"
CONF_NOTIFY_COOLDOWN: Final = "notify_cooldown"
CONF_NOTIFY_SERVICE: Final = "notify_service"

# An item is a grocery, a thing to buy, a task, or none of those. "None" is
# stored as no type at all and carries only a name and a note.
#
# Food and products are both bought, and the fields say what each one is for: a
# grocery has a best-before date, a product a link to where it comes from.
TYPE_FOOD: Final = "food"
TYPE_PRODUCT: Final = "product"
TYPE_TASK: Final = "task"
ITEM_TYPES: Final = [TYPE_FOOD, TYPE_PRODUCT, TYPE_TASK]

# HomeBasket tells a product apart by the database that knew its barcode, which
# is a finer split than a shopping list needs: what the cat eats is still
# shopping, and a shampoo is still a thing.
PRODUCT_KINDS: Final = {
    "food": TYPE_FOOD,
    "petfood": TYPE_FOOD,
    "beauty": TYPE_PRODUCT,
    "product": TYPE_PRODUCT,
}
DEFAULT_ITEM_TYPES: Final = ITEM_TYPES

# Which kind of shop something is bought in. HomeBasket gives a product one
# from the database that knew its barcode; anything typed by hand can be given
# one here. Each can be tied to the zones where it is worth a reminder - a
# butcher's is not where you are told about shampoo.
DEPARTMENT_GROCERIES: Final = "groceries"
DEPARTMENT_PRODUCE: Final = "produce"
DEPARTMENT_BUTCHER: Final = "butcher"
DEPARTMENT_COSMETICS: Final = "cosmetics"
DEPARTMENT_PETS: Final = "pets"
DEPARTMENT_BUILDING: Final = "building"
DEPARTMENTS: Final = [
    DEPARTMENT_GROCERIES,
    DEPARTMENT_PRODUCE,
    DEPARTMENT_BUTCHER,
    DEPARTMENT_COSMETICS,
    DEPARTMENT_PETS,
    DEPARTMENT_BUILDING,
]

# Where a department's zones are kept: {"butcher": ["zone.lidl"], ...}. A
# department that names no zones is reminded about everywhere, which is what
# everything did before there were departments at all.
CONF_DEPARTMENT_ZONES: Final = "department_zones"

# Something to buy is one of it unless someone says otherwise, counted in
# pieces in the language the house speaks.
DEFAULT_QUANTITY: Final = 1
DEFAULT_UNITS: Final = {"bg": "бр.", "en": "pcs"}
DEFAULT_LINK_PRODUCTS: Final = True

# What happens when something already on the list is added again. Counting it
# is the useful answer for a product - a second bottle of milk is two bottles,
# not two lines - and there is nothing to count on a task, so there the one
# that is already there is kept.
DUPLICATE_COUNT: Final = "count"
DUPLICATE_IGNORE: Final = "ignore"
DUPLICATE_ALLOW: Final = "allow"
DUPLICATES: Final = [DUPLICATE_COUNT, DUPLICATE_IGNORE, DUPLICATE_ALLOW]
DEFAULT_DUPLICATES: Final = DUPLICATE_COUNT

# What adding something did: a new line, one more of what was there, or
# nothing because the list already had it.
ADDED: Final = "added"
COUNTED: Final = "counted"
KEPT: Final = "kept"

# Off until asked for: a notification nobody expected is worse than none.
DEFAULT_NOTIFY_ARRIVAL: Final = False
# Minutes in the shop before it is worth saying anything. Long enough not to
# fire while driving past, short enough to reach you at the door.
DEFAULT_NOTIFY_DWELL: Final = 2.0
# Items with no shop can be bought anywhere, so they belong on every reminder.
DEFAULT_NOTIFY_UNASSIGNED: Final = True
# One reminder per shop per two hours, however many times you walk back in.
DEFAULT_NOTIFY_COOLDOWN: Final = 120.0

# Item fields we keep beyond what a to-do item can hold
ATTR_UID: Final = "uid"
ATTR_SUMMARY: Final = "summary"
ATTR_STATUS: Final = "status"
ATTR_TYPE: Final = "type"
ATTR_PRODUCT_CODE: Final = "product_code"
ATTR_STORE: Final = "store"
ATTR_QUANTITY: Final = "quantity"
ATTR_UNIT: Final = "unit"
ATTR_NOTE: Final = "note"
ATTR_DUE: Final = "due"
ATTR_DURATION: Final = "duration"
ATTR_DURATION_UNIT: Final = "duration_unit"
ATTR_TOOLS: Final = "tools"
ATTR_LINK: Final = "link"

# How long a task takes.
DURATION_UNITS: Final = ["minutes", "hours", "days"]

# Events
EVENT_UPDATED: Final = "homebasket_lists_updated"
EVENT_ARRIVAL: Final = "homebasket_lists_arrival"
SIGNAL_UPDATED: Final = "homebasket_lists_updated_signal"

# Services
SERVICE_ADD_ITEM: Final = "add_item"
SERVICE_UPDATE_ITEM: Final = "update_item"
SERVICE_REMOVE_ITEM: Final = "remove_item"
SERVICE_GET_ITEMS: Final = "get_items"
SERVICE_SYNC_NOW: Final = "sync_now"

STORAGE_VERSION: Final = 1


def _installed_version() -> str:
    """Return the version this integration is installed as.

    It is read from the manifest rather than written down twice, so the card's
    URL changes with every release and a browser fetches the new one instead of
    the copy it kept.
    """
    try:
        manifest = Path(__file__).parent / "manifest.json"
        return json.loads(manifest.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):  # pragma: no cover - never shipped
        return "0.0.0"


VERSION: Final = _installed_version()
