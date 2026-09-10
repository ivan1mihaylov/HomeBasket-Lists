"""Public interface for other integrations.

    api = hass.data.get("homebasket_lists_api")
    if api is not None and api.api_version >= 1:
        for board in api.lists:
            print(board["name"], len(board["items"]))

Listen for `homebasket_lists_updated` to know when something changed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .store import STATUS_NEEDS_ACTION

if TYPE_CHECKING:
    from .coordinator import ListRuntime

API_VERSION = 1


class HomeBasketListsAPI:
    """A stable view of the lists and their items."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise the facade."""
        self._hass = hass

    @property
    def api_version(self) -> int:
        """Return the interface version, for consumers to check against."""
        return API_VERSION

    def _runtimes(self) -> list[ListRuntime]:
        return list(self._hass.data.get(DOMAIN, {}).values())

    @property
    def lists(self) -> list[dict[str, Any]]:
        """Return every list with its items."""
        return [self._describe(runtime) for runtime in self._runtimes()]

    def get(self, entry_id: str) -> dict[str, Any] | None:
        """Return one list by its config entry id."""
        runtime = self._hass.data.get(DOMAIN, {}).get(entry_id)
        return self._describe(runtime) if runtime else None

    def items_for_store(
        self, store: str, *, include_unassigned: bool = True
    ) -> list[dict[str, Any]]:
        """Return the open items to buy at one shop.

        Items with no shop are included by default, since something without a
        shop can be bought anywhere.
        """
        found = []
        for runtime in self._runtimes():
            for item in runtime.store.items:
                if item["status"] != STATUS_NEEDS_ACTION:
                    continue
                assigned = item.get("store")
                if assigned == store or (assigned is None and include_unassigned):
                    found.append({**item, "list": runtime.name, "entry_id": runtime.entry.entry_id})
        return found

    def _describe(self, runtime: ListRuntime) -> dict[str, Any]:
        return {
            "entry_id": runtime.entry.entry_id,
            "name": runtime.name,
            "stores": runtime.stores,
            "item_types": runtime.item_types,
            "linked_lists": runtime.sync.linked_lists,
            "items": [dict(item) for item in runtime.store.items],
        }
