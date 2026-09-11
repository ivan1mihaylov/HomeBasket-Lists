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

from .const import DOMAIN
from .store import STATUS_COMPLETED, STATUS_NEEDS_ACTION, normalize_summary

_LOGGER = logging.getLogger(__name__)

INTENT_ADD = "HomeBasketListAddItem"
INTENT_COMPLETE = "HomeBasketListCompleteItem"
INTENT_READ = "HomeBasketListReadItems"

_REGISTERED = f"{DOMAIN}_intents_registered"

# Phrases per language. {item} is free text, {hb_list} is one of the list names.
SENTENCES: dict[str, dict[str, list[str]]] = {
    "en": {
        INTENT_ADD: [
            "add {item} to {hb_list}",
            "add {item} to the {hb_list} list",
            "put {item} on {hb_list}",
        ],
        INTENT_COMPLETE: [
            "check off {item} from {hb_list}",
            "mark {item} on {hb_list} as done",
            "complete {item} on {hb_list}",
        ],
        INTENT_READ: [
            "what is on {hb_list}",
            "what is left on {hb_list}",
            "read {hb_list}",
        ],
    },
    "bg": {
        INTENT_ADD: [
            "добави {item} в {hb_list}",
            "добави {item} към {hb_list}",
            "сложи {item} в {hb_list}",
        ],
        INTENT_COMPLETE: [
            "отметни {item} от {hb_list}",
            "купих {item} от {hb_list}",
            "махни {item} от {hb_list}",
        ],
        INTENT_READ: [
            "какво има в {hb_list}",
            "какво остава в {hb_list}",
            "прочети {hb_list}",
        ],
    },
}

RESPONSES: dict[str, dict[str, str]] = {
    "en": {
        "added": "Added {item} to {list}.",
        "completed": "Ticked off {item}.",
        "not_found": "{item} is not on {list}.",
        "empty": "{list} is empty.",
        "items": "{list} has {items}.",
        "no_list": "I could not find that list.",
    },
    "bg": {
        "added": "Добавих {item} в {list}.",
        "completed": "Отметнах {item}.",
        "not_found": "{item} го няма в {list}.",
        "empty": "{list} е празен.",
        "items": "В {list} има {items}.",
        "no_list": "Не намерих такъв списък.",
    },
}


def _phrases(language: str) -> dict[str, Any]:
    return SENTENCES.get(language, SENTENCES["en"])


def _words(language: str, key: str, **fields: Any) -> str:
    table = RESPONSES.get(language, RESPONSES["en"])
    return table[key].format(**fields)


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

        await runtime.async_add_item(summary)
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
        runtime = _pick_list(hass, slots.get("hb_list", {}).get("value"))
        if runtime is None:
            response.async_set_speech(_words(language, "no_list"))
            return response

        item = runtime.store.find_by_summary(summary, status=STATUS_NEEDS_ACTION)
        if item is None:
            response.async_set_speech(
                _words(language, "not_found", item=summary, list=runtime.name)
            )
            return response

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


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the intents.

    Home Assistant calls this itself, because a module named `intent.py` is an
    integration's intent platform. Setting a list up calls it again; the guard
    makes the second call a no-op.
    """
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True

    for handler in (AddItemIntent(), CompleteItemIntent(), ReadItemsIntent()):
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
