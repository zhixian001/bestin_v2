"""BESTIN Smart Home v2 API Services.

Architecture:
  - BestinApiService: Core API (NestJS Service pattern)
  - RoomService: Per-room device control
  - ThermostatService: Climate control
  - login(): Standalone auth for config_flow
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN, CONF_URL, CONF_UUID, CONF_ROOMS, CONF_DEVICES,
    _ROOMS, BESTIN_TOKEN,
    _LOGIN_URL, _FEATURES_URL, _VALLEY_URL, _CTRL_URL,
    _ENERGY_URL, _ELEV_URL, _SITE_INFO_URL,
)
from .dto import (
    FeatureType, DeviceState, CommandPayload, ElevatorPayload,
    LoginResult, BestinApiException,
)
from .http_client import BestinHttpClient, TokenStore, USER_AGENT

_LOGGER = logging.getLogger(__name__)


# ── Utility Functions ──────────────────────────────────────────────

def ensure_list(value: Any) -> List[Any]:
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def parse_units(response: Dict[str, Any]) -> Dict[str, str]:
    units = response.get("units")
    if not units:
        return {}
    return {u["unit"]: u["state"] for u in units}


def parse_features(response: Dict[str, Any]) -> Dict[str, int]:
    return {
        ft["name"]: ft["quantity"]
        for ft in response.get("features", [])
        if ft["quantity"] > 0
    }


# ── Standalone Login (config_flow 호환) ────────────────────────────

async def login(session: Any, uuid: str) -> Any:
    from .const import TIMEOUT_SEC

    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": uuid,
        "User-Agent": USER_AGENT,
    }

    try:
        response = await session.post(_LOGIN_URL, headers=headers, timeout=TIMEOUT_SEC)
    except Exception as ex:
        _LOGGER.error("[%s] login() exception: %s", DOMAIN, ex)
        raise BestinApiException("Login network error", detail=ex) from ex

    if response.status == 200:
        _LOGGER.debug("[%s] login() success", DOMAIN)
    elif response.status == 500:
        res_json = await response.json()
        _LOGGER.error("[%s] login() failed(500): %s", DOMAIN, res_json.get("err"))
    else:
        _LOGGER.error("[%s] login() failed(%d)", DOMAIN, response.status)

    return response


# ── BestinApiService ───────────────────────────────────────────────

class BestinApiService:
    """Core API service for BESTIN Smart Home v2."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass
        self._entry = entry

        self.url: str = entry.data[CONF_URL]
        self.uuid: str = entry.data[CONF_UUID]
        self.rooms: List[str] = entry.data[CONF_ROOMS]
        self.devices: List[str] = entry.data[CONF_DEVICES]

        self.token_store = TokenStore()
        self.http = BestinHttpClient(hass, self.token_store)

        self.gas: Dict[str, str] = {}
        self.fan: Dict[str, str] = {}
        self.features: Dict[str, int] = {}
        self.debug: bool = False

    # ── Auth ───────────────────────────────────────────────────────

    def is_token_available(self) -> bool:
        if not self.token_store.exists():
            _LOGGER.error("[%s] Token file not found: %s", DOMAIN, BESTIN_TOKEN)
            return False
        return True

    def get_login_info(self) -> Dict[str, Any]:
        return self.token_store.read()

    async def do_login(self) -> LoginResult:
        try:
            response = await self.http.post_with_api_key(_LOGIN_URL, self.uuid)
        except Exception as ex:
            _LOGGER.error("[%s] do_login() exception: %s", DOMAIN, ex)
            return LoginResult.fail("network fail")

        if response.status == 200:
            data = await response.json()
            self.token_store.save(data)
            if self.debug:
                _LOGGER.debug("[%s] do_login() success: %s", DOMAIN, data)
            return LoginResult.ok(data)

        if response.status == 500:
            error = await response.json()
            _LOGGER.error("[%s] do_login() failed(500): %s", DOMAIN, error.get("err"))
            return LoginResult.fail("server error")

        error = await response.json()
        _LOGGER.error("[%s] do_login() failed(%d): %s", DOMAIN, response.status, error)
        return LoginResult.fail("login failed")

    # ── Debug ──────────────────────────────────────────────────────

    def set_debug(self, enabled: bool) -> None:
        self.debug = enabled

    # ── Feature / Site Info ────────────────────────────────────────

    async def get_features(self) -> Dict[str, Any]:
        url = f"{self.url}{_FEATURES_URL}"
        res = await self.http.get(url)

        if res.status == 500:
            text = await res.text()
            _LOGGER.error("[%s] get_features() error(500): %s", DOMAIN, text)

        data = await res.json()
        if self.debug:
            _LOGGER.debug("[%s] get_features(): %s", DOMAIN, data)

        self.features = parse_features(data)
        return data

    async def get_site_info(self) -> Dict[str, Any]:
        url = f"{self.url}{_SITE_INFO_URL}"
        res = await self.http.get(url)

        if res.status == 500:
            text = await res.text()
            _LOGGER.error("[%s] get_site_info() error(500): %s", DOMAIN, text)

        data = await res.json()
        if self.debug:
            _LOGGER.debug("[%s] get_site_info(): %s", DOMAIN, data)
        return data

    # ── Valley ─────────────────────────────────────────────────────

    async def get_valley(self) -> Dict[str, Any]:
        try:
            res = await self.http.get_with_auth(_VALLEY_URL, self.uuid)
        except Exception as ex:
            _LOGGER.error("[%s] get_valley() exception: %s", DOMAIN, ex)
            raise BestinApiException("Valley request failed", detail=ex) from ex

        if res.status == 500:
            text = await res.text()
            _LOGGER.error("[%s] get_valley() error(500): %s", DOMAIN, text)

        data = await res.json()
        if self.debug:
            _LOGGER.debug("[%s] get_valley(): %s", DOMAIN, data)
        return data

    # ── State ──────────────────────────────────────────────────────

    async def get_state(self, feature: str, room: str = "1") -> Dict[str, str]:
        uri = _CTRL_URL.format(feature, room)
        url = f"{self.url}{uri}"

        res = await self.http.get(url)

        if res.status == 500:
            text = await res.text()
            _LOGGER.error("[%s] get_state(%s, %s) error(500): %s", DOMAIN, feature, room, text)

        data = await res.json()
        if self.debug:
            _LOGGER.debug("[%s] get_state(%s, %s): %s", DOMAIN, feature, room, data)

        return parse_units(data)

    # ── Command ────────────────────────────────────────────────────

    async def send_command(
        self, feature: str, unit: str, state: str, room: str = "1",
    ) -> None:
        uri = _CTRL_URL.format(feature, room)
        url = f"{self.url}{uri}"

        payload = CommandPayload(unit=unit, state=state)
        is_ventil = (feature == FeatureType.VENTIL)
        data = payload.to_dict(include_mode=is_ventil)

        res = await self.http.put(url, data)

        if self.debug:
            _LOGGER.debug(
                "[%s] send_command(%s, %s, %s, %s): %s",
                DOMAIN, feature, room, unit, state, await res.read(),
            )

    # ── Climate ────────────────────────────────────────────────────

    async def set_hvac_mode(self, room: str, action: str, temp: str) -> None:
        await self.send_command("thermostat", room, f"{action}/{temp}")

    async def set_hvac_temperature(
        self, room: str, action: str, temp: str, cur_temp: str,
    ) -> None:
        await self.send_command("thermostat", room, f"{action}/{temp}/{cur_temp}")

    # ── Light ──────────────────────────────────────────────────────

    async def light_on_off(self, room: str, unit: str, state: str) -> None:
        if room == "l":
            await self.send_command("livinglight", unit, state)
        else:
            await self.send_command("light", unit, state, room)

    async def light_all_off(self, room: str) -> None:
        if room == "l":
            await self.send_command("livinglight", "all", DeviceState.OFF)
        else:
            await self.send_command("light", "all", DeviceState.OFF, room)

    # ── Outlet ─────────────────────────────────────────────────────

    async def outlet_on_off(self, room: str, unit: str, state: str) -> None:
        await self.send_command("electric", unit, state, room)

    # ── Ventilator ─────────────────────────────────────────────────

    async def get_ventil_state(self) -> Dict[str, str]:
        state = await self.get_state("ventil")
        self.fan = state
        if self.debug:
            _LOGGER.debug("[%s] get_ventil_state(): %s", DOMAIN, state)
        return state

    async def ventil_on_off(self, unit: str, state: str) -> None:
        await self.send_command("ventil", unit, state)

    # ── Gas ────────────────────────────────────────────────────────

    async def get_gas_state(self) -> Dict[str, str]:
        state = await self.get_state("gas")
        self.gas = state
        if self.debug:
            _LOGGER.debug("[%s] get_gas_state(): %s", DOMAIN, state)
        return state

    async def gas_lock(self) -> None:
        await self.send_command("gas", "gas1", DeviceState.CLOSE)
        await self.get_gas_state()

    # ── Energy ─────────────────────────────────────────────────────

    async def get_energy(self) -> Dict[str, Any]:
        url = f"{self.url}{_ENERGY_URL}"
        res = await self.http.get(url)
        text = await res.text()

        if self.debug:
            _LOGGER.debug("[%s] get_energy(): %s", DOMAIN, json.loads(text))

        return json.loads(text)

    # ── Elevator ───────────────────────────────────────────────────

    async def call_elevator(self, address: str, direction: str) -> None:
        url = f"{self.url}{_ELEV_URL}"
        payload = ElevatorPayload(address=address, direction=direction)
        res = await self.http.post_with_auth(url, self.uuid, payload.to_dict())

        if res.status == 500:
            error = await res.json()
            _LOGGER.error("[%s] call_elevator() failed(500): %s", DOMAIN, error.get("err"))


