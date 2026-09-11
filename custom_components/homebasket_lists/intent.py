"""Voice control for our lists.

The lists are not to-do entities, so the built-in list intents cannot see
them. Instead this registers intents of its own and writes the sentences that
reach them into `custom_sentences/`, which is where Assist looks for phrases a
custom integration adds.

The sentence files are rewritten whenever the lists change, because the list
names are part of the phrases. A file is only replaced when its content would
differ, so an edit of your own survives until you rename a list.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, intent

from .const import COUNTED, DOMAIN, KEPT, TYPE_PRODUCT, TYPE_TASK
from .store import STATUS_COMPLETED, STATUS_NEEDS_ACTION, normalize_summary

_LOGGER = logging.getLogger(__name__)

INTENT_ADD = "HomeBasketListAddItem"
INTENT_COMPLETE = "HomeBasketListCompleteItem"
INTENT_READ = "HomeBasketListReadItems"
INTENT_SHOPPING = "HomeBasketListReadShopping"
INTENT_TASKS = "HomeBasketListReadTasks"

_REGISTERED = f"{DOMAIN}_intents_registered"

# Phrases per language. {item} is free text, {hb_list} is one of the list names.
SENTENCES: dict[str, dict[str, list[str]]] = {
    "en": {
        INTENT_ADD: [
            "add {item} to [the] {hb_list} [list]",
            "put {item} on [the] {hb_list} [list]",
            "write {item} on [the] {hb_list} [list]",
            "add {item} to (my|the) list",
        ],
        INTENT_COMPLETE: [
            "(check|tick) off {item} [(from|on|in) {hb_list}]",
            "mark {item} [(on|in) {hb_list}] as (done|bought|complete|completed|finished)",
            "complete {item} [(on|in) {hb_list}]",
            "I (bought|got) {item} [(from|on|in) {hb_list}]",
            "I (did|finished) {item} [(on|in) {hb_list}]",
            "remove {item} from {hb_list}",
        ],
        INTENT_READ: [
            "what is (on|left on) {hb_list}",
            "what does {hb_list} have",
            "read [out] {hb_list}",
            "read [out] the {hb_list} list",
            "tell me what is on {hb_list}",
        ],
        # The list is optional: without one, every list is answered at once.
        INTENT_SHOPPING: [
            "what do I (need|have) to buy [(in|on|from|for) {hb_list}]",
            "what should I buy [(in|on|from|for) {hb_list}]",
            "what is left to buy [(in|on|from|for) {hb_list}]",
            "tell me what I (need|have) to buy [(in|on|from|for) {hb_list}]",
            "what do I need from the (shop|shops|store)",
            "what is on my shopping list",
        ],
        INTENT_TASKS: [
            "what do I (need|have) to do [(in|on|for) {hb_list}]",
            "what should I do [(in|on|for) {hb_list}]",
            "what is left to do [(in|on|for) {hb_list}]",
            "what are my tasks [(in|on|for) {hb_list}]",
            "what jobs do I have [(in|on|for) {hb_list}]",
            "tell me my tasks [(in|on|for) {hb_list}]",
        ],
    },
    "bg": {
        INTENT_ADD: [
            "(добави|сложи|запиши|напиши) {item} (в|във|към|на) {hb_list}",
            "(добави|сложи|запиши|напиши) {item} (в|във|към|на) (списъка|списък) {hb_list}",
            "(добави|сложи|запиши|напиши) {item} (в|във|към) списъка",
        ],
        INTENT_COMPLETE: [
            "отметни {item} [(от|в|във|по) {hb_list}]",
            "(купих|взех|намерих) {item} [(от|в|във) {hb_list}]",
            "(свърших|направих|готово) {item} [(от|в|във|по) {hb_list}]",
            "махни {item} [(от|в|във) {hb_list}]",
            "(отбележи|маркирай) {item} [(от|в|във|по) {hb_list}] като (готово|купено|приключено|свършено|завършено)",
        ],
        INTENT_READ: [
            "какво (има|остава|е останало) (в|във|по) {hb_list}",
            "какво (има|остава) (в|във) (списъка|списък) {hb_list}",
            "прочети [ми] {hb_list}",
            "кажи ми какво (има|остава) (в|във|по) {hb_list}",
        ],
        INTENT_SHOPPING: [
            "какво (имам|трябва|остава) да купя [(в|във|от|за) {hb_list}]",
            "какво да купя [(в|във|от|за) {hb_list}]",
            "какво (има|остава) за купуване [(в|във|от|за) {hb_list}]",
            "какво (има|остава) за пазаруване [(в|във|от|за) {hb_list}]",
            "кажи ми какво (имам|трябва) да купя [(в|във|от|за) {hb_list}]",
            "какво ми трябва от (магазина|магазините|пазара)",
            "какво (има|остава) за пазар",
        ],
        INTENT_TASKS: [
            "какво (имам|трябва) да (правя|свърша|направя) [(в|във|по|за) {hb_list}]",
            "какво да (правя|свърша|направя) [(в|във|по|за) {hb_list}]",
            "какво (има|остава) за (правене|вършене|свършване) [(в|във|по|за) {hb_list}]",
            "какви задачи (имам|има|остават) [(в|във|по|за) {hb_list}]",
            "кажи ми задачите [(в|във|по|за) {hb_list}]",
            "какво ми (остава|предстои) (по|за) {hb_list}",
        ],
    },
}


RESPONSES: dict[str, dict[str, str]] = {
    "en": {
        "added": "Added {item} to {list}.",
        "increased": "{list} already had {item}, that is {count} now.",
        "already": "{list} already has {item}.",
        "completed": "Ticked off {item}.",
        "not_found": "{item} is not on {list}.",
        "empty": "{list} is empty.",
        "items": "{list} has {items}.",
        "no_list": "I could not find that list.",
        "any_list": "any list",
        "one_thing": "1 thing to buy",
        "many_things": "{count} things to buy",
        "one_task": "1 thing to do",
        "many_tasks": "{count} things to do",
        "nothing_to_buy": "Nothing to buy.",
        "nothing_to_buy_in": "Nothing to buy on {list}.",
        "nothing_to_do": "Nothing to do.",
        "nothing_to_do_in": "Nothing to do on {list}.",
        "from_shop": "from {shop}: {items}",
        "no_shop": "anywhere: {items}",
        "in_list": "{list} — {items}",
    },
    "bg": {
        "added": "Добавих {item} в {list}.",
        "increased": "Вече имаше {item} в {list}, станаха {count}.",
        "already": "{item} вече е в {list}.",
        "completed": "Отметнах {item}.",
        "not_found": "{item} го няма в {list}.",
        "empty": "{list} е празен.",
        "items": "В {list} има {items}.",
        "no_list": "Не намерих такъв списък.",
        "any_list": "списъците",
        "one_thing": "1 нещо за купуване",
        "many_things": "{count} неща за купуване",
        "one_task": "1 задача",
        "many_tasks": "{count} задачи",
        "nothing_to_buy": "Нямаш нищо за купуване.",
        "nothing_to_buy_in": "В {list} няма нищо за купуване.",
        "nothing_to_do": "Нямаш задачи.",
        "nothing_to_do_in": "В {list} няма задачи.",
        "from_shop": "от {shop}: {items}",
        "no_shop": "където и да е: {items}",
        "in_list": "{list} — {items}",
    },
}


# A unit is written short on a list and said in full: "2 бр." is read out as
# "2 броя". Each entry is (one, more than one).
SPOKEN_UNITS: dict[str, dict[str, tuple[str, str]]] = {
    "en": {
        "pcs": ("piece", "pieces"),
        "pcs.": ("piece", "pieces"),
        "kg": ("kilogram", "kilograms"),
        "g": ("gram", "grams"),
        "l": ("litre", "litres"),
        "ml": ("millilitre", "millilitres"),
    },
    "bg": {
        "бр": ("брой", "броя"),
        "бр.": ("брой", "броя"),
        "кг": ("килограм", "килограма"),
        "г": ("грам", "грама"),
        "л": ("литър", "литра"),
        "мл": ("милилитър", "милилитра"),
    },
}

SHORT_UNITS: dict[str, dict[str, str]] = {
    "en": {"minutes": "min", "hours": "h", "days": "days"},
    "bg": {"minutes": "мин", "hours": "ч", "days": "дни"},
}


def _phrases(language: str) -> dict[str, Any]:
    return SENTENCES.get(language, SENTENCES["en"])


def _words(language: str, key: str, **fields: Any) -> str:
    table = RESPONSES.get(language, RESPONSES["en"])
    return table[key].format(**fields)


def _number(value: Any, language: str) -> str | None:
    """Return a number as it would be said: 2, not 2.0, and 1,5 in Bulgarian."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return str(int(number))

    written = f"{number:g}"
    return written.replace(".", ",") if language == "bg" else written


