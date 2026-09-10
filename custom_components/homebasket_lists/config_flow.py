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
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_LINK_PRODUCTS,
    CONF_LINKED_LISTS,
    CONF_NAME,
    CONF_STORES,
    DEFAULT_LINK_PRODUCTS,
    DOMAIN,
)


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
            CONF_LINK_PRODUCTS,
            default=defaults.get(CONF_LINK_PRODUCTS, DEFAULT_LINK_PRODUCTS),
        ): bool,
    }


class HomeBasketListsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a list."""

    VERSION = 1

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
            return self.async_create_entry(data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_settings(defaults))
        )
