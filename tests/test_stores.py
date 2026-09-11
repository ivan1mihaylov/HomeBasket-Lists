"""Checks that a shop is guessed from Open Food Facts, without Home Assistant.

Adding a product should fill in the shop by itself when Open Food Facts names
one you have configured as a shop for the list, and leave it empty otherwise:

    python3 tests/test_stores.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import types
from pathlib import Path

# --- Home Assistant stubs, before importing the integration ----------------
for name in (
    "homeassistant",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers",
    "homeassistant.helpers.dispatcher",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.event",
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

sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: None
sys.modules["homeassistant.helpers.device_registry"].async_get = lambda hass: None

sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.core"].Event = object
sys.modules["homeassistant.core"].callback = lambda func: func
sys.modules["homeassistant.config_entries"].ConfigEntry = object
sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = (
    lambda *a, **k: None
)
sys.modules["homeassistant.helpers.event"].async_track_state_change_event = (
    lambda *a, **k: (lambda: None)
)
sys.modules["homeassistant.helpers.event"].async_track_time_interval = (
    lambda *a, **k: (lambda: None)
)
sys.modules["homeassistant.helpers.event"].async_call_later = (
    lambda *a, **k: (lambda: None)
)
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(utcnow=lambda: None)
sys.modules["homeassistant.util"].slugify = lambda text: str(text).lower()


class _Store:
    """Storage that keeps the data in memory."""

    def __init__(self, *args, **kwargs) -> None:
        self.data = None

    async def async_load(self):
        return self.data

    async def async_save(self, data) -> None:
        self.data = data


sys.modules["homeassistant.helpers.storage"].Store = _Store

_COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.coordinator import ListRuntime  # noqa: E402


class FakeState:
    def __init__(self, friendly_name: str | None) -> None:
        self.attributes = {"friendly_name": friendly_name} if friendly_name else {}


class FakeStates:
    def __init__(self, names: dict[str, str | None]) -> None:
        self.names = names

    def get(self, entity_id: str):
        if entity_id in self.names:
            return FakeState(self.names[entity_id])
        return None


class FakeHass:
    def __init__(self, names: dict[str, str | None]) -> None:
        self.states = FakeStates(names)
        self.data: dict = {}
        # Photos live under the config folder; a temporary one will do.
        self.config = types.SimpleNamespace(
            path=lambda *parts: str(Path(tempfile.mkdtemp()).joinpath(*parts))
        )


class FakeEntry:
    def __init__(self, stores: list[str]) -> None:
        self.entry_id = "entry"
        self.title = "Пазар"
        self.data: dict = {}
        self.options = {"stores": stores}


class FakeProducts:
    """Stands in for HomeBasket, holding what Open Food Facts returned."""

    def __init__(self, details: dict[str, dict]) -> None:
        self.details = details
        self.asked: list[str] = []

    async def async_details(self, code: str):
        self.asked.append(code)
        return self.details.get(code)


def runtime(zones: dict[str, str | None], details: dict[str, dict]) -> ListRuntime:
    hass = FakeHass(zones)
    run = ListRuntime(hass, FakeEntry(list(zones)))
    run.products = FakeProducts(details)
    return run


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
    print(f"  ok  {label}")


async def main() -> None:
    zones = {"zone.lidl": "Lidl", "zone.kaufland": "Kaufland", "zone.home": "Дом"}
    off = {
        # What Open Food Facts really returns: a comma-separated list, split
        # by HomeBasket, in whatever case and spelling the contributor used.
        "20120782": {"stores": ["Lidl"]},
        "3017620422003": {"stores": ["Carrefour", "Magasins U"]},
        "1111111111": {"stores": []},
        "2222222222": {"stores": ["Kaufland Bulgaria"]},
    }

    run = runtime(zones, off)
    check(
        "a shop Open Food Facts names is matched to its zone",
        await run.async_guess_store("20120782"),
        "zone.lidl",
    )
    check(
        "a shop that is not one of ours is left alone",
        await run.async_guess_store("3017620422003"),
        None,
    )
    check(
        "a product with no shops leaves the shop empty",
        await run.async_guess_store("1111111111"),
        None,
    )
    check(
        "a longer spelling of the same shop still matches",
        await run.async_guess_store("2222222222"),
        "zone.kaufland",
    )
    check(
        "an item with no product is not looked up at all",
        await run.async_guess_store(None),
        None,
    )
    check("nothing was fetched for an item with no product", run.products.asked.count(""), 0)

    # A list with no shops configured must not reach out at all.
    quiet = runtime({}, off)
    check(
        "a list without shops guesses nothing",
        await quiet.async_guess_store("20120782"),
        None,
    )
    check("and asks Open Food Facts nothing", quiet.products.asked, [])

    # A zone with no friendly name falls back to its entity id.
    plain = runtime({"zone.billa": None}, {"3": {"stores": ["BILLA"]}})
    check(
        "a zone without a friendly name matches on its id",
        await plain.async_guess_store("3"),
        "zone.billa",
    )

    # Names too short to be distinctive must match exactly, never loosely.
    short = runtime({"zone.t": "T"}, {"4": {"stores": ["Tesco"]}})
    check(
        "a two-letter shop name does not match everything",
        await short.async_guess_store("4"),
        None,
    )

    print("\nall shop guesses behave")


if __name__ == "__main__":
    asyncio.run(main())