def _spoken_unit(unit: str, quantity: float, language: str) -> str:
    """Return a unit as it is said, not as it is written on the list."""
    table = SPOKEN_UNITS.get(language, SPOKEN_UNITS["en"])
    if (pair := table.get(unit.casefold())) is None:
        return unit

    # Only one of a thing takes the singular: 21 броя, not 21 брой, which is
    # how it is said when the number is a figure rather than words.
    return pair[0] if quantity == 1 else pair[1]


def _amount(item: dict[str, Any], language: str) -> str:
    """Return a product with its quantity, as it is said: "5 броя яйца"."""
    summary = item.get("summary") or ""
    if (written := _number(item.get("quantity"), language)) is None:
        return summary

    unit = (item.get("unit") or "").strip()
    if unit:
        unit = _spoken_unit(unit, float(item["quantity"]), language)

    # Bulgarian says how many first - "5 броя яйца". English does not put a
    # bare count in front of the thing, so there the name leads and the amount
    # follows a dash: "eggs - 5 pcs".
    if language == "bg":
        return " ".join(part for part in (written, unit, summary) if part)
    return f"{summary} - {' '.join(part for part in (written, unit) if part)}"


def _task(item: dict[str, Any], language: str) -> str:
    """Return a task with how long it takes, when that is known."""
    summary = item.get("summary") or ""
    if (number := _number(item.get("duration"), language)) is None:
        return summary
    units = SHORT_UNITS.get(language, SHORT_UNITS["en"])
    unit = units.get(item.get("duration_unit") or "", "")
    return " ".join(part for part in (summary, number, unit) if part)


