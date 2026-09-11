"""Checks the photos an item can carry, without a running Home Assistant.

A product HomeBasket knows brings its own picture; everything else can have one
of its own. Photos are files, so this test uses real ones in a temporary
folder:

    python3 tests/test_photos.py
"""

from __future__ import annotations

import asyncio
import base64
import shutil
import sys
import tempfile
import types
from pathlib import Path

for name in ("homeassistant", "homeassistant.core"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["homeassistant.core"].HomeAssistant = object

_COMPONENT = (
    Path(__file__).resolve().parent.parent / "custom_components" / "homebasket_lists"
)
_package = types.ModuleType("homebasket_lists")
_package.__path__ = [str(_COMPONENT)]
sys.modules["homebasket_lists"] = _package

from homebasket_lists.images import ImageStore, InvalidImage  # noqa: E402

# The smallest possible PNG and JPEG, as the card would send them.
PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xdb pretend").decode()


class FakeHass:
    """Just the two things the store asks of Home Assistant."""

    def __init__(self, root: Path) -> None:
        self.config = types.SimpleNamespace(
            path=lambda *parts: str(root.joinpath(*parts))
        )

    async def async_add_executor_job(self, func, *args):
        return func(*args)


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: got {actual!r}, expected {expected!r}")
    print(f"  ok  {label}")


async def main() -> None:
    root = Path(tempfile.mkdtemp())
    hass = FakeHass(root)

    shopping = ImageStore(hass, "list-one")
    repairs = ImageStore(hass, "list-two")
    for store in (shopping, repairs):
        await store.async_load()

    check("an item with no photo has none", shopping.has("item1"), False)
    check("and asking for it gives nothing", await shopping.async_get("item1"), None)

    await shopping.async_set("item1", PNG)
    check("a stored photo is remembered", shopping.has("item1"), True)
    check("and comes back as it went in", await shopping.async_get("item1"), PNG)

    await shopping.async_set("item1", JPEG)
    check("a second photo replaces the first", await shopping.async_get("item1"), JPEG)
    check(
        "without leaving the old file behind",
        len(list((root / ".storage" / "homebasket_lists_images" / "list-one").iterdir())),
        1,
    )

    # Two lists, one item id each: neither may see the other's.
    await repairs.async_set("item1", PNG)
    check("each list keeps its own photos", await repairs.async_get("item1"), PNG)
    check("and the other one is untouched", await shopping.async_get("item1"), JPEG)

    # Anything that is not an image is refused.
    for bad, why in (
        ("hello", "not a data URL"),
        ("data:image/gif;base64,AAAA", "a format we do not take"),
        ("data:image/png;base64,!!!!", "not base64"),
        ("data:image/png;base64,", "empty"),
    ):
        try:
            await shopping.async_set("item2", bad)
        except InvalidImage:
            print(f"  ok  {why} is refused")
        else:
            raise AssertionError(f"{why} was accepted")
    check("and nothing was written", shopping.has("item2"), False)

    # An item that is deleted takes its photo with it.
    await shopping.async_set("item2", PNG)
    check("deleting a photo says it did", await shopping.async_delete("item2"), True)
    check("deleting it twice does not", await shopping.async_delete("item2"), False)

    # Items can also vanish from a linked list, where nothing knows about
    # photos, so the stale ones are swept up.
    await shopping.async_set("item3", PNG)
    await shopping.async_set("item4", PNG)
    check("sweeping keeps what is still there", await shopping.async_keep_only(["item1", "item3"]), 1)
    check("...the kept one is still readable", await shopping.async_get("item3"), PNG)
    check("...and the swept one is gone", shopping.has("item4"), False)

    # A list that is deleted takes its folder with it.
    await shopping.async_drop_all()
    check("dropping a list leaves no photos", shopping.has("item1"), False)
    check(
        "...and no folder",
        (root / ".storage" / "homebasket_lists_images" / "list-one").exists(),
        False,
    )
    check("...while the other list is untouched", await repairs.async_get("item1"), PNG)

    # What a fresh start sees.
    again = ImageStore(hass, "list-two")
    await again.async_load()
    check("photos survive a restart", again.has("item1"), True)

    shutil.rmtree(root, ignore_errors=True)
    print("\nall photo checks passed")


if __name__ == "__main__":
    asyncio.run(main())
