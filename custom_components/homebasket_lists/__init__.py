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
from .intent import async_setup_intents, async_write_sentences
from .api import HomeBasketListsAPI
from .const import (
    ATTR_DUE,
    ATTR_DURATION,
    ATTR_DURATION_UNIT,
    ATTR_NOTE,
    ATTR_PRODUCT_CODE,
    ATTR_QUANTITY,
    ATTR_STATUS,
    ATTR_STORE,
    ATTR_SUMMARY,
    ATTR_LINK,
    ATTR_TOOLS,
    ATTR_TYPE,
    ATTR_UID,
    ATTR_UNIT,
    COUNTED,
    DATA_API,
    DOMAIN,
    DURATION_UNITS,
    CONF_ITEM_TYPES,
    ITEM_TYPES,
    SERVICE_ADD_ITEM,
    SERVICE_GET_ITEMS,
    SERVICE_REMOVE_ITEM,
    SERVICE_SYNC_NOW,
    SERVICE_UPDATE_ITEM,
    TYPE_FOOD,
    TYPE_PRODUCT,
)
from .coordinator import ListRuntime
from .frontend import async_register_frontend
from .images import ImageStore
from .store import (
    STATUS_COMPLETED,
    STATUS_NEEDS_ACTION,
    ListStore,
    normalize_summary,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# A list is named rather than targeted by entity: the list itself is not an
# entity, only the sensor that counts what is left on it.
ATTR_LIST = "list"

ITEM_FIELDS = {
    vol.Optional(ATTR_TYPE): vol.Any(vol.In(ITEM_TYPES), None),
    vol.Optional(ATTR_STORE): cv.string,
    vol.Optional(ATTR_QUANTITY): vol.Any(vol.Coerce(float), None),
    vol.Optional(ATTR_UNIT): cv.string,
    vol.Optional(ATTR_NOTE): cv.string,
    vol.Optional(ATTR_DUE): cv.string,
    vol.Optional(ATTR_DURATION): vol.Coerce(float),
    vol.Optional(ATTR_DURATION_UNIT): vol.In(DURATION_UNITS),
    vol.Optional(ATTR_TOOLS): cv.string,
    vol.Optional(ATTR_LINK): cv.string,
    vol.Optional(ATTR_PRODUCT_CODE): cv.string,
}

# Every item field a service may set.
SETTABLE = (
    ATTR_TYPE,
    ATTR_STORE,
    ATTR_QUANTITY,
    ATTR_UNIT,
    ATTR_NOTE,
    ATTR_DUE,
    ATTR_DURATION,
    ATTR_DURATION_UNIT,
    ATTR_TOOLS,
    ATTR_LINK,
    ATTR_PRODUCT_CODE,
)

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
    await async_setup_intents(hass)
    await async_write_sentences(hass)
    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_create_background_task(
        hass, runtime.async_start(), f"{DOMAIN}_first_sync"
    )
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Bring an older list up to date.

    Version 1 had two kinds of item, where "product" meant anything you buy.
    It now means the things that are not groceries, so what was on a list
    becomes food, and a list that took products takes both.
    """
    if entry.version >= 2:
        return True

    kinds = entry.options.get(CONF_ITEM_TYPES, entry.data.get(CONF_ITEM_TYPES))
    if isinstance(kinds, list) and TYPE_PRODUCT in kinds and TYPE_FOOD not in kinds:
        kinds = [TYPE_FOOD if kind == TYPE_PRODUCT else kind for kind in kinds]
        kinds.insert(kinds.index(TYPE_FOOD) + 1, TYPE_PRODUCT)
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_ITEM_TYPES: kinds}
        )

    store = ListStore(hass, entry.entry_id)
    await store.async_load()
    moved = [item for item in store.items if item.get("type") == TYPE_PRODUCT]
    for item in moved:
        item["type"] = TYPE_FOOD
    if moved:
        await store.async_save()
        _LOGGER.info(
            "%s: %d items on %s are groceries now; change any that are not",
            DOMAIN,
            len(moved),
            entry.title,
        )

    hass.config_entries.async_update_entry(entry, version=2)
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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take a deleted list's photos with it."""
    await ImageStore(hass, entry.entry_id).async_drop_all()


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
        fields = _fields(call, *SETTABLE)

        item, outcome = await runtime.async_add_or_increase(
            call.data[ATTR_SUMMARY], **fields
        )
        return {"item": item, "outcome": outcome, "increased": outcome == COUNTED}

    async def async_update_item(call: ServiceCall) -> ServiceResponse:
        runtime = _one(hass, call.data.get(ATTR_LIST))
        fields = _fields(call, ATTR_SUMMARY, ATTR_STATUS, *SETTABLE)
        item = await runtime.async_update_item(call.data[ATTR_UID], **fields)
        if item is None:
            raise HomeAssistantError(f"No item {call.data[ATTR_UID]}")
        return {"item": item}

    async def async_remove_item(call: ServiceCall) -> ServiceResponse:
        runtime = _one(hass, call.data.get(ATTR_LIST))
        removed = await runtime.async_remove_items([call.data[ATTR_UID]])
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
