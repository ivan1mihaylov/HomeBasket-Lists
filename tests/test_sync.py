"""Checks the two-way sync without a running Home Assistant.

The sync engine is the riskiest part of this integration and the hardest to
try by hand, so it gets a test that runs anywhere:

    python3 tests/test_sync.py

Only what `sync.py` imports from Home Assistant is stubbed, and the linked
to-do list is a dictionary standing in for the `todo.*` services.
"""

from __future__ import annotations

import asyncio
import datetime
import sys
import types
import uuid
from pathlib import Path

# --- Home Assistant stubs, before importing the integration ----------------
for name in (
    "homeassistant",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.event",
    "homeassistant.config_entries",
    "homeassistant.util",
):
    sys.modules.setdefault(name, types.ModuleType(name))

sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.core"].Event = object
sys.modules["homeassistant.core"].callback = lambda func: func
sys.modules["homeassistant.config_entries"].ConfigEntry = object
sys.modules["homeassistant.helpers.event"].async_track_state_change_event = (
    lambda *a, **k: (lambda: None)
)
sys.modules["homeassistant.helpers.event"].async_track_time_interval = (
    lambda *a, **k: (lambda: None)
)
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(
    utcnow=lambda: datetime.datetime(2026, 1, 1)
)


class _Store:
    """Storage that keeps the data in memory."""

    def __init__(self, *args, **kwargs) -> None:
        self.data = None

    async def async_load(self):
        return self.data

    async def async_save(self, data) -> None:
        self.data = data


sys.modules["homeassistant.helpers.storage"].Store = _Store

# Stand the package up without running its __init__, which would pull in the
# whole of Home Assistant. Its submodules still import each other normally.
_COMPONENT = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.store import ListStore  # noqa: E402
from homebasket_lists.sync import ListSync  # noqa: E402

SPOKE = "todo.shopping_list"


