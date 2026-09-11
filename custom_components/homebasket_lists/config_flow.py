"""Config flow for HomeBasket Lists.

One config entry is one list, so a second list is another entry rather than a
setting inside the first.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_DUPLICATES,
    CONF_ITEM_TYPES,
    CONF_LINK_PRODUCTS,
    CONF_LINKED_LISTS,
    CONF_NAME,
    CONF_NOTIFY_ARRIVAL,
    CONF_NOTIFY_COOLDOWN,
    CONF_NOTIFY_DWELL,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_UNASSIGNED,
    CONF_NOTIFY_WATCH,
    CONF_DEPARTMENT_ZONES,
    CONF_STORES,
    DEPARTMENTS,
    DEFAULT_DUPLICATES,
    DEFAULT_ITEM_TYPES,
    DEFAULT_LINK_PRODUCTS,
    DEFAULT_NOTIFY_ARRIVAL,
    DEFAULT_NOTIFY_COOLDOWN,
    DEFAULT_NOTIFY_DWELL,
    DEFAULT_NOTIFY_UNASSIGNED,
    DOMAIN,
    DUPLICATES,
    ITEM_TYPES,
)


def _minutes(maximum: float) -> NumberSelector:
    """Return a field for a number of minutes."""
    return NumberSelector(
        NumberSelectorConfig(
            min=0,
            max=maximum,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="min",
        )
    )


# Each department's zones travel as their own field - a selector cannot edit a
# dictionary - and are folded back into one setting on the way out.
DEPARTMENT_ZONE_PREFIX = "zones_"


def _department_fields(defaults: dict[str, Any]) -> dict:
    """Return one zone picker per kind of shop.

    Naming no zone for a department means it is worth a reminder everywhere,
    which is what everything did before there were departments.
    """
    zones = defaults.get(CONF_DEPARTMENT_ZONES) or {}
    if not isinstance(zones, dict):
        zones = {}
    return {
        vol.Optional(
            f"{DEPARTMENT_ZONE_PREFIX}{department}",
            default=zones.get(department, []),
        ): EntitySelector(EntitySelectorConfig(domain="zone", multiple=True))
        for department in DEPARTMENTS
    }


def _fold_departments(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return the input with the per-department fields as one setting."""
    folded = dict(user_input)
    zones = {}
    for department in DEPARTMENTS:
        picked = folded.pop(f"{DEPARTMENT_ZONE_PREFIX}{department}", None) or []
        if picked:
            zones[department] = list(picked)
    folded[CONF_DEPARTMENT_ZONES] = zones
    return folded


def _settings(defaults: dict[str, Any]) -> dict:
    """Return the fields shared by the config and the options flow."""
    return {
        vol.Optional(
            CONF_LINKED_LISTS, default=defaults.get(CONF_LINKED_LISTS, [])
        ): EntitySelector(EntitySelectorConfig(domain="todo", multiple=True)),
        vol.Optional(
            CONF_STORES, default=defaults.get(CONF_STORES, [])
        ): EntitySelector(EntitySelectorConfig(domain="zone", multiple=True)),
        vol.Optional(
            CONF_ITEM_TYPES, default=defaults.get(CONF_ITEM_TYPES, DEFAULT_ITEM_TYPES)
        ): SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=kind, label=kind) for kind in ITEM_TYPES
                ],
                multiple=True,
                mode=SelectSelectorMode.LIST,
                translation_key=CONF_ITEM_TYPES,
            )
        ),
        vol.Optional(
            CONF_DUPLICATES, default=defaults.get(CONF_DUPLICATES, DEFAULT_DUPLICATES)
        ): SelectSelector(
            SelectSelectorConfig(
                options=[SelectOptionDict(value=mode, label=mode) for mode in DUPLICATES],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_DUPLICATES,
            )
        ),
        vol.Optional(
            CONF_LINK_PRODUCTS,
            default=defaults.get(CONF_LINK_PRODUCTS, DEFAULT_LINK_PRODUCTS),
        ): bool,
        vol.Optional(
            CONF_NOTIFY_ARRIVAL,
            default=defaults.get(CONF_NOTIFY_ARRIVAL, DEFAULT_NOTIFY_ARRIVAL),
        ): bool,
        vol.Optional(
            CONF_NOTIFY_WATCH, default=defaults.get(CONF_NOTIFY_WATCH, [])
        ): EntitySelector(
            EntitySelectorConfig(domain=["person", "device_tracker"], multiple=True)
        ),
        vol.Optional(
            CONF_NOTIFY_DWELL,
            default=defaults.get(CONF_NOTIFY_DWELL, DEFAULT_NOTIFY_DWELL),
        ): _minutes(120),
        vol.Optional(
            CONF_NOTIFY_COOLDOWN,
            default=defaults.get(CONF_NOTIFY_COOLDOWN, DEFAULT_NOTIFY_COOLDOWN),
        ): _minutes(1440),
        vol.Optional(
            CONF_NOTIFY_UNASSIGNED,
            default=defaults.get(CONF_NOTIFY_UNASSIGNED, DEFAULT_NOTIFY_UNASSIGNED),
        ): bool,
        vol.Optional(
            CONF_NOTIFY_SERVICE, default=defaults.get(CONF_NOTIFY_SERVICE, "")
        ): TextSelector(TextSelectorConfig()),
    }


class HomeBasketListsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a list."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the list's name and what it is linked to."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "empty_name"
            else:
                self._async_abort_entries_match({CONF_NAME: name})
                return self.async_create_entry(title=name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(TextSelectorConfig()),
                **_settings({}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return HomeBasketListsOptionsFlow()


class HomeBasketListsOptionsFlow(OptionsFlow):
    """Change what a list is linked to, and which zones are its shops."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the options."""
        if user_input is not None:
            return self.async_create_entry(data=_fold_departments(user_input))

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {**_settings(defaults), **_department_fields(defaults)}
            ),
        )
