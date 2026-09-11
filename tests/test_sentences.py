"""Checks the Assist phrases the integration writes.

A custom sentences file in the wrong shape does not only lose our own phrases:
the conversation agent fails to load the whole language, so every other custom
sentence goes with it. That is worth a test:

    python3 tests/test_sentences.py

It parses the phrases with hassil, the same library Home Assistant matches
with, when that is installed, and checks the file's shape either way.
"""

from __future__ import annotations

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

_intent = sys.modules["homeassistant.helpers.intent"]
_intent.IntentHandler = object
_intent.Intent = object
_intent.IntentResponse = object
_intent.async_register = lambda *a, **k: None

_helpers = sys.modules["homeassistant.helpers"]
_helpers.intent = _intent
_helpers.config_validation = sys.modules["homeassistant.helpers.config_validation"]

_cv = sys.modules["homeassistant.helpers.config_validation"]
_cv.string = str

_COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.intent import (  # noqa: E402
    INTENT_ADD,
    INTENT_COMPLETE,
    INTENT_READ,
    INTENT_SHOPPING,
    INTENT_TASKS,
    SENTENCES,
    sentence_document,
)

NAMES = ["Пазар", "Ремонт"]

# What someone would actually say, and what should come out of it.
SPOKEN = {
    "bg": [
        ("добави мляко в Пазар", INTENT_ADD, {"item": "мляко", "hb_list": "Пазар"}),
        ("купих хляб от Пазар", INTENT_COMPLETE, {"item": "хляб", "hb_list": "Пазар"}),
        ("какво има в Ремонт", INTENT_READ, {"hb_list": "Ремонт"}),
        ("какво имам да купя", INTENT_SHOPPING, {}),
        ("какво трябва да купя", INTENT_SHOPPING, {}),
        ("какво трябва да купя от Пазар", INTENT_SHOPPING, {"hb_list": "Пазар"}),
        ("какво да купя", INTENT_SHOPPING, {}),
        ("какво има за пазаруване", INTENT_SHOPPING, {}),
        ("какво ми трябва от магазина", INTENT_SHOPPING, {}),
        ("какво имам да правя", INTENT_TASKS, {}),
        ("какво трябва да свърша по Ремонт", INTENT_TASKS, {"hb_list": "Ремонт"}),
        ("какво има за правене", INTENT_TASKS, {}),
        ("кажи ми задачите в Ремонт", INTENT_TASKS, {"hb_list": "Ремонт"}),
        ("купих мляко", INTENT_COMPLETE, {"item": "мляко"}),
        ("сложи мляко в списъка", INTENT_ADD, {"item": "мляко"}),
        ("какво имам да правя по Ремонт", INTENT_TASKS, {"hb_list": "Ремонт"}),
        ("какви задачи имам в Ремонт", INTENT_TASKS, {"hb_list": "Ремонт"}),
    ],
    "en": [
        ("add milk to Пазар", INTENT_ADD, {"item": "milk", "hb_list": "Пазар"}),
        ("complete bread on Пазар", INTENT_COMPLETE, {"item": "bread", "hb_list": "Пазар"}),
        ("what is on Ремонт", INTENT_READ, {"hb_list": "Ремонт"}),
        ("what do I need to buy", INTENT_SHOPPING, {}),
        ("what should I buy", INTENT_SHOPPING, {}),
        ("what is left to buy", INTENT_SHOPPING, {}),
        ("what is on my shopping list", INTENT_SHOPPING, {}),
        ("what should I do", INTENT_TASKS, {}),
        ("I bought milk", INTENT_COMPLETE, {"item": "milk"}),
        ("what do I need to buy from Пазар", INTENT_SHOPPING, {"hb_list": "Пазар"}),
        ("what do I have to do", INTENT_TASKS, {}),
        ("what are my tasks on Ремонт", INTENT_TASKS, {"hb_list": "Ремонт"}),
    ],
}


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
    print(f"  ok  {label}")


def main() -> None:
    for language, phrases in SENTENCES.items():
        document = sentence_document(language, phrases, NAMES)

        # The line Home Assistant's conversation agent reads every intent with.
        for name, entry in document["intents"].items():
            blocks = entry.get("data", [])
            if not blocks or "sentences" not in blocks[0]:
                raise AssertionError(f"{language}/{name} carries no sentences")
        print(f"  ok  {language}: every intent is a mapping with data")

        # Every {slot} in a sentence has to be a list, or nothing matches.
        declared = set(document["lists"])
        for name, entry in document["intents"].items():
            for sentence in entry["data"][0]["sentences"]:
                for part in sentence.split("{")[1:]:
                    slot = part.split("}")[0]
                    if slot not in declared:
                        raise AssertionError(f"{language}/{name}: {slot} is not a list")
        print(f"  ok  {language}: every slot is declared")

        check(
            f"{language}: the lists that exist are offered",
            document["lists"]["hb_list"]["values"],
            NAMES,
        )
        check(
            f"{language}: what was said is free text",
            document["lists"]["item"]["wildcard"],
            True,
        )

    try:
        from hassil import Intents, recognize
    except ImportError:
        print("\nhassil is not installed; the shape was checked, matching was not")
        return

    for language, phrases in SENTENCES.items():
        parsed = Intents.from_dict(sentence_document(language, phrases, NAMES))
        for spoken, intent_name, expected in SPOKEN[language]:
            result = recognize(spoken, parsed)
            if result is None:
                raise AssertionError(f"{language}: nothing matched {spoken!r}")
            slots = {
                name: entity.value
                for name, entity in result.entities.items()
                if entity.value is not None
            }
            check(f"{language}: {spoken!r} is understood", result.intent.name, intent_name)
            check(f"{language}: ...with the right slots", slots, expected)

    # Every wording, not only the ones spelled out above: hassil expands the
    # alternatives and optional parts, and each one has to come back as the
    # intent it was written for.
    from hassil.sample import sample_intents

    for language, phrases in SENTENCES.items():
        parsed = Intents.from_dict(sentence_document(language, phrases, NAMES))
        seen = 0
        for intent_name, sampled in sample_intents(
            parsed, exclude_sentences_with_wildcards=False
        ):
            spoken = " ".join(sampled.replace("{item}", "мляко").split())
            result = recognize(spoken, parsed)
            if result is None:
                raise AssertionError(f"{language}: nothing matched {spoken!r}")
            if result.intent.name != intent_name:
                raise AssertionError(
                    f"{language}: {spoken!r} is {result.intent.name}, "
                    f"not {intent_name}"
                )
            seen += 1
        print(f"  ok  {language}: all {seen} wordings are understood")

    print("\nall Assist phrase checks passed")


if __name__ == "__main__":
    main()