class FakeTodo:
    """A built-in to-do list, as far as the sync engine can tell."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, summary: str, status: str = "needs_action") -> str:
        uid = uuid.uuid4().hex[:8]
        self.items[uid] = {"uid": uid, "summary": summary, "status": status}
        return uid

    def remove(self, summary: str) -> None:
        for uid, item in list(self.items.items()):
            if item["summary"] == summary:
                del self.items[uid]

    def set_status(self, summary: str, status: str) -> None:
        for item in self.items.values():
            if item["summary"] == summary:
                item["status"] = status

    def contents(self) -> set[tuple[str, str]]:
        return {(item["summary"], item["status"]) for item in self.items.values()}

    async def async_call(
        self, domain, service, data, target=None, blocking=False, return_response=False
    ):
        assert domain == "todo", domain
        if service == "get_items":
            return {SPOKE: {"items": list(self.items.values())}}
        if service == "add_item":
            self.add(data["item"])
            return None
        if service == "remove_item":
            self.items.pop(data["item"], None)
            self.remove(data["item"])
            return None
        if service == "update_item":
            for uid, item in self.items.items():
                if uid == data["item"] or item["summary"] == data["item"]:
                    if "status" in data:
                        item["status"] = data["status"]
                    if "rename" in data:
                        item["summary"] = data["rename"]
            return None
        raise AssertionError(f"unexpected todo.{service}")


class FakeHass:
    def __init__(self, todo: FakeTodo) -> None:
        self.services = todo


class FakeEntry:
    def __init__(self) -> None:
        self.options = {"linked_lists": [SPOKE], "link_products": False}
        self.data: dict = {}


class NoProducts:
    available = False

    def match(self, summary):
        return None

    def department(self, code):
        return None


class Products:
    """HomeBasket, holding two products it knows by name and barcode."""

    available = True
    known = {
        "3800091500130": {
            "code": "3800091500130",
            "name": "Натурална минерална вода Велинград 1,5 L",
            "kind": "food",
            "department": "groceries",
        },
        "8006540889824": {
            "code": "8006540889824",
            "name": "Шампоан",
            "kind": "beauty",
            "department": "cosmetics",
        },
    }

    def match(self, summary):
        return next(
            (p for p in self.known.values() if p["name"] == summary),
            None,
        )

    def get(self, code):
        return self.known.get(code)

    def department(self, code):
        from homebasket_lists.products import ProductLink

        return ProductLink.department(self, code)

    async def async_details(self, code):
        return None

    async def async_kind(self, code):
        from homebasket_lists.products import ProductLink

        return await ProductLink.async_kind(self, code)


def ours(store: ListStore) -> set[tuple[str, str]]:
    return {(item["summary"], item["status"]) for item in store.items}


def check(label: str, store: ListStore, todo: FakeTodo, expected: set) -> None:
    """Both sides must hold exactly `expected`."""
    for side, actual in (("ours", ours(store)), ("spoke", todo.contents())):
        if actual != expected:
            raise AssertionError(
                f"{label}: {side} is {sorted(actual)}, expected {sorted(expected)}"
            )
    print(f"  ok  {label}")


async def main() -> None:
    todo = FakeTodo()
    hass = FakeHass(todo)
    store = ListStore(None, "entry")
    await store.async_load()
    sync = ListSync(hass, FakeEntry(), store, NoProducts())

    todo.add("Хляб")
    todo.add("Мляко")
    await sync.async_sync()
    check(
        "a first sync adopts what the linked list holds",
        store,
        todo,
        {("Хляб", "needs_action"), ("Мляко", "needs_action")},
    )

    await store.async_add(summary="Яйца")
    await sync.async_sync()
    check(
        "an item added here reaches the linked list",
        store,
        todo,
        {("Хляб", "needs_action"), ("Мляко", "needs_action"), ("Яйца", "needs_action")},
    )

    todo.add("Сирене")
    await sync.async_sync()
    check(
        "an item added there reaches us",
        store,
        todo,
        {
            ("Хляб", "needs_action"),
            ("Мляко", "needs_action"),
            ("Яйца", "needs_action"),
            ("Сирене", "needs_action"),
        },
    )

    # The one that used to come straight back: the pull re-adopted it before
    # the push could carry the deletion across.
    await store.async_remove([store.find_by_summary("Яйца")["uid"]])
    await sync.async_sync()
    check(
        "an item deleted here stays deleted",
        store,
        todo,
        {("Хляб", "needs_action"), ("Мляко", "needs_action"), ("Сирене", "needs_action")},
    )

    todo.set_status("Хляб", "completed")
    await sync.async_sync()
    check(
        "ticking there ticks here",
        store,
        todo,
        {("Хляб", "completed"), ("Мляко", "needs_action"), ("Сирене", "needs_action")},
    )

    todo.remove("Мляко")
    await sync.async_sync()
    check(
        "deleting there deletes here",
        store,
        todo,
        {("Хляб", "completed"), ("Сирене", "needs_action")},
    )

    cheese = store.find_by_summary("Сирене")
    await store.async_update(cheese["uid"], status="completed")
    await sync.async_sync()
    check(
        "ticking here ticks there",
        store,
        todo,
        {("Хляб", "completed"), ("Сирене", "completed")},
    )

    await store.async_update(cheese["uid"], status="needs_action")
    await sync.async_sync()
    check(
        "un-ticking here un-ticks there",
        store,
        todo,
        {("Хляб", "completed"), ("Сирене", "needs_action")},
    )

    # --- a line from a to-do list is still a product ------------------------
    # This is how a scan reaches a list when HomeBasket writes to a to-do
    # entity rather than straight to the list: only a name arrives.
    todo = FakeTodo()
    hass = FakeHass(todo)
    store = ListStore(None, "entry2")
    await store.async_load()
    entry = FakeEntry()
    entry.options["link_products"] = True
    linked = ListSync(hass, entry, store, Products())

    todo.add("Натурална минерална вода Велинград 1,5 L")
    todo.add("Шампоан")
    todo.add("Да платя тока")
    await linked.async_sync()

    def kind_of(summary):
        return store.find_by_summary(summary).get("type")

    print("  ok  a to-do line is adopted")
    for label, summary, expected in (
        ("what Open Food Facts knew arrives as a grocery", "Натурална минерална вода Велинград 1,5 L", "food"),
        ("what Open Beauty Facts knew arrives as a thing", "Шампоан", "product"),
        ("and a line that is no product arrives without a kind", "Да платя тока", None),
    ):
        actual = kind_of(summary)
        if actual != expected:
            raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
        print(f"  ok  {label}")

    def amount_of(summary):
        item = store.find_by_summary(summary)
        return (item.get("quantity"), item.get("unit"))

    def shop_of(summary):
        return store.find_by_summary(summary).get("department")

    for label, summary, expected in (
        ("...bought where HomeBasket says", "Натурална минерална вода Велинград 1,5 L", "groceries"),
        ("...and the shampoo at the cosmetics shop", "Шампоан", "cosmetics"),
        ("...while a task belongs to no shop", "Да платя тока", None),
    ):
        actual = shop_of(summary)
        if actual != expected:
            raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
        print(f"  ok  {label}")

    for label, summary, expected in (
        ("a grocery from a to-do list is one of it", "Натурална минерална вода Велинград 1,5 L", (1, "pcs")),
        ("so is a thing", "Шампоан", (1, "pcs")),
        ("a line that is no product is left alone", "Да платя тока", (None, None)),
    ):
        actual = amount_of(summary)
        if actual != expected:
            raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
        print(f"  ok  {label}")

    # An item that has been sitting there without a kind since before any of
    # this learns one on the next pass.
    plain = await store.async_add(summary="Шампоан 2")
    await store.async_update(plain["uid"], product_code="8006540889824")
    changed = await linked.async_link_products()
    if store.find_by_summary("Шампоан 2").get("type") != "product":
        raise AssertionError("an item already linked to a product kept no kind")
    print("  ok  one already on the list learns what it is on the next pass")
    if amount_of("Шампоан 2") != (1, "pcs"):
        raise AssertionError(f"...and how many: {amount_of('Шампоан 2')}")
    print("  ok  ...and that there is one of it")

    # One that already says how much stays as it is.
    much = await store.async_add(summary="Шампоан 3", quantity=2, unit="l")
    await store.async_update(much["uid"], product_code="8006540889824", type=None)
    await linked.async_link_products()
    if amount_of("Шампоан 3") != (2, "l"):
        raise AssertionError(f"a stated quantity was overwritten: {amount_of('Шампоан 3')}")
    print("  ok  ...while one that says how much keeps it")
    if changed != 1:
        raise AssertionError(f"expected one change, got {changed}")
    print("  ok  ...and nothing else is touched")

    print("\nAll sync checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
