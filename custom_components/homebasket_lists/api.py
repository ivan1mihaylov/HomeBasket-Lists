"""Public interface for other integrations.

    api = hass.data.get("homebasket_lists_api")
    if api is not None and api.api_version >= 1:
        for board in api.lists:
            print(board["name"], len(board["items"]))

        # Adding what a list already has counts one more of it.
        await api.async_add_item("Мляко", quantity=1, unit="бр.")

Listen for `homebasket_lists_updated` to know when something changed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .const import COUNTED, DOMAIN
from .store import STATUS_NEEDS_ACTION, normalize_summary

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

    # ------------------------------------------------------------------
    # Putting something on a list
    # ------------------------------------------------------------------
    def pick(self, *, entry_id: str | None = None, name: str | None = None) -> Any | None:
        """Return the list a caller means, or None when that is not clear.

        With neither an id nor a name, the only list there is - so an
        integration that just wants "the shopping list" gets it without being
        configured, as long as there is one.
        """
        runtimes = self._runtimes()
        if entry_id is not None:
            return next((r for r in runtimes if r.entry.entry_id == entry_id), None)
        if name is not None:
            wanted = normalize_summary(name)
            return next((r for r in runtimes if normalize_summary(r.name) == wanted), None)
        return runtimes[0] if len(runtimes) == 1 else None

    async def async_add_item(
        self,
        summary: str,
        *,
        entry_id: str | None = None,
        name: str | None = None,
        **fields: Any,
    ) -> dict[str, Any] | None:
        """Put something on a list, or add one more of it if it is there.

        `fields` takes the same names an item has: quantity, unit, store,
        product_code, note, type. Returns what happened, or None when there is
        no such list:

            {"entry_id": ..., "list": ..., "item": {...}, "increased": False}
        """
        runtime = self.pick(entry_id=entry_id, name=name)
        if runtime is None:
            return None

        item, outcome = await runtime.async_add_or_increase(summary, **fields)
        return {
            "entry_id": runtime.entry.entry_id,
            "list": runtime.name,
            "item": item,
            # "added", "counted" or "kept" - the list decides which.
            "outcome": outcome,
            "increased": outcome == COUNTED,
        }

    def _describe(self, runtime: ListRuntime) -> dict[str, Any]:
        return {
            "entry_id": runtime.entry.entry_id,
            "name": runtime.name,
            "stores": runtime.stores,
            "item_types": runtime.item_types,
            "linked_lists": runtime.sync.linked_lists,
            "items": [dict(item) for item in runtime.store.items],
        }
