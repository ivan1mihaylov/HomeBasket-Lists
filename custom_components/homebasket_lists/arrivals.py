"""Reminds you what to buy once you are actually in the shop.

A list can watch the people it belongs to. When one of them reaches a zone the
list calls a shop and stays there long enough to be shopping rather than
driving past, the phone that reported the arrival gets a notification with what
is still open for that shop - plus anything with no shop at all, since that can
be bought anywhere.

Everything about it is a setting of the list: whether to notify, who to watch,
how long they must stay, and how often the same shop may remind them.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util, slugify

from .const import (
    CONF_NOTIFY_ARRIVAL,
    CONF_NOTIFY_COOLDOWN,
    CONF_NOTIFY_DWELL,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_UNASSIGNED,
    CONF_NOTIFY_WATCH,
    DEFAULT_NOTIFY_ARRIVAL,
    DEFAULT_NOTIFY_COOLDOWN,
    DEFAULT_NOTIFY_DWELL,
    DEFAULT_NOTIFY_UNASSIGNED,
    DOMAIN,
    EVENT_ARRIVAL,
)
from .options import option
from .store import STATUS_NEEDS_ACTION

if TYPE_CHECKING:
    from .coordinator import ListRuntime

_LOGGER = logging.getLogger(__name__)

# States that mean "nowhere in particular".
NOWHERE = (STATE_NOT_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN, "")

# How many item names one notification carries before it just counts the rest.
NAMED = 8

WORDS = {
    "bg": {
        "title": "{shop}: {list}",
        "one": "1 нещо за купуване",
        "many": "{count} неща за купуване",
        "more": "и още {count}",
    },
    "en": {
        "title": "{shop}: {list}",
        "one": "1 thing to buy",
        "many": "{count} things to buy",
        "more": "and {count} more",
    },
}


def _words(language: str) -> dict[str, str]:
    """Return the notification wording for a language, falling back to English."""
    return WORDS.get((language or "en").split("-")[0].lower(), WORDS["en"])


def _amount(item: dict[str, Any]) -> str:
    """Return an item's name with its quantity, when it has one."""
    summary = item.get("summary") or ""
    try:
        number = float(item.get("quantity"))
    except (TypeError, ValueError):
        return summary

    written = str(int(number)) if number.is_integer() else f"{number:g}"
    if unit := (item.get("unit") or "").strip():
        written = f"{written} {unit}"
    return f"{summary} ({written})"


