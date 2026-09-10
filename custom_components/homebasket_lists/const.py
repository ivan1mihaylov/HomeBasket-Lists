"""Constants for HomeBasket Lists."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "homebasket_lists"
VERSION: Final = "0.1.0"

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

DEFAULT_ITEM_TYPES: Final = ["product", "task"]
DEFAULT_LINK_PRODUCTS: Final = True

# Item fields we keep beyond what a to-do item can hold
ATTR_UID: Final = "uid"
ATTR_SUMMARY: Final = "summary"
ATTR_STATUS: Final = "status"
ATTR_TYPE: Final = "type"
ATTR_PRODUCT_CODE: Final = "product_code"
ATTR_STORE: Final = "store"
ATTR_QUANTITY: Final = "quantity"
ATTR_NOTE: Final = "note"

TYPE_PRODUCT: Final = "product"
TYPE_TASK: Final = "task"

# Events
EVENT_UPDATED: Final = "homebasket_lists_updated"
SIGNAL_UPDATED: Final = "homebasket_lists_updated_signal"

# Services
SERVICE_ADD_ITEM: Final = "add_item"
SERVICE_UPDATE_ITEM: Final = "update_item"
SERVICE_REMOVE_ITEM: Final = "remove_item"
SERVICE_GET_ITEMS: Final = "get_items"
SERVICE_SYNC_NOW: Final = "sync_now"

STORAGE_VERSION: Final = 1
