"""WebSocket commands used by the dashboard card."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api as ws
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, DURATION_UNITS
from .coordinator import ListRuntime
from .store import STATUS_COMPLETED, STATUS_NEEDS_ACTION

_REGISTERED = f"{DOMAIN}_ws_registered"

# An item's kind travels as `item_type`, not `type`. The WebSocket protocol
# names the command in a key called `type`, and voluptuous markers compare by
# their string, so a field of that name silently replaces the command name and
# the command can never be reached.
# The fields are declared by name, and the schema is built from them. A
# voluptuous marker is not a string, so reading the schema's keys as field
# names hands markers to **kwargs, where Python refuses them.
ITEM_VALIDATORS = {
    "summary": str,
    "status": vol.In([STATUS_NEEDS_ACTION, STATUS_COMPLETED]),
    "item_type": vol.Any(str, None),
    "store": vol.Any(str, None),
    "quantity": vol.Any(str, None),
    "note": vol.Any(str, None),
    "due": vol.Any(str, None),
    "duration": vol.Any(int, float, None),
    "duration_unit": vol.Any(vol.In(DURATION_UNITS), None),
    "tools": vol.Any(str, None),
    "product_code": vol.Any(str, None),
}

ITEM_FIELDS = {
    vol.Optional(name): validator for name, validator in ITEM_VALIDATORS.items()
}

# Wire name -> stored name.
FIELD_NAMES = {"item_type": "type"}


def _item_fields(msg: dict[str, Any], *, skip: tuple[str, ...] = ()) -> dict[str, Any]:
    """Return the item fields a message actually carried."""
    return {
        FIELD_NAMES.get(name, name): msg[name]
        for name in ITEM_VALIDATORS
        if name in msg and name not in skip
    }


def _runtime(hass: HomeAssistant, entry_id: str) -> ListRuntime:
    """Return one list, or raise."""
    if (runtime := hass.data.get(DOMAIN, {}).get(entry_id)) is None:
        raise HomeAssistantError("No such list")
    return runtime


def _describe(runtime: ListRuntime) -> dict[str, Any]:
    """Return one list, with each item's product filled in."""
    items = []
    for item in runtime.store.items:
        entry = dict(item)
        if product := runtime.products.get(item.get("product_code")):
            entry["product"] = {
                "code": product.get("code"),
                "codes": product.get("codes", []),
                "name": product.get("name"),
                "brand": product.get("brand"),
                "category": product.get("category"),
                "image": product.get("image"),
                "has_photo": product.get("has_photo", False),
            }
        items.append(entry)

    return {
        "entry_id": runtime.entry.entry_id,
        "name": runtime.name,
        "stores": runtime.stores,
        "item_types": runtime.item_types,
        "linked_lists": runtime.sync.linked_lists,
        "products_available": runtime.products.available,
        "items": items,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the WebSocket commands once."""
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True

    for handler in (
        websocket_lists,
        websocket_add_item,
        websocket_update_item,
        websocket_remove_item,
        websocket_move_item,
        websocket_sync,
        websocket_photo,
        websocket_product_details,
        websocket_search_products,
    ):
        ws.async_register_command(hass, handler)


@ws.websocket_command({vol.Required("type"): f"{DOMAIN}/lists"})
@ws.async_response
async def websocket_lists(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return every list the card can show."""
    runtimes = hass.data.get(DOMAIN, {}).values()
    connection.send_result(
        msg["id"], {"lists": [_describe(runtime) for runtime in runtimes]}
    )


@ws.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/item/add",
        vol.Required("entry_id"): str,
        vol.Required("summary"): str,
        **ITEM_FIELDS,
    }
)
@ws.async_response
async def websocket_add_item(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Add an item to a list."""
    runtime = _runtime(hass, msg["entry_id"])
    fields = _item_fields(msg, skip=("summary",))

    if "product_code" not in fields and (
        product := runtime.products.match(msg["summary"])
    ):
        fields["product_code"] = product["code"]

    item = await runtime.store.async_add(summary=msg["summary"], **fields)
    await runtime.async_changed()
    connection.send_result(msg["id"], {"item": item})


@ws.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/item/update",
        vol.Required("entry_id"): str,
        vol.Required("uid"): str,
        **ITEM_FIELDS,
    }
)
@ws.async_response
async def websocket_update_item(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change an item."""
    runtime = _runtime(hass, msg["entry_id"])
    item = await runtime.store.async_update(msg["uid"], **_item_fields(msg))
    if item is None:
        connection.send_error(msg["id"], "not_found", "No such item")
        return
    await runtime.async_changed()
    connection.send_result(msg["id"], {"item": item})


@ws.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/item/remove",
        vol.Required("entry_id"): str,
        vol.Required("uid"): str,
    }
)
@ws.async_response
async def websocket_remove_item(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete an item, here and in every linked list."""
    runtime = _runtime(hass, msg["entry_id"])
    removed = await runtime.store.async_remove([msg["uid"]])
    await runtime.async_changed()
    connection.send_result(msg["id"], {"removed": bool(removed)})


@ws.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/item/move",
        vol.Required("entry_id"): str,
        vol.Required("uid"): str,
        vol.Optional("previous_uid"): vol.Any(str, None),
    }
)
@ws.async_response
async def websocket_move_item(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Reorder an item."""
    runtime = _runtime(hass, msg["entry_id"])
    moved = await runtime.store.async_move(msg["uid"], msg.get("previous_uid"))
    runtime.async_notify()
    connection.send_result(msg["id"], {"moved": moved})


@ws.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/sync", vol.Optional("entry_id"): str}
)
@ws.async_response
async def websocket_sync(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Run a sync now, instead of waiting for the next change."""
    runtimes = (
        [_runtime(hass, msg["entry_id"])]
        if "entry_id" in msg
        else list(hass.data.get(DOMAIN, {}).values())
    )
    linked = 0
    for runtime in runtimes:
        await runtime.sync.async_sync()
        linked += await runtime.sync.async_link_products()
        runtime.async_notify()
    connection.send_result(msg["id"], {"lists": len(runtimes), "products_linked": linked})


@ws.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/product/photo", vol.Required("code"): str}
)
@ws.async_response
async def websocket_photo(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return a product photo HomeBasket holds, as a data URL."""
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if not runtimes:
        connection.send_result(msg["id"], {"photo": None})
        return
    photo = await runtimes[0].products.async_photo(msg["code"])
    connection.send_result(msg["id"], {"photo": photo})


@ws.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/product/details", vol.Required("code"): str}
)
@ws.async_response
async def websocket_product_details(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return what HomeBasket knows about a product, for the item sheet.

    This reads HomeBasket's cache; it does not go out to Open Food Facts.
    """
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if not runtimes:
        connection.send_result(msg["id"], {"details": None})
        return
    details = await runtimes[0].products.async_details(msg["code"])
    connection.send_result(msg["id"], {"details": details})


@ws.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/products/search",
        vol.Required("query"): str,
        vol.Optional("limit", default=6): vol.All(int, vol.Range(min=1, max=25)),
    }
)
@ws.async_response
async def websocket_search_products(
    hass: HomeAssistant, connection: ws.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return HomeBasket products matching what is being typed."""
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if not runtimes:
        connection.send_result(msg["id"], {"products": []})
        return

    found = runtimes[0].products.search(msg["query"], msg["limit"])
    connection.send_result(
        msg["id"],
        {
            "products": [
                {
                    "code": product.get("code"),
                    "name": product.get("name"),
                    "brand": product.get("brand"),
                    "category": product.get("category"),
                    "image": product.get("image"),
                    "has_photo": product.get("has_photo", False),
                }
                for product in found
            ]
        },
    )
