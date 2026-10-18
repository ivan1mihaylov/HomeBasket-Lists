"""Checks that another integration can send a picture with an item.

    python3 tests/test_api_photo.py
"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

for name in ("homeassistant", "homeassistant.core", "homeassistant.helpers", "homeassistant.helpers.storage", "homeassistant.util"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.core"].callback = lambda func: func
sys.modules["homeassistant.helpers.storage"].Store = object
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(utcnow=lambda: None, now=lambda: None)

_COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.api import API_VERSION, HomeBasketListsAPI  # noqa: E402
from homebasket_lists.const import DOMAIN  # noqa: E402
from homebasket_lists.images import _decode  # noqa: E402

PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise SystemExit(f"FAIL {label}: {actual!r} != {expected!r}")
    print(f"  ok  {label}")


class _Images:
    def __init__(self) -> None:
        self.photos: dict[str, str] = {}

    def has(self, uid: str) -> bool:
        return uid in self.photos

    async def async_set(self, uid: str, data_url: str) -> None:
        _decode(data_url)
        self.photos[uid] = data_url


class _Runtime:
    def __init__(self) -> None:
        self.entry = types.SimpleNamespace(entry_id="list1")
        self.name = "Покупки"
        self.images = _Images()
        self.items: dict[str, dict] = {}
        self.notified = 0

    async def async_add_or_increase(self, summary: str, **fields):
        if "photo" in fields:
            raise AssertionError("the photo must not reach the item's fields")
        item = self.items.setdefault(summary, {"uid": f"uid-{len(self.items)}", "summary": summary, **fields})
        return item, "added"

    def async_notify(self) -> None:
        self.notified += 1


async def main() -> None:
    runtime = _Runtime()
    hass = types.SimpleNamespace(data={DOMAIN: {"list1": runtime}})
    api = HomeBasketListsAPI(hass)
    check("version says photos are taken", (api.api_version, API_VERSION >= 2), (2, True))

    result = await api.async_add_item("Сьомга", quantity=1, photo=PNG)
    uid = result["item"]["uid"]
    check("the photo is the item's own", runtime.images.photos.get(uid), PNG)
    check("the card is told", runtime.notified, 1)

    await api.async_add_item("Сьомга", photo=PNG.replace("iVBOR", "iVBOX"))
    check("an item's photo is kept", runtime.images.photos.get(uid), PNG)

    result = await api.async_add_item("Домати", photo="data:text/plain;base64,aGk=")
    check("a bad picture still adds the item", (result["item"]["summary"], runtime.images.has(result["item"]["uid"])), ("Домати", False))

    result = await api.async_add_item("Боб")
    check("no photo, nothing stored", runtime.images.has(result["item"]["uid"]), False)
    check("only the good picture notified", runtime.notified, 1)
    print("\nall api photo checks passed")


asyncio.run(main())
