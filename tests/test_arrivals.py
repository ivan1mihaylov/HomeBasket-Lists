"""Checks the shop reminders and the fixed item kinds, without Home Assistant.

Both are hard to try by hand - one needs you to walk into a shop, the other
needs a list to be changed and then fed from four directions - so they get a
test that runs anywhere:

    python3 tests/test_arrivals.py
"""

from __future__ import annotations

import asyncio
import datetime
import sys
import types
from pathlib import Path
from typing import Any

# --- Home Assistant stubs, before importing the integration ----------------
for name in (
    "homeassistant",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.event",
    "homeassistant.helpers.storage",
    "homeassistant.config_entries",
    "homeassistant.util",
):
    sys.modules.setdefault(name, types.ModuleType(name))

const = sys.modules["homeassistant.const"]
const.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
const.STATE_HOME = "home"
const.STATE_NOT_HOME = "not_home"
const.STATE_UNAVAILABLE = "unavailable"
const.STATE_UNKNOWN = "unknown"

sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.core"].Event = object
sys.modules["homeassistant.core"].callback = lambda func: func
sys.modules["homeassistant.config_entries"].ConfigEntry = object

NOW = datetime.datetime(2026, 1, 1, 12, 0)
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(utcnow=lambda: NOW)
sys.modules["homeassistant.util"].slugify = lambda text: (
    "".join(ch if ch.isalnum() else "_" for ch in str(text).lower()).strip("_")
)

# Timers are held rather than run, so a test can decide whether the person
# stayed in the shop or walked back out.
TIMERS: list[dict] = []


def _call_later(hass, delay, action):
    entry = {"delay": delay, "action": action, "cancelled": False}
    TIMERS.append(entry)

    def cancel():
        entry["cancelled"] = True

    return cancel


sys.modules["homeassistant.helpers.event"].async_call_later = _call_later

# Who is being followed, so a test can see that the watcher started at all.
WATCHED: list[list[str]] = []


def _track(hass, entities, action):
    WATCHED.append(list(entities))
    return lambda: None


sys.modules["homeassistant.helpers.event"].async_track_state_change_event = _track
sys.modules["homeassistant.helpers.event"].async_track_time_interval = (
    lambda *a, **k: (lambda: None)
)


class _Registry:
    """An empty registry: no test here has a phone registered."""

    @staticmethod
    def async_get(*args):
        return None


sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: _Registry
sys.modules["homeassistant.helpers.device_registry"].async_get = lambda hass: _Registry


class _Store:
    def __init__(self, *args, **kwargs) -> None:
        self.data = None

    async def async_load(self):
        return self.data

    async def async_save(self, data) -> None:
        self.data = data


sys.modules["homeassistant.helpers.storage"].Store = _Store
sys.modules["homeassistant.helpers.dispatcher"] = types.ModuleType(
    "homeassistant.helpers.dispatcher"
)
sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = (
    lambda *a, **k: None
)

_COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.arrivals import ArrivalWatcher  # noqa: E402
from homebasket_lists.options import apply_type  # noqa: E402
from homebasket_lists.store import ListStore  # noqa: E402


# --- Standing in for Home Assistant ----------------------------------------
class FakeState:
    def __init__(self, entity_id, state, **attributes) -> None:
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes


class FakeStates:
    def __init__(self) -> None:
        self.states: dict[str, FakeState] = {}

    def set(self, entity_id, state, **attributes) -> FakeState:
        self.states[entity_id] = FakeState(entity_id, state, **attributes)
        return self.states[entity_id]

    def get(self, entity_id):
        return self.states.get(entity_id)

    def async_all(self, domain):
        return [s for s in self.states.values() if s.entity_id.startswith(f"{domain}.")]


class FakeServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def has_service(self, domain, service) -> bool:
        return False

    async def async_call(self, domain, service, data, **kwargs) -> None:
        self.calls.append((domain, service, data))


class FakeBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.once: dict[str, Any] = {}

    def async_fire(self, event, data) -> None:
        self.events.append((event, data))

    def async_listen_once(self, event, action):
        self.once[event] = action
        return lambda: None


class FakeHass:
    def __init__(self) -> None:
        self.states = FakeStates()
        self.services = FakeServices()
        self.bus = FakeBus()
        self.data: dict = {}
        self.config = types.SimpleNamespace(language="bg")
        self.is_running = True
        self.tasks: list = []

    def async_create_task(self, coro) -> None:
        self.tasks.append(asyncio.ensure_future(coro))


class FakeEntry:
    def __init__(self, **options) -> None:
        self.entry_id = "entry"
        self.title = "Пазар"
        self.data: dict = {}
        self.options = options


class FakeRuntime:
    """Only what the watcher asks of a list."""

    def __init__(self, hass, entry, store, stores) -> None:
        self.hass = hass
        self.entry = entry
        self.store = store
        self.stores = stores
        self.name = entry.title

    def zone_name(self, entity_id: str) -> str:
        state = self.hass.states.get(entity_id)
        if state is not None and state.attributes.get("friendly_name"):
            return state.attributes["friendly_name"]
        return entity_id.split(".", 1)[-1].replace("_", " ")


class Event:
    def __init__(self, entity_id, old, new) -> None:
        self.data = {"entity_id": entity_id, "old_state": old, "new_state": new}


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
    print(f"  ok  {label}")


async def flush(hass) -> None:
    """Let the watcher's background work finish."""
    while hass.tasks:
        await asyncio.gather(*hass.tasks)
        hass.tasks = [task for task in hass.tasks if not task.done()]


async def build(**options):
    hass = FakeHass()
    hass.states.set("zone.lidl", "0", friendly_name="Lidl")
    hass.states.set("zone.kaufland", "0", friendly_name="Kaufland")
    hass.states.set("person.ivan", "not_home", source="device_tracker.phone")

    store = ListStore(None, "entry")
    await store.async_load()
    entry = FakeEntry(notify_arrival=True, notify_dwell=2, **options)
    runtime = FakeRuntime(hass, entry, store, ["zone.lidl", "zone.kaufland"])
    return hass, store, ArrivalWatcher(hass, runtime)


def arrive(hass, watcher, where: str) -> None:
    """Move the person, the way a state change reaches the watcher."""
    old = hass.states.get("person.ivan")
    new = hass.states.set("person.ivan", where, source="device_tracker.phone")
    watcher._async_moved(Event("person.ivan", old, new))


def stay() -> None:
    """Run the timer of someone who did not leave."""
    for timer in TIMERS:
        if not timer["cancelled"]:
            timer["action"](NOW)
    TIMERS.clear()


