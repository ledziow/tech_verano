"""Config flow for Tech Verano integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client
from .verano import TECH_VERANO

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    http_session = aiohttp_client.async_get_clientsession(hass)
    api = TECH_VERANO(http_session)

    if not await api.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD]):
        raise InvalidAuth
    
    modules = await api.list_modules()
    # Currently only one Tech controller supported
    module = modules[0]

    # Return info that you want to store in the config entry.
    return {
        "user_id": api.user_id,
        "user": data[CONF_USERNAME],
        "pass": data[CONF_PASSWORD],
        "token": api.token,
        "udid": module["udid"],
        "version": module["version"],
        "selectedModuleIndex": api.selectedModuleIndex,
        "name": module["name"]
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tech Verano."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        _LOGGER.debug(f"ConfigFlow user_input: {str(user_input)}")

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title="Tech - VERANO", data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
