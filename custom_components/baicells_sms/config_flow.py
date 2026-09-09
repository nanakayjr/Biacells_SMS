"""Config flow for Baicells SMS."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    CONF_COMMAND_TIMEOUT,
    CONF_DELETE_AFTER_READ,
    CONF_DEVICE_PATH,
    CONF_LOGO_PATH,
    CONF_POLL_INTERVAL,
    CONF_STRICT_HOST_KEY,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_DELETE_AFTER_READ,
    DEFAULT_DEVICE_PATH,
    DEFAULT_LOGO_PATH,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_STRICT_HOST_KEY,
    DOMAIN,
)


def _build_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "192.168.150.1")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "root")): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
            vol.Required(
                CONF_DEVICE_PATH,
                default=defaults.get(CONF_DEVICE_PATH, DEFAULT_DEVICE_PATH),
            ): str,
            vol.Required(
                CONF_POLL_INTERVAL,
                default=defaults.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            ): vol.All(int, vol.Range(min=30, max=86400)),
            vol.Required(
                CONF_COMMAND_TIMEOUT,
                default=defaults.get(CONF_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT),
            ): vol.All(int, vol.Range(min=5, max=120)),
            vol.Required(
                CONF_DELETE_AFTER_READ,
                default=defaults.get(CONF_DELETE_AFTER_READ, DEFAULT_DELETE_AFTER_READ),
            ): bool,
            vol.Required(
                CONF_STRICT_HOST_KEY,
                default=defaults.get(CONF_STRICT_HOST_KEY, DEFAULT_STRICT_HOST_KEY),
            ): bool,
            vol.Optional(
                CONF_LOGO_PATH,
                default=defaults.get(CONF_LOGO_PATH, DEFAULT_LOGO_PATH),
            ): str,
        }
    )


class BaicellsSmsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Baicells SMS."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle first setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Baicells {user_input[CONF_HOST]}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return BaicellsSmsOptionsFlow()


class BaicellsSmsOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_build_schema(defaults))

    
    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
    #     """Return the options flow for this integration."""
    #     return BaicellsSmsOptionsFlow(config_entry)


# class BaicellsSmsOptionsFlow(config_entries.OptionsFlow):
#     """Handle options flow for Baicells SMS."""

#     async def async_step_init(self, user_input: dict[str, Any] | None = None):
#         """Manage the integration options."""
#         if user_input is not None:
#             return self.async_create_entry(title="", data=user_input)

#         defaults = {**self.config_entry.data, **self.config_entry.options}
#         return self.async_show_form(step_id="init", data_schema=_build_schema(defaults))