class ArrivalWatcher:
    """Watches people for one list and notifies them at its shops."""

    def __init__(self, hass: HomeAssistant, runtime: ListRuntime) -> None:
        """Initialise the watcher."""
        self.hass = hass
        self.runtime = runtime
        self._unsubscribe: Callable[[], None] | None = None
        self._waiting_for_start: Callable[[], None] | None = None
        # Who is in a shop waiting to have stayed long enough.
        self._waiting: dict[str, Callable[[], None]] = {}
        # When each person was last reminded about each shop.
        self._reminded: dict[tuple[str, str], Any] = {}

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        """Return whether this list notifies anyone at all."""
        return bool(
            option(self.runtime.entry, CONF_NOTIFY_ARRIVAL, DEFAULT_NOTIFY_ARRIVAL)
        )

    @property
    def watched(self) -> list[str]:
        """Return the people or devices being followed.

        Nobody chosen means every person in the house, which is what someone
        turning this on without naming anyone means.
        """
        value = option(self.runtime.entry, CONF_NOTIFY_WATCH, [])
        if isinstance(value, str):
            value = [value]
        chosen = [entity_id for entity_id in value or [] if entity_id]
        if chosen:
            return chosen
        return [state.entity_id for state in self.hass.states.async_all("person")]

    @property
    def dwell(self) -> float:
        """Return how many seconds in the shop count as being there."""
        minutes = option(self.runtime.entry, CONF_NOTIFY_DWELL, DEFAULT_NOTIFY_DWELL)
        try:
            return max(0.0, float(minutes) * 60)
        except (TypeError, ValueError):
            return DEFAULT_NOTIFY_DWELL * 60

    @property
    def cooldown(self) -> timedelta:
        """Return how long a shop stays quiet after reminding someone."""
        minutes = option(
            self.runtime.entry, CONF_NOTIFY_COOLDOWN, DEFAULT_NOTIFY_COOLDOWN
        )
        try:
            return timedelta(minutes=max(0.0, float(minutes)))
        except (TypeError, ValueError):
            return timedelta(minutes=DEFAULT_NOTIFY_COOLDOWN)

    @property
    def include_unassigned(self) -> bool:
        """Return whether items with no shop go on every reminder."""
        return bool(
            option(
                self.runtime.entry, CONF_NOTIFY_UNASSIGNED, DEFAULT_NOTIFY_UNASSIGNED
            )
        )

    @property
    def fallback_service(self) -> tuple[str, str] | None:
        """Return the service to notify when the arriving device is unknown."""
        configured = str(
            option(self.runtime.entry, CONF_NOTIFY_SERVICE, "") or ""
        ).strip()
        if not configured:
            return None
        domain, _, service = configured.partition(".")
        if not service:
            return "notify", domain
        return domain, service

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Start watching, once there is anyone to watch."""
        if not self.enabled or not self.runtime.stores:
            return

        if self.hass.is_running:
            self._async_watch()
            return

        # People are entities too, and during a restart they may not exist yet,
        # so a list set up before them would watch an empty house.
        self._waiting_for_start = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, self._async_started
        )

    @callback
    def _async_started(self, _event: Any) -> None:
        """Everyone exists now."""
        self._waiting_for_start = None
        self._async_watch()

    @callback
    def _async_watch(self) -> None:
        """Follow the people this list cares about."""
        if not (watched := self.watched):
            _LOGGER.debug(
                "%s notifies on arrival but nobody is watched", self.runtime.name
            )
            return

        self._unsubscribe = async_track_state_change_event(
            self.hass, watched, self._async_moved
        )

    async def async_unload(self) -> None:
        """Stop watching and drop any pending reminder."""
        for name in ("_unsubscribe", "_waiting_for_start"):
            if (stop := getattr(self, name)) is not None:
                stop()
                setattr(self, name, None)
        while self._waiting:
            _, cancel = self._waiting.popitem()
            cancel()

    # ------------------------------------------------------------------
    # Arriving and leaving
    # ------------------------------------------------------------------
    @callback
    def _async_moved(self, event: Event) -> None:
        """Note that someone changed where they are."""
        entity_id = event.data["entity_id"]
        was = self._zone_of(event.data.get("old_state"))
        now = self._zone_of(event.data.get("new_state"))
        if was == now:
            # An attribute changed, or they moved between two places that are
            # not shops of this list. Neither starts or stops anything.
            return

        # Leaving cancels the wait, so only staying counts.
        if (cancel := self._waiting.pop(entity_id, None)) is not None:
            cancel()
        if now is None:
            return

        if not self.dwell:
            self.hass.async_create_task(self._async_arrived(entity_id, now))
            return

        @callback
        def _stayed(_now: Any) -> None:
            self._waiting.pop(entity_id, None)
            self.hass.async_create_task(self._async_arrived(entity_id, now))

        self._waiting[entity_id] = async_call_later(self.hass, self.dwell, _stayed)

    def _zone_of(self, state: Any) -> str | None:
        """Return which of this list's shops a state is in, if any."""
        if state is None or state.state in NOWHERE:
            return None

        here = str(state.state).casefold().strip()
        for zone in self.runtime.stores:
            if zone == "zone.home" and here == STATE_HOME:
                return zone
            if here == self.runtime.zone_name(zone).casefold().strip():
                return zone
        return None

    async def _async_arrived(self, entity_id: str, zone: str) -> None:
        """Someone has been in one of our shops long enough. Tell them."""
        if self._zone_of(self.hass.states.get(entity_id)) != zone:
            return  # They left while we were waiting.

        moment = dt_util.utcnow()
        last = self._reminded.get((entity_id, zone))
        if last is not None and moment - last < self.cooldown:
            return

        if not (items := self._items_for(zone)):
            return

        self._reminded[(entity_id, zone)] = moment
        shop = self.runtime.zone_name(zone)
        title, message = self._message(shop, items)
        target = self._async_target(entity_id)

        self.hass.bus.async_fire(
            EVENT_ARRIVAL,
            {
                "entry_id": self.runtime.entry.entry_id,
                "list": self.runtime.name,
                "zone": zone,
                "shop": shop,
                "entity_id": entity_id,
                "count": len(items),
                "items": [item["summary"] for item in items],
                "notified": ".".join(target) if target else None,
            },
        )
        await self._async_send(target, title, message, zone)

    def _items_for(self, zone: str) -> list[dict[str, Any]]:
        """Return what is still open for one shop."""
        found = []
        for item in self.runtime.store.items:
            if item.get("status") != STATUS_NEEDS_ACTION:
                continue
            store = item.get("store")
            if store == zone or (store in (None, "") and self.include_unassigned):
                found.append(item)
        return found

    def _message(self, shop: str, items: list[dict[str, Any]]) -> tuple[str, str]:
        """Return the notification's title and body."""
        words = _words(self.hass.config.language)
        title = words["title"].format(shop=shop, list=self.runtime.name)

        count = len(items)
        head = words["one"] if count == 1 else words["many"].format(count=count)
        names = [_amount(item) for item in items[:NAMED]]
        if count > NAMED:
            names.append(words["more"].format(count=count - NAMED))
        return title, f"{head}: {', '.join(names)}"

    # ------------------------------------------------------------------
    # Reaching the right phone
    # ------------------------------------------------------------------
    def _async_target(self, entity_id: str) -> tuple[str, str] | None:
        """Return the service that reaches the device that arrived."""
        tracker = entity_id
        if entity_id.startswith("person."):
            state = self.hass.states.get(entity_id)
            # A person is wherever their phone says they are, and `source` is
            # the tracker that said so - which is the phone to notify.
            tracker = (state.attributes.get("source") if state else None) or entity_id

        if (service := self._async_mobile_app(tracker)) is not None:
            return "notify", service
        return self.fallback_service

    def _async_mobile_app(self, tracker: str) -> str | None:
        """Return the mobile app notify service of a tracker's device."""
        entity = er.async_get(self.hass).async_get(tracker)
        if entity is None or entity.device_id is None:
            return None
        device = dr.async_get(self.hass).async_get(entity.device_id)
        if device is None:
            return None

        # The service is named after the device as it registered itself, which
        # renaming it in the interface does not change - so try both.
        for name in (device.name, device.name_by_user):
            if not name:
                continue
            service = f"mobile_app_{slugify(name)}"
            if self.hass.services.has_service("notify", service):
                return service
        return None

    async def _async_send(
        self, target: tuple[str, str] | None, title: str, message: str, zone: str
    ) -> None:
        """Send the reminder, or leave it in the notifications panel."""
        tag = f"{DOMAIN}_{self.runtime.entry.entry_id}_{zone}"
        if target is None:
            _LOGGER.debug(
                "No notify service for %s, using the panel", self.runtime.name
            )
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {"title": title, "message": message, "notification_id": tag},
                blocking=False,
            )
            return

        domain, service = target
        try:
            await self.hass.services.async_call(
                domain,
                service,
                {"title": title, "message": message, "data": {"tag": tag}},
                blocking=False,
            )
        except Exception:  # noqa: BLE001 - a missing phone must not break the list
            _LOGGER.warning(
                "Could not notify through %s.%s", domain, service, exc_info=True
            )
