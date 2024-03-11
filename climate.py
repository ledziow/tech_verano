"""Support for TECH-VERANO HVAC system."""
import logging
import json
from typing import List, Optional
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    HVACMode,
    HVACAction
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.FAN_MODE
)

PRESET_SCHEDULE1 = "schedule1"
PRESET_SCHEDULE2 = "schedule2"
PRESET_SCHEDULE3 = "schedule3"
PRESET_SCHEDULE_WEEKLY = "schedule_weekly"
PRESET_COMFORT = "comfort"
PRESET_ECO = "eco"
PRESET_PROTECTION = "protection"

THERM_MODES = (
    PRESET_SCHEDULE1,
    PRESET_SCHEDULE2,
    PRESET_SCHEDULE3,
    PRESET_SCHEDULE_WEEKLY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_PROTECTION
    )

FAN_MODES = (
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""

    _LOGGER.debug("Setting up entry, module udid: " + config_entry.data["udid"])

    TECH_VERANO_OBJ = hass.data[DOMAIN][config_entry.entry_id]
    devices = await TECH_VERANO_OBJ.list_modules()

    async_add_entities(
        [
            TECHVERANOThermostat(
                device,
                TECH_VERANO_OBJ,
                config_entry,
            )
            for device in devices
        ],
        True,
    )


class TECHVERANOThermostat(ClimateEntity, RestoreEntity):
    """Representation of a Tech-Verano climate."""


    def __init__(self, device, TECH_VERANO_OBJ, config):
        """Initialize the Tech-Verano device."""

        _LOGGER.debug("Init Tech-Verano Thermostat...")
        _LOGGER.debug("Config data: %s", str(config.data))
        self._config = config
        self._attr_unique_id = config.entry_id
        self._TECH_VERANO_OBJ = TECH_VERANO_OBJ
        self._name = device["name"]
        self._id = device["id"]
        self._udid = device["udid"]
        self._ver = device["version"]

        self._attr_hvac_action = HVACAction.IDLE
        self._attr_hvac_mode = HVACMode.AUTO

        self._target_temp = 21
        self._current_temp = None
        self._attr_target_temperature_high = 22
        self._attr_target_temperature_low = 18
        self._attr_min_temp = 7
        self._attr_max_temp = 30
        self._attr_target_temperature_step = 0.1
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        
        self._attr_fan_mode = FAN_AUTO
        self._attr_preset_mode = PRESET_SCHEDULE_WEEKLY
        self._attr_preset_modes = THERM_MODES


    def update_properties(self, module_data):
        """ Upadate device properties.
        """

        try:
            _LOGGER.info("Update Tech-Verano Thermostat data started ...")
            
            if module_data:
                # HVAC Mode
                _LOGGER.debug(f"Object module_data: {module_data}")
                if (hvac_state_data := module_data[53]) is not None:
                    for i in hvac_state_data:
                        if "Heating" in i:
                            self._attr_hvac_mode = HVACMode.HEAT
                            break
                        elif "Cooling" in i:
                            self._attr_hvac_mode = HVACMode.COOL
                            break
                # Current Temp       
                if (temp_data := module_data.get(58)) is not None:
                    for i in temp_data:
                        if "Current temperature" in i:
                            self._current_temp = i[1]
                            _LOGGER.debug(f"Set current_temp: {i[1]}")
                            continue
                        if "Set temp." in i:
                            self._target_temp = i[1]
                            _LOGGER.debug(f"Set target_temp: {i[1]}")
                            continue
                # Fan speed        
                if (fan_mode_data := module_data.get(63)) is not None:
                    for i in fan_mode_data:
                        if "Mode" in i:
                            if "Automatic mode" in i[1]:
                                self._current_fan_mode = FAN_AUTO
                            continue

                if (fan_data := module_data.get(62)) is not None:
                    for i in fan_data:
                        if "Fan 0-10 V (F)" in i:
                            if i[1] == 0:
                                self._attr_hvac_action = HVACAction.IDLE
                            else:
                                self._attr_hvac_action = HVACAction.HEATING
                            continue
                # Profile
                if (profile_data := module_data.get(54)) is not None:
                    for i in profile_data:
                        if "Profile" in i:
                            if "Weekly schedule" in i[1]:
                                self._attr_hvac_mode = HVACMode.AUTO
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
        return SUPPORT_FLAGS

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        return self._attr_hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return [HVACMode.COOL,HVACMode.HEAT, HVACMode.AUTO]

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        return self._attr_hvac_action
    
    @property
    def fan_modes(self):
        """Return the list of available fan operation modes.

        Need to be a subset of FAN_MODES.
        """
        return FAN_MODES
    
    @property
    def preset_modes(self):
        """Return the list of available THERM operation modes.

        Need to be a subset of THERM_MODES.
        """
        return THERM_MODES

    async def async_update(self):
        """Call by the Tech device callback to update state."""
        
        _LOGGER.debug("Updating Tech VERANO: %s, udid: %s, id: %s", self._name, self._udid, self._id)
        module_data = await self._TECH_VERANO_OBJ.get_module_tiles(self._udid)
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
        """Return the temperature we try to xreach."""
        return self._target_temp
    

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.info("%s [%s] : Setting temp to %s", self._name, self._id, temperature)
        try:
            if temperature:
                self._temperature = temperature
                r = await self._TECH_VERANO_OBJ.set_const_temp(self._udid, self._id, temperature)
                _LOGGER.info("%s [%s] : Setting temp to %s, results: %s.", self._name, self._id, temperature, r)
        except Exception as e:
            _LOGGER.error("%s [%s] : Setting temp to %s failed. Error: %s.", self._name, self._id, temperature, e)
            if e.status_code == 401:
                _LOGGER.debug("Starting re-auth process.")
                r = await self._TECH_VERANO_OBJ.authenticate(self._config.data["user"],self._config.data["pass"])
                r = await self.async_set_temperature(self, **kwargs)


    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        _LOGGER.debug("%s: Setting hvac mode to %s", self._name, hvac_mode)
        """ if hvac_mode == HVAC_MODE_OFF:
            await self._api.set_zone(self._config_entry.data["udid"], self._id, False)
        elif hvac_mode == HVAC_MODE_HEAT:
            await self._api.set_zone(self._config_entry.data["udid"], self._id, True) """
        
    
    async def async_set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""

        _LOGGER.debug("%s: Setting present mode to %s", self._name, preset_mode)
        
        if preset_mode not in (self._attr_preset_modes or []):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {self._attr_preset_modes}"
            )
        if preset_mode == self._attr_preset_mode:
            return
        else:
            try:
                self._attr_preset_mode = preset_mode
                r = await self._TECH_VERANO_OBJ.set_preset_mode(self._udid, self._id, preset_mode)
                _LOGGER.info("%s [%s] : Setting present mode to %s, results: %s.", self._name, self._id, preset_mode, r)
            except Exception as e:
                _LOGGER.error("%s [%s] : Setting present mode to %s failed. Error: %s.", self._name, self._id, preset_mode, e)
                if e.status_code == 401:
                    _LOGGER.debug("Starting re-auth process.")
                    r = await self._TECH_VERANO_OBJ.authenticate(self._config.data["user"],self._config.data["pass"])
                    r = await self.async_set_preset_mode(self, preset_mode)

