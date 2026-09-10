"""The HomeBasket Lists integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from . import websocket_api
from .intent import async_register_intents, async_write_sentences
from .api import HomeBasketListsAPI
from .const import (
    ATTR_NOTE,
    ATTR_PRODUCT_CODE,
    ATTR_QUANTITY,
    ATTR_STATUS,
    ATTR_STORE,
    ATTR_SUMMARY,
    ATTR_TYPE,
    ATTR_UID,
    DATA_API,
    DOMAIN,
    SERVICE_ADD_ITEM,
    SERVICE_GET_ITEMS,
    SERVICE_REMOVE_ITEM,
    SERVICE_SYNC_NOW,
    SERVICE_UPDATE_ITEM,
)
from .coordinator import ListRuntime
from .frontend import async_register_frontend
from .store import STATUS_COMPLETED, STATUS_NEEDS_ACTION, normalize_summary

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# A list is named rather than targeted by entity: the list itself is not an
# entity, only the sensor that counts what is left on it.
ATTR_LIST = "list"

ITEM_FIELDS = {
    vol.Optional(ATTR_TYPE): cv.string,
    vol.Optional(ATTR_STORE): cv.string,
    vol.Optional(ATTR_QUANTITY): cv.string,
    vol.Optional(ATTR_NOTE): cv.string,
    vol.Optional(ATTR_PRODUCT_CODE): cv.string,
}

ADD_ITEM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_LIST): cv.string,
        vol.Required(ATTR_SUMMARY): cv.string,
        **ITEM_FIELDS,
    }
)

UPDATE_ITEM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_LIST): cv.string,
        vol.Required(ATTR_UID): cv.string,
        vol.Optional(ATTR_SUMMARY): cv.string,
        vol.Optional(ATTR_STATUS): vol.In([STATUS_NEEDS_ACTION, STATUS_COMPLETED]),
        **ITEM_FIELDS,
    }
)

REMOVE_ITEM_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_LIST): cv.string, vol.Required(ATTR_UID): cv.string}
)

GET_ITEMS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_LIST): cv.string,
        vol.Optional(ATTR_STORE): cv.string,
        vol.Optional(ATTR_TYPE): cv.string,
        vol.Optional(ATTR_STATUS): vol.In([STATUS_NEEDS_ACTION, STATUS_COMPLETED]),
    }
)

SYNC_NOW_SCHEMA = vol.Schema({vol.Optional(ATTR_LIST): cv.string})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one list."""
    runtime = ListRuntime(hass, entry)
    await runtime.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    hass.data[DATA_API] = HomeBasketListsAPI(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_frontend(hass)
    websocket_api.async_register(hass)
    async_register_intents(hass)
    await async_write_sentences(hass)
    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_create_background_task(
        hass, runtime.async_start(), f"{DOMAIN}_first_sync"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one list."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime: ListRuntime = hass.data[DOMAIN].pop(entry.entry_id)
        await runtime.async_unload()
        # The list names are part of the Assist phrases.
        await async_write_sentences(hass)
        if not hass.data[DOMAIN]:
            hass.data.pop(DATA_API, None)
            for service in (
                SERVICE_ADD_ITEM,
                SERVICE_UPDATE_ITEM,
                SERVICE_REMOVE_ITEM,
                SERVICE_GET_ITEMS,
                SERVICE_SYNC_NOW,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _runtimes(hass: HomeAssistant, name: str | None) -> list[ListRuntime]:
    """Return the lists a call is about: one by name or id, or all of them."""
    everything: list[ListRuntime] = list(hass.data.get(DOMAIN, {}).values())
    if name is None:
        return everything

    wanted = normalize_summary(name)
    for runtime in everything:
        if runtime.entry.entry_id == name or normalize_summary(runtime.name) == wanted:
            return [runtime]
    raise HomeAssistantError(f"There is no list called {name}")


def _one(hass: HomeAssistant, name: str | None) -> ListRuntime:
    """Return exactly one list, or explain why that is ambiguous."""
    found = _runtimes(hass, name)
    if not found:
        raise HomeAssistantError("No list is set up")
    if name is None and len(found) > 1:
        raise HomeAssistantError("Say which list: there is more than one")
    return found[0]


def _fields(call: ServiceCall, *names: str) -> dict:
    """Return the item fields a call actually set."""
    return {name: call.data[name] for name in names if name in call.data}


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the services once."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_ITEM):
        return

    async def async_add_item(call: ServiceCall) -> ServiceResponse:
        runtime = _one(hass, call.data.get(ATTR_LIST))
        fields = _fields(call, ATTR_TYPE, ATTR_STORE, ATTR_QUANTITY, ATTR_NOTE, ATTR_PRODUCT_CODE)

        summary = call.data[ATTR_SUMMARY]
        if ATTR_PRODUCT_CODE not in fields and (
            product := runtime.products.match(summary)
        ):
            fields[ATTR_PRODUCT_CODE] = product["code"]

        item = await runtime.store.async_add(summary=summary, **fields)
        await runtime.async_changed()
        return {"item": item}

    async def async_update_item(call: ServiceCall) -> ServiceResponse:
        runtime = _one(hass, call.data.get(ATTR_LIST))
        fields = _fields(
            call,
            ATTR_SUMMARY,
            ATTR_STATUS,
            ATTR_TYPE,
            ATTR_STORE,
            ATTR_QUANTITY,
            ATTR_NOTE,
            ATTR_PRODUCT_CODE,
        )
        item = await runtime.store.async_update(call.data[ATTR_UID], **fields)
        if item is None:
            raise HomeAssistantError(f"No item {call.data[ATTR_UID]}")
        await runtime.async_changed()
        return {"item": item}

    async def async_remove_item(call: ServiceCall) -> ServiceResponse:
        runtime = _one(hass, call.data.get(ATTR_LIST))
        removed = await runtime.store.async_remove([call.data[ATTR_UID]])
        await runtime.async_changed()
        return {"removed": bool(removed)}

    async def async_get_items(call: ServiceCall) -> ServiceResponse:
        runtimes = _runtimes(hass, call.data.get(ATTR_LIST))

        store = call.data.get(ATTR_STORE)
        wanted_type = call.data.get(ATTR_TYPE)
        status = call.data.get(ATTR_STATUS)

        items = []
        for runtime in runtimes:
            for item in runtime.store.items:
                if status is not None and item["status"] != status:
                    continue
                if wanted_type is not None and item.get("type") != wanted_type:
                    continue
                # A shop filter also returns the items with no shop: those can
                # be bought anywhere, so they belong on every reminder.
                if store is not None and item.get("store") not in (store, None):
                    continue
                items.append({**item, "list": runtime.name})

        return {"count": len(items), "items": items}

    async def async_sync_now(call: ServiceCall) -> ServiceResponse:
        runtimes = _runtimes(hass, call.data.get(ATTR_LIST))

        linked = 0
        for runtime in runtimes:
            await runtime.sync.async_sync()
            linked += await runtime.sync.async_link_products()
            runtime.async_notify()
        return {"lists": len(runtimes), "products_linked": linked}

    for name, handler, schema in (
        (SERVICE_ADD_ITEM, async_add_item, ADD_ITEM_SCHEMA),
        (SERVICE_UPDATE_ITEM, async_update_item, UPDATE_ITEM_SCHEMA),
        (SERVICE_REMOVE_ITEM, async_remove_item, REMOVE_ITEM_SCHEMA),
        (SERVICE_GET_ITEMS, async_get_items, GET_ITEMS_SCHEMA),
        (SERVICE_SYNC_NOW, async_sync_now, SYNC_NOW_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN, name, handler, schema=schema, supports_response=SupportsResponse.OPTIONAL
        )
