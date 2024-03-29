import logging
import aiohttp
import json
import time
import asyncio

logging.basicConfig(level=logging.DEBUG)

# ----------- GLOBAL ----------- #
_LOGGER = logging.getLogger(__name__)
# ----------- GLOBAL ----------- #

class TECH_VERANO:
    """Main class to perform Tech API requests"""

    TECH_API_URL = "https://emodul.eu/"

    def __init__(self, session: aiohttp.ClientSession, user_id = None, token = None, 
                 base_url = TECH_API_URL, update_interval = 30):
       
        _LOGGER.debug("Init TECH_VERANO class object.")

        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
        }

        self.base_url = base_url
        self.update_interval = update_interval
        self.session = session

        if user_id and token:
            self.user_id = user_id
            self.token = token
            self.headers.setdefault("Authorization", "Bearer " + token)
            self.authenticated = True
        else:
            self.authenticated = False

        self.last_update = None
        self.update_lock = asyncio.Lock()
        self.zones = {}
        self.tiles = {}
        self.selectedModuleIndex = None
        self.selectedModuleHash = None
        self.language_strings_dict = None


    async def tech_get(self, request_path: str, headers: dict):
        """ A wrapper for GET request
        """

        url = self.base_url + request_path

        _LOGGER.debug("Sending GET request to Tech API: " + url)

        async with self.session.get(url, headers=headers) as response:

            if response.status != 200:
                _LOGGER.warning("Invalid response from Tech API: %s", response.status)
                raise TechError(response.status, await response.text())

            data = await response.json()
            await self.update_cookies(response=response)

            _LOGGER.debug("Tech API GET request headers: %s", str(response.request_info.headers))
            _LOGGER.debug("Tech API GET response headers: %s", str(response.headers))

            return data
        
    
    async def tech_post(self, request_path: str, post_data: str, headers: dict):
        """ A wrapper for POST request
        """
        
        url = self.base_url + request_path

        _LOGGER.debug("Sending POST request to Tech API: " + url)

        async with self.session.post(url, data=post_data, headers=headers) as response:
            _LOGGER.debug("Tech API POST request data: %s", str(post_data))
            _LOGGER.debug("Tech API POST request headers: %s", str(response.request_info.headers))
            _LOGGER.debug("Tech API POST response headers: %s", str(response.headers))
            if response.status != 200:
                _LOGGER.warning("Invalid response from Tech API: %s", response.status)
                raise TechError(response.status, await response.text())

            data = await response.json()
            await self.update_cookies(response=response)
            
            _LOGGER.debug("Tech API POST response: %s", data)
            
            return data
        
            
    async def update_cookies(self, response: aiohttp.ClientResponse):
        
        from http.cookies import SimpleCookie, Morsel

        cookie_set = SimpleCookie()
        _LOGGER.debug("Updating cookies for Tech API ...")

        try:
            for k in response.raw_headers:
                if "Set-Cookie" in k[0].decode():
                    cookie_elements = [x.strip() for x in k[1].decode("utf-8").split(';')]

                    # Get name of cookie from first row
                    c_row = [x.strip() for x in cookie_elements[0].split('=')]

                    cookie_set[c_row[0]] = c_row[1]

                    for i in cookie_elements:
                        if '=' in i:
                            c = [x.strip() for x in i.split('=')]
                            if len(c) == 2 and c[0] != c_row[0]:
                                cookie_set[c_row[0]][c[0]] = c[1]
                    cookie_set[c_row[0]]['HttpOnly'] = True
                    cookie_set[c_row[0]]['secure'] = True
                    cookie_set[c_row[0]]['domain'] = 'emodul.eu'

                    if len(cookie_set) > 0:
                        self.session.cookie_jar.update_cookies(cookie_set)
                        _LOGGER.debug("Cookies for Tech API were updated!")

        except Exception as e:
            _LOGGER.error(f"Parsing 'Set-cookies' cookie for Tech API failed, Error: {e}")
        

    async def authenticate(self, username: str, password: str):
        """ Authetication
        """

        path = "frontend/login"
        post_data = {
            "username": username,
            "password": password,
            "rememberMe": False,
            "languageId": "en",
            "remote": False
        }
        headers = self.headers
        headers.update({
            "Referer": "https://emodul.eu/login",
            "Origin": "https://emodul.eu"
        })

        _LOGGER.info("TECH_VERANO authentication.")

        try:
            _LOGGER.info(f"TECH_VERANO auth at login page: {path}")
            result = await self.tech_post(request_path=path, post_data=json.dumps(post_data), headers=headers)
            self.authenticated = result["authenticated"]
            if self.authenticated:
                self.selectedModuleHash = result["selectedModuleHash"]
                self.selectedModuleIndex = result["selectedModuleIndex"]
            
            
            path = "api/v1/authentication"
            _LOGGER.info(f"TECH_VERANO auth at login page: {path}")
            result = await self.tech_post(request_path=path, post_data=json.dumps(post_data), headers=headers)
            
            self.authenticated = result["authenticated"]

            if self.authenticated:
                self.user_id = str(result["user_id"])
                self.token = result["token"]
                self.headers = {
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip',
                    'Authorization': 'Bearer ' + self.token
                }

        except Exception as e:
            _LOGGER.error("TECH_VERANO authentication failed, error: %s", e)

        return result["authenticated"]
    

    async def is_authenticated(self):
        """ Check auth
        """

        if self.authenticated:
            _LOGGER.debug(f"Checking if the user {self.user_id} is authenticated ...")
            
            path = "frontend/is_authenticated"
            result = await self.tech_get(request_path=path, headers=self.headers)

        else:
            _LOGGER.error(f"The user {self.user_id} is not authenticated.")
            raise TechError(401, "Unauthorized")
        
        return result


    async def language_strings(self):
        """ Pull list of language strings
        """

        try:
            _LOGGER.debug(f"Pulling language strings ...")
            
            path = "api/v1/i18n/en"
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip'
            }
            result = await self.tech_get(request_path=path, headers=headers)
            if result:
                self.language_strings_dict = result["data"]
                return(result["data"])

        except Exception as e:
            _LOGGER.error(f"Pulling language strings failed. Error: {e}")
        
        return None
    

    async def list_modules(self):
        """ Pull list of modules
        """

        if self.authenticated:
            _LOGGER.debug(f"The user {self.user_id} authenticated, getting list of modules ...")
            
            path = "api/v1/users/" + self.user_id + "/modules"
            result = await self.tech_get(request_path=path, headers=self.headers)

        else:
            _LOGGER.error(f"Pulling list of modules failed. The user {self.user_id} is not authenticated")
            raise TechError(401, "Unauthorized")
        
        return result
    
    
    async def get_module_data(self, module_udid):
        """ Get module data.
        """

        _LOGGER.debug(f"Getting module {module_udid} data ...")

        if self.authenticated:
            path = "api/v1/users/" + self.user_id + "/modules/" + module_udid
            result = await self.tech_get(request_path=path, headers=self.headers)

        else:
            _LOGGER.error(f"Pulling module data failed. The user {self.user_id} is not authenticated")
            raise TechError(401, "Unauthorized")
        
        return result
    
    
    async def get_module_data_web(self, module_index):
        """ Get module data.
        """

        _LOGGER.debug(f"Getting module {module_index} data ...")

        if self.authenticated:
            path = "frontend/menu_main?module_index=0"
            result = await self.tech_get(request_path=path, headers=self.headers)

        else:
            _LOGGER.error(f"Pulling module data failed. The user {self.user_id} is not authenticated")
            raise TechError(401, "Unauthorized")
        
        return result
    
    
    async def get_module_zones(self, module_udid):
        """Returns Tech module zones either from cache or it will
        update all the cached values for Tech module assuming
        no update has occurred for at least the [update_interval].

        Parameters:
        inst (Tech): The instance of the Tech API.
        module_udid (string): The Tech module udid.

        Returns:
        Dictionary of zones indexed by zone ID.
        """
        async with self.update_lock:
            now = time.time()
            _LOGGER.debug("Geting module zones: now: %s, last_update %s, interval: %s", now, self.last_update, self.update_interval)
            if self.last_update is None or now > self.last_update + self.update_interval:
                _LOGGER.debug("Updating module zones cache..." + module_udid)    
                result = await self.get_module_data(module_udid)
                zones = result["zones"]["elements"]
                zones = list(filter(lambda e: e['zone']['zoneState'] != "zoneUnregistered", zones))
                for zone in zones:
                    self.zones[zone["zone"]["id"]] = zone
                self.last_update = now
        return self.zones
    

    async def get_module_tiles(self, module_udid):
        """Returns Tech module tiles either from cache or it will
        update all the cached values for Tech module assuming
        no update has occurred for at least the [update_interval].

        Parameters:
        inst (Tech): The instance of the Tech API.
        module_udid (string): The Tech module udid.

        Returns:
        Dictionary of tiles indexed by tiles ID.
        """

        async with self.update_lock:
            now = time.time()
            _LOGGER.debug("Geting module tiles: now: %s, last_update %s, interval: %s", now, self.last_update, self.update_interval)

            if self.last_update is None or now > self.last_update + self.update_interval:

                _LOGGER.debug(f"Updating module {module_udid} tiles cache ...")
                await self.language_strings()
                result = await self.get_module_data(module_udid)
                if self.language_strings_dict is None:
                    await self.language_strings()
                tiles = result["tiles"]

                temp_tiles = {}
                if tiles:
                    for tile in tiles:
 
                        # type = 6, Universal status with widgets
                        # type = 40, Text information
                        # type = 50, Controller software version
                        if tile["type"] == 6:
                            if (tile_params := tile["params"]) is not None:                            
                                data = []
                                for k,v in tile_params.items():
                                    if ("widget" in k) and v.get("txtId") != 0:
                                        t = [self.language_strings_dict.get(str(v.get("txtId")))]
                                        # Units:
                                        # - value type = 6: Degrees Celsius.
                                        # - value type = 7: Tenth degrees Celsius.
                                        # - value type = 18: Inscription from CN Description Base, or flame brightness in status history [0-8000]
                                        # - value type = 8: Percentages.
                                        if v.get("unit") == 7:
                                            t.append(v.get("value")/10)
                                        elif v.get("unit") == 18:
                                            t.append(self.language_strings_dict.get(str(v.get("value"))))
                                        else:
                                            t.append(v.get("value"))
                                        data.append(t)

                                temp_tiles[tile["id"]] = data

                        elif tile["type"] == 40:
                            if (tile_params := tile["params"]) is not None:   
                                temp_tiles[tile["id"]] = [
                                    self.language_strings_dict.get(str(tile_params.get("headerId"))),
                                    self.language_strings_dict.get(str(tile_params.get("statusId")))
                                ]
                        elif tile["type"] == 50:
                            if (tile_params := tile["params"]) is not None:   
                                temp_tiles[tile["id"]] = [
                                    self.language_strings_dict.get(str(tile_params.get("txtId"))),
                                    tile_params.get("controllerName"),
                                    tile_params.get("version")
                                ]

                _LOGGER.debug(f"Module {module_udid} tiles data: {temp_tiles}")    
                self.last_update = now
                self.tiles = temp_tiles

        return self.tiles
    
    
    async def get_zone(self, module_udid, zone_id):
        """Returns zone from Tech API cache.

        Parameters:
        module_udid (string): The Tech module udid.
        zone_id (int): The Tech module zone ID.

        Returns:
        Dictionary of zone.
        """
        await self.get_module_zones(module_udid)
        return self.zones[zone_id]
    
    
    async def set_const_temp(self, module_udid, selectedModuleIndex, target_temp):
        """Sets constant temperature.
        
        Parameters:
        module_udid (string): The Tech module udid.
        target_temp (float): The target temperature to be set within the zone.

        Returns:
        JSON object with the result.
        """
        result = None
        _LOGGER.debug("Setting constant temperature ...")
        if self.authenticated:
            path = "frontend/send_control_data"
            data = [{
                "ido":139,
                "params":int(target_temp  * 10),
                "module_index":selectedModuleIndex
            }]
            headers = self.headers
            headers = {
                "Referer": f"https://emodul.eu/web/{module_udid}/control",
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                'Authorization': f"Bearer {self.token}"
            }
            _LOGGER.debug(f"Setting constant temperature {target_temp}")
            try:
                #self.session.cookie_jar.clear()
                result = await self.tech_post(request_path=path, post_data=json.dumps(data), headers=headers)
                _LOGGER.debug(f"Setting constant temperature successed, results: {result}")
            except Exception as e:
                _LOGGER.error(f"Setting constant temperature failed. Error: {e}")
                raise TechError(401, "Unauthorized")
        else:
            raise TechError(401, "Unauthorized")
        
        return result
    
    
    async def set_preset_mode(self, module_udid, selectedModuleIndex, preset_mode):
        """Sets constant temperature.
        
        Parameters:
        module_udid (string): The Tech module udid.
        preset_mode (string): The target PRESENT mode to be set.

        Returns:
        JSON object with the result.
        """
        result = None
        _LOGGER.debug("Setting PRESENT mode ...")

        PRESENT_MODES_VALs = {
            "eco": 0,
            "comfort": 1,
            "protection": 2,
            "schedule1": 3,
            "schedule2": 4,
            "schedule3": 5,
            "schedule_weekly": 6
        }

        if self.authenticated:

            if preset_mode in PRESENT_MODES_VALs:

                path = "frontend/send_control_data"
                data = [{
                    "ido":100,
                    "params":PRESENT_MODES_VALs[preset_mode],
                    "module_index":selectedModuleIndex
                }]
                headers = self.headers
                headers = {
                    "Referer": f"https://emodul.eu/web/{module_udid}/control",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/plain, */*",
                    'Authorization': f"Bearer {self.token}"
                }
                _LOGGER.debug(f"Setting PRESENT mode {preset_mode}")
                try:
                    #self.session.cookie_jar.clear()
                    result = await self.tech_post(request_path=path, post_data=json.dumps(data), headers=headers)
                    _LOGGER.debug(f"Setting PRESENT mode successed, results: {result}")
                except Exception as e:
                    _LOGGER.error(f"Setting PRESENT mode failed. Error: {e}")
                    raise TechError(401, "Unauthorized")
        else:
            raise TechError(401, "Unauthorized")
        
        return result
    

    async def set_fan_mode(self, module_udid, selectedModuleIndex, fan_mode):
        """Sets constant temperature.
        
        Parameters:
        module_udid (string): The Tech module udid.
        fan_mode (string): The target FAN mode to be set.

        Returns:
        JSON object with the result.
        """
        result = None
        _LOGGER.debug("Setting Fan mode ...")

        if self.authenticated:

            path = "frontend/send_control_data"
            data = []
            FAN_MODE_SET = {
                "ido":140,
                "params":3,
                "module_index":selectedModuleIndex
            }
            FAN_SPEED_SET = {
                "ido":141,
                "params":0,
                "module_index":selectedModuleIndex
            }
            headers = self.headers
            headers = {
                "Referer": f"https://emodul.eu/web/{module_udid}/control",
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                'Authorization': f"Bearer {self.token}"
            }

            if fan_mode == "auto":
                FAN_MODE_SET["params"] = 3
                data.append(FAN_MODE_SET)
            elif fan_mode == "off":
                FAN_MODE_SET["params"] = 0
                data.append(FAN_MODE_SET)
            elif fan_mode == "low":
                FAN_MODE_SET["params"] = 1
                FAN_SPEED_SET["params"] = 0
                data.append(FAN_SPEED_SET)
                data.append(FAN_MODE_SET)
            elif fan_mode == "medium":
                FAN_MODE_SET["params"] = 1
                FAN_SPEED_SET["params"] = 1
                data.append(FAN_SPEED_SET)
                data.append(FAN_MODE_SET)
            elif fan_mode == "high":
                FAN_MODE_SET["params"] = 1
                FAN_SPEED_SET["params"] = 2
                data.append(FAN_SPEED_SET)
                data.append(FAN_MODE_SET)

            _LOGGER.debug(f"Setting FAN_MODE mode {fan_mode}")
            try:
                result = await self.tech_post(request_path=path, post_data=json.dumps(data), headers=headers)
                _LOGGER.debug(f"Setting FAN_MODE successed, results: {result}")
            except Exception as e:
                _LOGGER.error(f"Setting FAN_MODE mode failed. Error: {e}")
                raise TechError(401, "Unauthorized")
        else:
            raise TechError(401, "Unauthorized")
        
        return result


    async def set_zone(self, module_udid, zone_id, on = True):
        """Turns the zone on or off.
        
        Parameters:
        module_udid (string): The Tech module udid.
        zone_id (int): The Tech module zone ID.
        on (bool): Flag indicating to turn the zone on if True or off if False.

        Returns:
        JSON object with the result.
        """
        _LOGGER.debug("Turing zone on/off: %s", on)
        if self.authenticated:
            path = "users/" + self.user_id + "/modules/" + module_udid + "/zones"
            data = {
                "zone" : {
                    "id" : zone_id,
                    "zoneState" : "zoneOn" if on else "zoneOff"
                }
            }
            _LOGGER.debug(data)
            result = await self.post(path, json.dumps(data))
            _LOGGER.debug(result)
        else:
            raise TechError(401, "Unauthorized")
        return result


class TechError(Exception):
    """Raised when Tech APi request ended in error.
    Attributes:
        status_code - error code returned by Tech API
        status - more detailed description
    """
    def __init__(self, status_code, status):
        self.status_code = status_code
        self.status = status