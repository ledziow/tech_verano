"""Support for TECH-VERANO HVAC system."""
import logging
import json
from typing import List, Optional
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.climate.const import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_CURRENT_HUMIDITY,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    HVACMode,
    HVACAction
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
    STATE_ON,
    UnitOfTemperature
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""

    _LOGGER.debug("Setting up entry, module udid: " + config_entry.data["udid"])

    api = hass.data[DOMAIN][config_entry.entry_id]
    devices = await api.list_modules()

    async_add_entities(
        [
            TECHVERANOThermostat(
                device,
                api,
                config_entry,
            )
            for device in devices
        ],
        True,
    )


class TECHVERANOThermostat(ClimateEntity, RestoreEntity):
    """Representation of a Tech-Verano climate."""


    def __init__(self, device, api, config):
        """Initialize the Tech-Verano device."""

        _LOGGER.debug("Init Tech-Verano Thermostat...")
        self._config = config
        #self._attr_unique_id = config.data["udid"]
        self._attr_unique_id = config.entry_id
        self._api = api
        self._name = device["name"]
        self._id = device["id"]
        self._udid = device["udid"]
        self._ver = device["version"]
        #self.update_properties()

        self._available = True
        self._current_temp = None

        self._current_fan_mode = FAN_AUTO # default optimistic state
        self._current_operation = HVACMode.OFF  # default optimistic state
        self._target_temp = 21  # default optimistic state
        self._attr_target_temperature_high = None
        self._attr_target_temperature_low = None
        self._attr_max_temp = 25
        self._attr_min_temp = 9


    def update_properties(self, module_data):
        """ Upadate device properties.
        """

        try:
            _LOGGER.info("Update Tech-Verano Thermostat data started ...")
            
            if module_data:
                # HVAC Mode
                _LOGGER.debug(f"Object module_data: {module_data}")
                if (hvac_state_data := module_data[53]) is not None:
                    self._current_operation = HVACMode.OFF
                    for i in hvac_state_data:
                        if "Heating" in i:
                            self._current_operation = HVACMode.HEAT
                            break
                        elif "Cooling" in i:
                            self._current_operation = HVACMode.COOL
                            break
                # Current Temp       
                if (temp_data := module_data.get(58)) is not None:
                    for i in temp_data:
                        if "Current temperature" in i:
                            self._current_temp = i[1]
                            continue
                        if "Set temp" in i:
                            self._target_temp = i[1]
                            continue
                # Fan speed        
                if (temp_data := module_data.get(63)) is not None:
                    for i in temp_data:
                        if "Mode" in i:
                            if "Automatic mode" in i[1]:
                                self._current_fan_mode = FAN_AUTO
                            continue

            else:
                _LOGGER.debug("No module data, No updates.")

        except Exception as e:
            _LOGGER.error(f"Update Tech-Verano Thermostat data failed. ERROR: {str(e)}")


    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id
    
    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        return self._current_operation

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return [HVACMode.OFF,HVACMode.COOL,HVACMode.HEAT]

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        return self.state

    async def async_update(self):
        """Call by the Tech device callback to update state."""
        
        _LOGGER.debug("Updating Tech VERANO: %s, udid: %s, id: %s", self._name, self._udid, self._id)

        module_data = await self._api.get_module_tiles(self._udid)
        #await self._api.get_zone(self._config_entry.data["udid"], self._id)
        self.update_properties(module_data)

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    async def async_set_temperature(self, temp):
        """Set new target temperatures."""

        _LOGGER.debug("%s: Setting temp to %s", self._name, temp)
        """ temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature:
            _LOGGER.debug("%s: Setting temperature to %s", self._name, temperature)
            self._temperature = temperature
            await self._api.set_const_temp(self._config_entry.data["udid"], self._id, temperature) """

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        _LOGGER.debug("%s: Setting hvac mode to %s", self._name, hvac_mode)
        """ if hvac_mode == HVAC_MODE_OFF:
            await self._api.set_zone(self._config_entry.data["udid"], self._id, False)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self._api.set_zone(self._config_entry.data["udid"], self._id, True) """