def _by_shop(runtime: Any, items: list[dict[str, Any]], language: str) -> str:
    """Return the products of one list, grouped by the shop to buy them in.

    Saying the shop is the point of the question: a list of twenty things is
    useless, four things in Lidl and two anywhere is a plan.
    """
    groups: dict[str | None, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item.get("store") or None, []).append(item)

    parts = []
    for store, group in groups.items():
        names = ", ".join(_amount(item, language) for item in group)
        if store:
            parts.append(
                _words(
                    language,
                    "from_shop",
                    shop=runtime.zone_name(store),
                    items=names,
                )
            )
        else:
            parts.append(_words(language, "no_shop", items=names))
    return "; ".join(parts)


def _open_items(runtime: Any, kind: str) -> list[dict[str, Any]]:
    """Return one list's open items of one kind."""
    return [
        item
        for item in runtime.store.items
        if item["status"] == STATUS_NEEDS_ACTION and item.get("type") == kind
    ]


def _runtimes(hass: HomeAssistant) -> list[Any]:
    return list(hass.data.get(DOMAIN, {}).values())


def _pick_list(hass: HomeAssistant, name: str | None) -> Any | None:
    """Return the list a phrase named, or the only one there is."""
    runtimes = _runtimes(hass)
    if not runtimes:
        return None
    if not name:
        return runtimes[0] if len(runtimes) == 1 else None

    wanted = normalize_summary(name)
    for runtime in runtimes:
        if normalize_summary(runtime.name) == wanted:
            return runtime
    for runtime in runtimes:
        if wanted in normalize_summary(runtime.name):
            return runtime
    return None


