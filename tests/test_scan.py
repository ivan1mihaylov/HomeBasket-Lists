"""Checks scanning straight onto a list, without a running Home Assistant.

The list's own scan button hands a barcode to HomeBasket and puts what comes
back on the list - the right kind of item, counted if it is already there, and
nothing at all when the barcode is new to everyone:

    python3 tests/test_scan.py
"""

from __future__ import annotations

import asyncio
import datetime
import sys
import tempfile
import types
from pathlib import Path

for name in (
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.websocket_api",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.dispatcher",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.event",
    "homeassistant.helpers.storage",
    "homeassistant.config_entries",
    "homeassistant.util",
):
    sys.modules.setdefault(name, types.ModuleType(name))

_const = sys.modules["homeassistant.const"]
_const.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
_const.STATE_HOME = "home"
_const.STATE_NOT_HOME = "not_home"
_const.STATE_UNAVAILABLE = "unavailable"
_const.STATE_UNKNOWN = "unknown"

sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.core"].Event = object
sys.modules["homeassistant.core"].callback = lambda func: func
sys.modules["homeassistant.config_entries"].ConfigEntry = object
sys.modules["homeassistant.exceptions"].HomeAssistantError = type(
    "HomeAssistantError", (Exception,), {}
)

# The decorators only register a command; here they just hand the function back.
_ws = sys.modules["homeassistant.components.websocket_api"]
_ws.websocket_command = lambda schema: (lambda func: func)
_ws.async_response = lambda func: func
_ws.ActiveConnection = object
_ws.async_register_command = lambda *a, **k: None
sys.modules["homeassistant.components"].websocket_api = _ws

_event = sys.modules["homeassistant.helpers.event"]
_event.async_call_later = lambda *a, **k: (lambda: None)
_event.async_track_state_change_event = lambda *a, **k: (lambda: None)
_event.async_track_time_interval = lambda *a, **k: (lambda: None)
sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = lambda *a, **k: None
sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: None
sys.modules["homeassistant.helpers.device_registry"].async_get = lambda hass: None


class _Store:
    def __init__(self, *args, **kwargs) -> None:
        self.data = None

    async def async_load(self):
        return self.data

    async def async_save(self, data) -> None:
        self.data = data


sys.modules["homeassistant.helpers.storage"].Store = _Store
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(
    utcnow=lambda: datetime.datetime(2026, 1, 1)
)
sys.modules["homeassistant.util"].slugify = lambda text: str(text).lower()

_COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists import websocket_api  # noqa: E402
from homebasket_lists.coordinator import ListRuntime  # noqa: E402


class FakeHomeBasket:
    """HomeBasket, with one barcode it knows and one it does not."""

    api_version = 1

    def __init__(self) -> None:
        self.asked: list[str] = []
        self.added_to_own_list = False

    async def async_resolve(self, code, *, add_to_list=False, source="api"):
        self.asked.append(code)
        # The list adds things itself; HomeBasket's own list is not involved.
        self.added_to_own_list = self.added_to_own_list or add_to_list
        if code == "3800065123456":
            return {
                "code": code,
                "product_code": code,
                "name": "Pilos milk 2 l",
                "kind": "food",
                "status": "looked_up",
            }
        if code == "5907400385032":
            return {
                "code": code,
                "product_code": code,
                "name": "Sinsay lamp",
                "kind": "product",
                "status": "looked_up",
            }
        return {"code": code, "product_code": code, "name": None, "status": "unknown"}

    def get(self, code):
        return None

    def match(self, summary):
        return None

    def find(self, text):
        return []


class FakeBus:
    def async_fire(self, *args, **kwargs) -> None:
        pass


class FakeHass:
    def __init__(self) -> None:
        self.data: dict = {}
        self.bus = FakeBus()
        self.config = types.SimpleNamespace(
            path=lambda *parts: str(Path(tempfile.mkdtemp()).joinpath(*parts))
        )

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class FakeEntry:
    def __init__(self, **options) -> None:
        self.entry_id = "e1"
        self.title = "Shopping"
        self.data: dict = {}
        self.options = options


class FakeConnection:
    def __init__(self) -> None:
        self.result = None
        self.error = None

    def send_result(self, msg_id, payload) -> None:
        self.result = payload

    def send_error(self, msg_id, code, message) -> None:
        self.error = (code, message)


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
    print(f"  ok  {label}")


async def scan(hass, code, **extra):
    connection = FakeConnection()
    await websocket_api.websocket_scan(
        hass, connection, {"id": 1, "entry_id": "e1", "code": code, **extra}
    )
    return connection


async def main() -> None:
    hass = FakeHass()
    runtime = ListRuntime(hass, FakeEntry())
    await runtime.store.async_load()
    hass.data["homebasket_lists"] = {"e1": runtime}

    # --- with no HomeBasket ------------------------------------------------
    answer = await scan(hass, "3800065123456")
    check("without HomeBasket, scanning says so", answer.error[0], "not_available")
    check("...and nothing lands on the list", len(runtime.store.items), 0)

    # --- with it -----------------------------------------------------------
    homebasket = FakeHomeBasket()
    hass.data["homebasket_api"] = homebasket

    answer = await scan(hass, "3800065123456", quantity=1, unit="pcs")
    check("a grocery lands on the list", answer.result["item"]["summary"], "Pilos milk 2 l")
    check("...as a grocery", answer.result["item"]["type"], "food")
    check("...with the quantity the card asked for", answer.result["item"]["quantity"], 1)
    check("...and its unit", answer.result["item"]["unit"], "pcs")
    check("...linked to the product", answer.result["item"]["product_code"], "3800065123456")
    check("...saying what happened", answer.result["outcome"], "added")
    check("...and HomeBasket's own list was left alone", homebasket.added_to_own_list, False)

    answer = await scan(hass, "3800065123456", quantity=1, unit="pcs")
    check("scanning it again counts one more", answer.result["outcome"], "counted")
    check("...rather than a second line", len(runtime.store.items), 1)
    check("...and the count says two", runtime.store.items[0]["quantity"], 2)

    answer = await scan(hass, "5907400385032", quantity=1, unit="pcs")
    check("a thing lands as a thing", answer.result["item"]["type"], "product")
    check("...as a second item", len(runtime.store.items), 2)

    # --- a barcode nobody knows -------------------------------------------
    answer = await scan(hass, "0000000000000")
    check("an unknown barcode is reported as unknown", answer.result["status"], "unknown")
    check("...with nothing to show for it", answer.result["item"], None)
    check("...and the list is untouched", len(runtime.store.items), 2)

    print("\nall scan checks passed")


if __name__ == "__main__":
    asyncio.run(main())
