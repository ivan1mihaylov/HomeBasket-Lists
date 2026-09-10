"""A small sensor per list.

The list itself lives only in this integration, but how much is still on it is
worth having as a normal entity: badges, dashboards and zone automations can
all use it without going through a service call.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_UPDATED, VERSION
from .coordinator import ListRuntime
from .store import STATUS_COMPLETED, STATUS_NEEDS_ACTION


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor for one list."""
    runtime: ListRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HomeBasketListSensor(runtime)])


class HomeBasketListSensor(SensorEntity):
    """How much is still to do on one list."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:cart-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "items"
    _attr_translation_key = "open_items"

    def __init__(self, runtime: ListRuntime) -> None:
        """Initialise the sensor."""
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_open_items"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.name,
            manufacturer="HomeBasket",
            model="List",
            entry_type=DeviceEntryType.SERVICE,
            sw_version=VERSION,
        )

    async def async_added_to_hass(self) -> None:
        """Refresh whenever the list changes."""
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
    def native_value(self) -> int:
        """Return how many items are still open."""
        return sum(
            1
            for item in self._runtime.store.items
            if item["status"] == STATUS_NEEDS_ACTION
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the shape of the list."""
        items = self._runtime.store.items
        return {
            "list": self._runtime.name,
            "entry_id": self._runtime.entry.entry_id,
            "completed": sum(1 for item in items if item["status"] == STATUS_COMPLETED),
            "total": len(items),
            "stores": self._runtime.stores,
            "linked_lists": self._runtime.sync.linked_lists,
        }