async def main() -> None:
    # --- who gets told what ------------------------------------------------
    hass, store, watcher = await build()
    await store.async_add(summary="Мляко", store="zone.lidl", quantity=2, unit="бр.")
    await store.async_add(summary="Батерии")  # no shop: can be bought anywhere
    await store.async_add(summary="Тиква", store="zone.kaufland")

    arrive(hass, watcher, "Lidl")
    check("arriving starts a wait rather than a notification", hass.services.calls, [])
    check("and the wait is as long as the setting says", TIMERS[0]["delay"], 120.0)

    stay()
    await flush(hass)
    check("staying sends exactly one notification", len(hass.services.calls), 1)

    domain, service, data = hass.services.calls[0]
    check("with no phone known, it lands in the panel", (domain, service), ("persistent_notification", "create"))
    check("titled with the shop and the list", data["title"], "Lidl: Пазар")
    check(
        "listing what is open here, and what can be bought anywhere",
        data["message"],
        "2 неща за купуване: Мляко (2 бр.), Батерии",
    )
    check("and it says who arrived", hass.bus.events[0][1]["entity_id"], "person.ivan")
    check("and where", hass.bus.events[0][1]["shop"], "Lidl")

    # --- walking out before the time is up ---------------------------------
    hass, store, watcher = await build()
    await store.async_add(summary="Мляко", store="zone.lidl")
    arrive(hass, watcher, "Lidl")
    arrive(hass, watcher, "not_home")
    stay()
    await flush(hass)
    check("driving past a shop says nothing", hass.services.calls, [])

    # --- coming straight back ----------------------------------------------
    hass, store, watcher = await build(notify_cooldown=120)
    await store.async_add(summary="Мляко", store="zone.lidl")
    arrive(hass, watcher, "Lidl")
    stay()
    await flush(hass)
    arrive(hass, watcher, "not_home")
    arrive(hass, watcher, "Lidl")
    stay()
    await flush(hass)
    check("the same shop does not remind twice in a row", len(hass.services.calls), 1)

    # --- a shop with nothing on the list -----------------------------------
    hass, store, watcher = await build(notify_unassigned=False)
    await store.async_add(summary="Мляко", store="zone.lidl")
    await store.async_add(summary="Батерии")
    arrive(hass, watcher, "Kaufland")
    stay()
    await flush(hass)
    check("a shop with nothing to buy stays quiet", hass.services.calls, [])

    # --- somewhere that is not a shop of this list -------------------------
    hass, store, watcher = await build()
    await store.async_add(summary="Мляко", store="zone.lidl")
    arrive(hass, watcher, "Работа")
    check("arriving anywhere else starts nothing", TIMERS, [])

    # --- a ticked-off item is not worth a walk -----------------------------
    hass, store, watcher = await build()
    item = await store.async_add(summary="Мляко", store="zone.lidl")
    await store.async_update(item["uid"], status="completed")
    arrive(hass, watcher, "Lidl")
    stay()
    await flush(hass)
    check("what is already bought is not mentioned", hass.services.calls, [])

    # --- turned off entirely ------------------------------------------------
    hass, store, watcher = await build()
    watcher.runtime.entry.options["notify_arrival"] = False
    check("a list that does not notify has nothing to watch", watcher.enabled, False)

    # --- the kind a list forces --------------------------------------------
    free = FakeEntry()
    tasks = FakeEntry(item_types=["task"])
    products = FakeEntry(item_types=["product"])
    plain = FakeEntry(item_types=[])

    check(
        "a list allowing both kinds leaves an item alone",
        apply_type(free, {"summary": "Мляко", "type": "product"}),
        {"summary": "Мляко", "type": "product"},
    )
    check(
        "a task list makes a product a task",
        apply_type(tasks, {"summary": "Мляко", "type": "product"})["type"],
        "task",
    )
    check(
        "a task list gives a kind to what arrives without one",
        apply_type(tasks, {"summary": "Мляко"})["type"],
        "task",
    )
    check(
        "a product list makes a task a product",
        apply_type(products, {"summary": "Смени крушка", "type": "task"})["type"],
        "product",
    )
    check(
        "a list of plain lines strips the kind",
        apply_type(plain, {"summary": "Мляко", "type": "product"})["type"],
        None,
    )
    check(
        "and nothing else about the item is touched",
        apply_type(tasks, {"summary": "Мляко", "quantity": 2})["quantity"],
        2,
    )

    # --- starting up before the people exist -------------------------------
    hass, store, watcher = await build()
    hass.is_running = False
    WATCHED.clear()
    await watcher.async_setup()
    check("a list set up during a restart waits", WATCHED, [])

    hass.states.set("person.mira", "not_home")
    hass.bus.once["homeassistant_started"](None)
    check(
        "and follows everyone once the house is up",
        sorted(WATCHED[0]),
        ["person.ivan", "person.mira"],
    )

    hass, store, watcher = await build(notify_watch=["device_tracker.phone"])
    WATCHED.clear()
    await watcher.async_setup()
    check(
        "a list naming who to follow follows only them",
        WATCHED,
        [["device_tracker.phone"]],
    )

    print("\nall arrival and item-kind checks passed")


if __name__ == "__main__":
    asyncio.run(main())
