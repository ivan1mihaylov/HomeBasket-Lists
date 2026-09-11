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
        if code == "8006540889824":
            return {
                "code": code,
                "product_code": code,
                "name": "Head & Shoulders shampoo",
                "kind": "beauty",
                "status": "looked_up",
            }
        if code == "7613034091406":
            return {
                "code": code,
                "product_code": code,
                "name": "Felix cat food",
                "kind": "petfood",
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


async def _ready(value):
    """Hand a value back as something that can be awaited."""
    return value


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

    # --- a product HomeBasket knew before it knew about kinds --------------
    class Older(FakeHomeBasket):
        """HomeBasket from before it told a grocery from a thing."""

        async def async_resolve(self, code, *, add_to_list=False, source="api"):
            return {
                "code": code,
                "product_code": code,
                "name": "Velingrad water 1.5 l",
                "kind": None,
                "status": "known",
            }

    hass.data["homebasket_api"] = Older()
    answer = await scan(hass, "3800011000000", quantity=1, unit="pcs")
    check(
        "a product with no kind still lands as shopping",
        answer.result["item"]["type"],
        "food",
    )
    hass.data["homebasket_api"] = homebasket

    # --- the other two databases -------------------------------------------
    # A shopping list splits things more coarsely than the databases do: what
    # the cat eats is still shopping, a shampoo is still a thing.
    answer = await scan(hass, "8006540889824", quantity=1, unit="pcs")
    check("Open Beauty Facts means a thing", answer.result["item"]["type"], "product")
    check("...by its own name", answer.result["item"]["summary"], "Head & Shoulders shampoo")

    answer = await scan(hass, "7613034091406", quantity=1, unit="pcs")
    check("Open Pet Food Facts means shopping", answer.result["item"]["type"], "food")
    check("...by its own name", answer.result["item"]["summary"], "Felix cat food")

    # --- the kind comes from the database that knew the barcode ------------
    class Databases(FakeHomeBasket):
        """HomeBasket with two products, each known by a different database."""

        known = {
            "3800230410016": {"code": "3800230410016", "name": "Velingrad water 1.5 l", "kind": "food", "department": "groceries"},
            "4008496932504": {"code": "4008496932504", "name": "Zewa towels", "kind": None, "department": None},
            "8006540889824": {"code": "8006540889824", "name": "Head & Shoulders shampoo", "kind": "beauty", "department": "cosmetics"},
            "7613034091406": {"code": "7613034091406", "name": "Felix cat food", "kind": "petfood", "department": "pets"},
        }
        details = {"4008496932504": {"label": "Zewa towels", "kind": "product"}}

        @property
        def products(self):
            return list(self.known.values())

        def get(self, code):
            return self.known.get(code)

        async def async_get_details(self, code, *, refresh=False):
            self.asked.append(code)
            return self.details.get(code)

    databases = Databases()
    hass.data["homebasket_api"] = databases

    # An item put on the list by HomeBasket itself, which said nothing about
    # what the product is: the list asks rather than leaves it without a kind.
    item = await runtime.async_add_item("Velingrad water 0.5 l", product_code="3800230410016")
    check("a barcode Open Food Facts knew lands as a grocery", item["type"], "food")
    check("...as one of it", (item["quantity"], item["unit"]), (1, "pcs"))
    check("...without asking the databases again", databases.asked, [])

    item = await runtime.async_add_item("Zewa towels", product_code="4008496932504")
    check("one Open Products Facts knew lands as a thing", item["type"], "product")
    check("...after one look at the record", databases.asked, ["4008496932504"])

    item = await runtime.async_add_item("Shampoo for Ivan", product_code="8006540889824")
    check("one Open Beauty Facts knew lands as a thing too", item["type"], "product")

    item = await runtime.async_add_item("Food for the cat", product_code="7613034091406")
    check("one Open Pet Food Facts knew lands as shopping", item["type"], "food")
    check("...neither of them asking again", databases.asked, ["4008496932504"])

    # Which shop each is bought in comes from the product, not from the list.
    check(
        "a product carries its shop onto the list",
        [runtime.store.find_by_summary(name)["department"]
         for name in ("Velingrad water 0.5 l", "Shampoo for Ivan", "Food for the cat")],
        ["groceries", "cosmetics", "pets"],
    )
    check(
        "...and one HomeBasket cannot place has none",
        runtime.store.find_by_summary("Zewa towels")["department"],
        None,
    )

    # Something the databases have never heard of keeps the kind it was given.
    item = await runtime.async_add_item("Call the plumber", type="task")
    check("a task is still a task", item["type"], "task")
    check("...with nothing to count", (item["quantity"], item["unit"]), (None, None))

    item = await runtime.async_add_item("Rice", type="food", quantity=2, unit="kg")
    check("a stated quantity is left alone", (item["quantity"], item["unit"]), (2, "kg"))

    item = await runtime.async_add_item("Potatoes", type="food", unit="kg")
    check("...and a unit on its own means one of that", (item["quantity"], item["unit"]), (1, "kg"))

    # A line that went on the list before anyone knew what it was.
    plain = await runtime.store.async_add(summary="Velingrad water 6 l")
    check("...starts with no kind", plain.get("type"), None)
    counted, outcome = await runtime.async_add_or_increase(
        "Velingrad water 6 l", type="food", product_code="3800230410023"
    )
    check("scanning it counts one more", outcome, "counted")
    check("...and it learns what it is", counted["type"], "food")

    hass.data["homebasket_api"] = homebasket
    kept = len(runtime.store.items)

    # --- what a list configures is kept by HomeBasket too -------------------
    class Keeper(FakeHomeBasket):
        """HomeBasket, keeping what a list hands it."""

        def __init__(self) -> None:
            super().__init__()
            self.kept = {}
            self.photos = {}

        @property
        def products(self):
            return list(self.kept.values())

        def get(self, code):
            return self.kept.get(code)

        async def async_remember_product(self, name, *, department=None, photo=None, **rest):
            for product in self.kept.values():
                if product["name"].casefold() == name.casefold():
                    if department and not product.get("department"):
                        product["department"] = department
                    if photo and product["code"] not in self.photos:
                        self.photos[product["code"]] = photo
                    return product
            code = f"local:{name.casefold()}"
            self.kept[code] = {"code": code, "codes": [code], "name": name,
                               "kind": None, "department": department, "source": "list"}
            if photo:
                self.photos[code] = photo
            return self.kept[code]

        async def async_set_department(self, code, department):
            self.kept[code]["department"] = department
            return True

        async def async_set_photo(self, code, photo):
            self.photos[code] = photo
            return True

    keeper = Keeper()
    hass.data["homebasket_api"] = keeper
    runtime.images = types.SimpleNamespace(
        async_get=lambda uid: _ready("data:image/jpeg;base64,AAA"),
        has=lambda uid: True,
    )

    item, _ = await runtime.async_add_or_increase("Bread from the bakery", type="food")
    check("something with no barcode is kept by HomeBasket", item["product_code"], "local:bread from the bakery")
    check("...under the name it was given", keeper.kept[item["product_code"]]["name"], "Bread from the bakery")

    again, outcome = await runtime.async_add_or_increase("Bread from the bakery", type="food")
    check("adding it again is the same product", again["product_code"], item["product_code"])
    check("...counted, not kept twice", (outcome, len(keeper.kept)), ("counted", 1))

    await runtime.async_update_item(item["uid"], department="bakery")
    check(
        "configuring it configures the product",
        keeper.kept[item["product_code"]]["department"],
        "bakery",
    )
    await runtime.async_remember_item(item["uid"])
    check("...and its picture goes over too", bool(keeper.photos.get(item["product_code"])), True)

    # A task is the list's own business, not a product.
    chore, _ = await runtime.async_add_or_increase("Sweep the yard", type="task")
    check("a task is not made into a product", chore.get("product_code"), None)
    check("...and HomeBasket still holds one thing", len(keeper.kept), 1)

    hass.data["homebasket_api"] = homebasket
    runtime.images = types.SimpleNamespace(async_get=lambda uid: _ready(None), has=lambda uid: False)
    kept = len(runtime.store.items)

    # --- a barcode nobody knows -------------------------------------------
    answer = await scan(hass, "0000000000000")
    check("an unknown barcode is reported as unknown", answer.result["status"], "unknown")
    check("...with nothing to show for it", answer.result["item"], None)
    check("...and the list is untouched", len(runtime.store.items), kept)

    print("\nall scan checks passed")


if __name__ == "__main__":
    asyncio.run(main())