def _pick_lists(hass: HomeAssistant, name: str | None) -> list[Any] | None:
    """Return the lists a question is about.

    A named list is that one; no name at all means every list, since "what do
    I have to buy" is a question about the shopping, not about one list.
    Returns None when the name matched nothing.
    """
    if not name:
        return _runtimes(hass)
    runtime = _pick_list(hass, name)
    return None if runtime is None else [runtime]


class _ListIntent(intent.IntentHandler):
    """Shared slot handling for the list intents."""

    slot_schema = {
        vol.Optional("item"): cv.string,
        vol.Optional("hb_list"): cv.string,
    }

    @staticmethod
    def _language(intent_obj: intent.Intent) -> str:
        return (intent_obj.language or "en").split("-")[0].lower()


class AddItemIntent(_ListIntent):
    """Add an item by voice."""

    intent_type = INTENT_ADD

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        language = self._language(intent_obj)
        response = intent_obj.create_response()

        summary = (slots.get("item", {}).get("value") or "").strip()
        runtime = _pick_list(hass, slots.get("hb_list", {}).get("value"))
        if runtime is None or not summary:
            response.async_set_speech(_words(language, "no_list"))
            return response

        item, outcome = await runtime.async_add_or_increase(summary)
        if outcome == KEPT:
            response.async_set_speech(
                _words(language, "already", item=summary, list=runtime.name)
            )
        elif outcome == COUNTED:
            # Saying it is already there, without the number, would sound like
            # nothing happened.
            response.async_set_speech(
                _words(
                    language,
                    "increased",
                    item=summary,
                    list=runtime.name,
                    count=_number(item.get("quantity"), language) or "",
                )
            )
        else:
            response.async_set_speech(
                _words(language, "added", item=summary, list=runtime.name)
            )
        return response


class CompleteItemIntent(_ListIntent):
    """Tick an item off by voice."""

    intent_type = INTENT_COMPLETE

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        language = self._language(intent_obj)
        response = intent_obj.create_response()

        summary = (slots.get("item", {}).get("value") or "").strip()
        named = slots.get("hb_list", {}).get("value")
        runtimes = _pick_lists(hass, named)
        if not runtimes:
            response.async_set_speech(_words(language, "no_list"))
            return response

        # "купих мляко" does not say where it was written down, so whichever
        # list still has it open is the one meant.
        runtime = next(
            (
                candidate
                for candidate in runtimes
                if candidate.store.find_by_summary(summary, status=STATUS_NEEDS_ACTION)
            ),
            None,
        )
        if runtime is None:
            where = (
                runtimes[0].name
                if len(runtimes) == 1
                else _words(language, "any_list")
            )
            response.async_set_speech(
                _words(language, "not_found", item=summary, list=where)
            )
            return response

        item = runtime.store.find_by_summary(summary, status=STATUS_NEEDS_ACTION)

        await runtime.store.async_update(item["uid"], status=STATUS_COMPLETED)
        await runtime.async_changed()
        response.async_set_speech(_words(language, "completed", item=item["summary"]))
        return response


class ReadItemsIntent(_ListIntent):
    """Read out what is still on a list."""

    intent_type = INTENT_READ

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        language = self._language(intent_obj)
        response = intent_obj.create_response()

        runtime = _pick_list(hass, slots.get("hb_list", {}).get("value"))
        if runtime is None:
            response.async_set_speech(_words(language, "no_list"))
            return response

        open_items = [
            item["summary"]
            for item in runtime.store.items
            if item["status"] == STATUS_NEEDS_ACTION
        ]
        if not open_items:
            response.async_set_speech(_words(language, "empty", list=runtime.name))
            return response

        response.async_set_speech(
            _words(language, "items", list=runtime.name, items=", ".join(open_items))
        )
        return response