# Backward compatibility alias
BestinAPIv2 = BestinApiService


# ── RoomService ────────────────────────────────────────────────────

class RoomService:
    """Per-room device state & control service."""

    def __init__(self, room: str, api: BestinApiService):
        self.room = room
        self.room_desc: str = _ROOMS[room]
        self._api = api

        self.lights: Dict[str, str] = {}
        self.outlets: Dict[str, str] = {}

    # ── Light ──────────────────────────────────────────────────────

    async def fetch_light_state(self) -> None:
        feature = "livinglight" if self.room == "l" else "light"
        room_param = "1" if self.room == "l" else self.room
        self.lights = await self._api.get_state(feature, room_param)

    async def fetch_dimming_light_state(self) -> None:
        feature = "dimming_livinglight" if self.room == "l" else "dimming_light"
        room_param = "1" if self.room == "l" else self.room
        self.lights = await self._api.get_state(feature, room_param)

    async def light_on(self, switch: str) -> None:
        await self._api.light_on_off(self.room, switch, DeviceState.ON)

    async def light_off(self, switch: str) -> None:
        await self._api.light_on_off(self.room, switch, DeviceState.OFF)

    def is_light_on(self, switch: str) -> str:
        return self.lights[switch]

    # ── Outlet ─────────────────────────────────────────────────────

    async def fetch_outlet_state(self) -> None:
        self.outlets = await self._api.get_state("electric", self.room)

    async def outlet_on(self, switch: str) -> None:
        await self._api.outlet_on_off(self.room, switch, DeviceState.ON)

    async def outlet_off(self, switch: str) -> None:
        await self._api.outlet_on_off(self.room, switch, DeviceState.OFF)

    async def outlet_set(self, switch: str) -> None:
        await self._api.outlet_on_off(self.room, switch, DeviceState.SET)

    async def outlet_unset(self, switch: str) -> None:
        await self._api.outlet_on_off(self.room, switch, DeviceState.UNSET)

    def is_outlet_on(self, switch: str) -> str:
        return self.outlets[switch]


# Backward compatibility alias
BestinRoom = RoomService


# ── ThermostatService ──────────────────────────────────────────────

class ThermostatService:
    """Thermostat state & control service."""

    def __init__(self, api: BestinApiService):
        self._api = api
        self.thermostats: Dict[str, str] = {}

    def _parse_field(self, room: str, index: int) -> str:
        return self.thermostats[room].split("/")[index]

    async def fetch_state(self) -> None:
        self.thermostats = await self._api.get_state("thermostat")

    async def set_hvac_mode(self, room: str, action: str, target_temp: str) -> None:
        await self._api.set_hvac_mode(room, action, target_temp)

    async def set_hvac_temperature(
        self, room: str, action: str, target_temp: str, cur_temp: str,
    ) -> None:
        await self._api.set_hvac_temperature(room, action, target_temp, cur_temp)

    def is_on(self, room: str) -> str:
        return self._parse_field(room, 0)

    def get_target_temp(self, room: str) -> str:
        return self._parse_field(room, 1)

    def get_current_temp(self, room: str) -> str:
        return self._parse_field(room, 2)


# Backward compatibility alias
BestinThermostat = ThermostatService
