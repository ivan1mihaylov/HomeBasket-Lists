"""Checks what the assistant actually says, without Home Assistant.

"What do I have to buy" has to come back with the shop and the quantity, and
"what do I have to do" with the tasks, for one list or for all of them:

    python3 tests/test_voice.py
"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

for name in (
    "homeassistant",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.intent",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.storage",
    "homeassistant.config_entries",
    "homeassistant.util",
):
    sys.modules.setdefault(name, types.ModuleType(name))

sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.config_entries"].ConfigEntry = object
sys.modules["homeassistant.helpers.storage"].Store = object
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(utcnow=lambda: None)


class _Handler:
    """Enough of a Home Assistant intent handler to run one."""

    @staticmethod
    def async_validate_slots(slots):
        return slots


_intent = sys.modules["homeassistant.helpers.intent"]
_intent.IntentHandler = _Handler
_intent.Intent = object
_intent.IntentResponse = object
_intent.async_register = lambda *a, **k: None

_helpers = sys.modules["homeassistant.helpers"]
_helpers.intent = _intent
_helpers.config_validation = sys.modules["homeassistant.helpers.config_validation"]
sys.modules["homeassistant.helpers.config_validation"].string = str

_COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.intent import (  # noqa: E402
    CompleteItemIntent,
    ReadShoppingIntent,
    ReadTasksIntent,
)


class FakeStore:
    def __init__(self, items) -> None:
        self.items = items

    def find_by_summary(self, summary, *, status=None):
        wanted = " ".join(str(summary or "").split()).casefold()
        for item in self.items:
            if " ".join(item["summary"].split()).casefold() != wanted:
                continue
            if status is None or item["status"] == status:
                return item
        return None

    async def async_update(self, uid, **fields):
        for item in self.items:
            if item["uid"] == uid:
                item.update(fields)
                return item
        return None


class FakeRuntime:
    def __init__(self, name, items) -> None:
        self.name = name
        self.store = FakeStore(items)
        self.changed = 0

    async def async_changed(self) -> None:
        self.changed += 1

    def zone_name(self, entity_id: str) -> str:
        return {"zone.lidl": "Lidl", "zone.kaufland": "Kaufland"}.get(entity_id, entity_id)


class FakeHass:
    def __init__(self, runtimes) -> None:
        self.data = {"homebasket_lists": {str(i): r for i, r in enumerate(runtimes)}}


class FakeResponse:
    def __init__(self) -> None:
        self.speech = None

    def async_set_speech(self, text) -> None:
        self.speech = text


class FakeIntent:
    def __init__(self, hass, language="bg", **slots) -> None:
        self.hass = hass
        self.language = language
        self.slots = {name: {"value": value} for name, value in slots.items()}

    def create_response(self):
        return FakeResponse()


def item(summary, **fields):
    return {
        "uid": summary,
        "summary": summary,
        "status": fields.pop("status", "needs_action"),
        "type": fields.pop("type", "product"),
        "quantity": fields.pop("quantity", None),
        "unit": fields.pop("unit", None),
        "store": fields.pop("store", None),
        "duration": fields.pop("duration", None),
        "duration_unit": fields.pop("duration_unit", None),
        **fields,
    }


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}:\n  got      {actual!r}\n  expected {expected!r}")
    print(f"  ok  {label}")


async def say(handler, hass, **slots) -> str:
    response = await handler.async_handle(FakeIntent(hass, **slots))
    return response.speech


async def main() -> None:
    shopping = ReadShoppingIntent()
    tasks = ReadTasksIntent()

    market = FakeRuntime(
        "Пазар",
        [
            item("мляко", quantity=2, unit="бр.", store="zone.lidl"),
            item("хляб", store="zone.lidl"),
            item("тиква", store="zone.kaufland"),
            item("батерии"),
            item("сирене", status="completed", store="zone.lidl"),
            item("смени крушка", type="task", duration=30, duration_unit="minutes"),
        ],
    )
    repairs = FakeRuntime(
        "Ремонт",
        [
            item("боя", quantity=5, unit="литра", store="zone.kaufland"),
            item("изкърпи стената", type="task"),
            item("полей цветята", type="task", duration=1, duration_unit="hours"),
            item("смени ключа", type="task", status="completed"),
        ],
    )

    one = FakeHass([market])
    both = FakeHass([market, repairs])

    check(
        "what to buy says the shop and the quantity",
        await say(shopping, one),
        "4 неща за купуване: от Lidl: 2 броя мляко, хляб; от Kaufland: тиква; "
        "където и да е: батерии.",
    )
    check(
        "what to do reads the tasks, with how long they take",
        await say(tasks, one),
        "1 задача: смени крушка 30 мин.",
    )
    check(
        "asking with no list covers them all, saying which is which",
        await say(tasks, both),
        "3 задачи: Пазар — смени крушка 30 мин. Ремонт — изкърпи стената, "
        "полей цветята 1 ч.",
    )
    check(
        "naming a list answers about that one only",
        await say(tasks, both, hb_list="Ремонт"),
        "2 задачи: изкърпи стената, полей цветята 1 ч.",
    )
    check(
        "part of a list's name is enough",
        await say(shopping, both, hb_list="ремон"),
        "1 нещо за купуване: от Kaufland: 5 литра боя.",
    )

    # A unit is written short and said in full.
    counted = FakeRuntime(
        "Брой",
        [
            item("кисело мляко", quantity=1, unit="бр."),
            item("яйца", quantity=10, unit="бр"),
            item("ябълки", quantity=21, unit="бр."),
            item("банани", quantity=11, unit="бр."),
            item("сирене", quantity=1, unit="кг"),
            item("кайма", quantity=1.5, unit="кг"),
            item("мляко", quantity=2, unit="литра"),
        ],
    )
    check(
        "short units are said in full, agreeing with the number",
        await say(shopping, FakeHass([counted])),
        "7 неща за купуване: където и да е: 1 брой кисело мляко, 10 броя яйца, "
        "21 броя ябълки, 11 броя банани, 1 килограм сирене, 1,5 килограма кайма, "
        "2 литра мляко.",
    )
    check(
        "asking about a list that is not set up",
        await say(tasks, FakeHass([repairs]), hb_list="Пазар"),
        "Не намерих такъв списък.",
    )
    check(
        "nothing to buy anywhere",
        await say(shopping, FakeHass([FakeRuntime("Празен", [])])),
        "Нямаш нищо за купуване.",
    )
    check(
        "nothing to do on the list that was named",
        await say(tasks, FakeHass([FakeRuntime("Празен", [])]), hb_list="Празен"),
        "В Празен няма задачи.",
    )
    check(
        "a name that matches no list",
        await say(shopping, one, hb_list="Гараж"),
        "Не намерих такъв списък.",
    )
    check(
        # A unit the answer's language does not know is said as it was typed,
        # rather than guessed at.
        "and it all works in English too",
        await say(shopping, one, language="en"),
        "4 things to buy: from Lidl: мляко - 2 бр., хляб; from Kaufland: тиква; "
        "anywhere: батерии.",
    )
    check(
        "an English list says its own units in full",
        await say(
            shopping,
            FakeHass([FakeRuntime("Shopping", [item("eggs", quantity=10, unit="pcs")])]),
            language="en",
        ),
        "1 thing to buy: anywhere: eggs - 10 pieces.",
    )

    # --- ticking off without saying which list -----------------------------
    complete = CompleteItemIntent()
    check(
        "an item is ticked off on whichever list still has it",
        await say(complete, both, item="боя"),
        "Отметнах боя.",
    )
    check("...and it is really ticked off", repairs.store.items[0]["status"], "completed")
    check("...on the list that had it", repairs.changed, 1)
    check("...and no other list was touched", market.changed, 0)
    check(
        "something on no list at all says so",
        await say(complete, both, item="ананас"),
        "ананас го няма в списъците.",
    )

    print("\nall spoken answers are right")


if __name__ == "__main__":
    asyncio.run(main())