class _ReadKindIntent(_ListIntent):
    """Answer "what do I have to buy" and "what do I have to do".

    Both questions are the same shape: take one kind of item from one list or
    from all of them, and say what is left. Only the wording differs.
    """

    kind: str
    one: str
    many: str
    nothing: str
    nothing_in: str

    def _describe(
        self, runtime: Any, items: list[dict[str, Any]], language: str
    ) -> str:
        raise NotImplementedError

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        language = self._language(intent_obj)
        response = intent_obj.create_response()

        named = slots.get("hb_list", {}).get("value")
        runtimes = _pick_lists(hass, named)
        if runtimes is None or not runtimes:
            response.async_set_speech(_words(language, "no_list"))
            return response

        found = [
            (runtime, items)
            for runtime in runtimes
            if (items := _open_items(runtime, self.kind))
        ]
        if not found:
            # Naming a list makes the answer about that list, so say which.
            if named and len(runtimes) == 1:
                speech = _words(language, self.nothing_in, list=runtimes[0].name)
            else:
                speech = _words(language, self.nothing)
            response.async_set_speech(speech)
            return response

        count = sum(len(items) for _, items in found)
        head = (
            _words(language, self.one)
            if count == 1
            else _words(language, self.many, count=count)
        )

        sections = []
        for runtime, items in found:
            body = self._describe(runtime, items, language)
            # Which list something is on only matters when more than one
            # answered; otherwise it is just noise.
            sections.append(
                _words(language, "in_list", list=runtime.name, items=body)
                if len(found) > 1
                else body
            )

        response.async_set_speech(f"{head}: {'. '.join(sections)}.")
        return response


class ReadShoppingIntent(_ReadKindIntent):
    """Say what is left to buy, and where."""

    intent_type = INTENT_SHOPPING
    kind = TYPE_PRODUCT
    one = "one_thing"
    many = "many_things"
    nothing = "nothing_to_buy"
    nothing_in = "nothing_to_buy_in"

    def _describe(
        self, runtime: Any, items: list[dict[str, Any]], language: str
    ) -> str:
        return _by_shop(runtime, items, language)


class ReadTasksIntent(_ReadKindIntent):
    """Say what is left to do."""

    intent_type = INTENT_TASKS
    kind = TYPE_TASK
    one = "one_task"
    many = "many_tasks"
    nothing = "nothing_to_do"
    nothing_in = "nothing_to_do_in"

    def _describe(
        self, runtime: Any, items: list[dict[str, Any]], language: str
    ) -> str:
        return ", ".join(_task(item, language) for item in items)


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the intents.

    Home Assistant calls this itself, because a module named `intent.py` is an
    integration's intent platform. Setting a list up calls it again; the guard
    makes the second call a no-op.
    """
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True

    for handler in (
        AddItemIntent(),
        CompleteItemIntent(),
        ReadItemsIntent(),
        ReadShoppingIntent(),
        ReadTasksIntent(),
    ):
        intent.async_register(hass, handler)


def sentence_document(
    language: str, phrases: dict[str, list[str]], names: list[str]
) -> dict[str, Any]:
    """Return one custom sentences file, in the shape Assist expects.

    Every intent is a mapping with a `data` list - a bare list of blocks under
    the intent name makes the conversation agent fail to load the language at
    all, taking every other custom sentence down with it. Every {slot} must
    also be a list: what was said is free text, so `item` is a wildcard, while
    `hb_list` is the names of the lists that exist.
    """
    return {
        "language": language,
        "intents": {
            name: {"data": [{"sentences": list(sentences)}]}
            for name, sentences in phrases.items()
        },
        "lists": {
            "item": {"wildcard": True},
            "hb_list": {"values": list(names)},
        },
    }


async def async_write_sentences(hass: HomeAssistant) -> None:
    """Write the Assist phrases for the lists that exist right now."""
    names = sorted(runtime.name for runtime in _runtimes(hass))
    if not names:
        return

    for language, phrases in SENTENCES.items():
        document = sentence_document(language, phrases, names)
        text = (
            "# Written by the HomeBasket Lists integration.\n"
            "# It is rewritten when a list is added or renamed.\n"
            + yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
        )

        path = Path(hass.config.path("custom_sentences", language, f"{DOMAIN}.yaml"))

        def _write(path: Path = path, text: str = text) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file() and path.read_text(encoding="utf-8") == text:
                return
            path.write_text(text, encoding="utf-8")

        try:
            await hass.async_add_executor_job(_write)
        except OSError as err:
            _LOGGER.warning("Could not write the Assist sentences for %s: %s", language, err)
