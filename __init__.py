"""The Tech Verano integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN
from .verano import TECH_VERANO

# ----------- GLOBAL ----------- #
_LOGGER = logging.getLogger(__name__)
# ----------- GLOBAL ----------- #

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tech Verano from a config entry."""

    _LOGGER.debug("Setting up component's entry.")
    _LOGGER.debug("Entry -> title: " + entry.title + ", data: " + str(entry.data) + ", id: " + entry.entry_id + ", domain: " + entry.domain + ", entry: " + entry)
    

    hass.data.setdefault(DOMAIN, {})
    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    http_session = aiohttp_client.async_get_clientsession(hass)
    hass.data[DOMAIN][entry.entry_id] = TECH_VERANO(http_session, entry.data["user_id"], entry.data["token"])
    
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, PLATFORMS)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
