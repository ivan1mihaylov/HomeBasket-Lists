"""Each of our lists is also a plain to-do entity.

That is what makes it work with the voice assistants, the built-in To-do panel
and every existing automation, exactly like the lists Home Assistant ships
with. The extra fields live beside it, in our own storage.
"""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SIGNAL_UPDATED, VERSION
from .coordinator import ListRuntime
from .store import STATUS_COMPLETED, STATUS_NEEDS_ACTION


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the list entity."""
    runtime: ListRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeBasketTodoList(runtime)])


def _due(value: str | None):
    """Turn a stored due value back into a date or datetime."""
    if not value:
        return None
    if (parsed := dt_util.parse_datetime(value)) is not None:
        return parsed
    return dt_util.parse_date(value)


class HomeBasketTodoList(TodoListEntity):
    """One HomeBasket list, as a to-do entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
    )

    def __init__(self, runtime: ListRuntime) -> None:
        """Initialise the entity."""
        self._runtime = runtime
        self._attr_unique_id = runtime.entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.name,
            manufacturer="HomeBasket",
            model="Shopping list",
            entry_type=DeviceEntryType.SERVICE,
            sw_version=VERSION,
        )

    async def async_added_to_hass(self) -> None:
        """Refresh whenever the list changes elsewhere."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATED}_{self._runtime.entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the items, as Home Assistant sees them."""
        return [
            TodoItem(
                uid=item["uid"],
                summary=item["summary"],
                status=(
                    TodoItemStatus.COMPLETED
                    if item["status"] == STATUS_COMPLETED
                    else TodoItemStatus.NEEDS_ACTION
                ),
                description=item.get("note"),
                due=_due(item.get("due")),
            )
            for item in self._runtime.store.items
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item, from a voice assistant or the built-in panel."""
        product = self._runtime.products.match(item.summary or "")
        await self._runtime.store.async_add(
            summary=item.summary,
            status=(
                STATUS_COMPLETED
                if item.status == TodoItemStatus.COMPLETED
                else STATUS_NEEDS_ACTION
            ),
            note=item.description,
            due=item.due.isoformat() if item.due else None,
            product_code=product["code"] if product else None,
        )
        await self._runtime.async_changed()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Rename an item, tick it off, or change its note or due date."""
        fields = {
            "summary": item.summary,
            "note": item.description,
            "due": item.due.isoformat() if item.due else None,
        }
        if item.status is not None:
            fields["status"] = (
                STATUS_COMPLETED
                if item.status == TodoItemStatus.COMPLETED
                else STATUS_NEEDS_ACTION
            )
        await self._runtime.store.async_update(item.uid, **fields)
        await self._runtime.async_changed()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items."""
        await self._runtime.store.async_remove(uids)
        await self._runtime.async_changed()

    async def async_move_todo_item(self, uid: str, previous_uid: str | None) -> None:
        """Reorder an item."""
        await self._runtime.store.async_move(uid, previous_uid)
        self._runtime.async_notify()
