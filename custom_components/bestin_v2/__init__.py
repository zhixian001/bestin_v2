""" Bestin v2 """
import logging
import asyncio
import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant

from datetime import timedelta
from datetime import datetime
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_SCAN_INTERVAL, CONF_PASSWORD)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

from .const import DOMAIN, CONF_URL, CONF_UUID, CONF_ROOMS, DT_LIGHT, DT_OUTLET, DT_CLIMATE, DT_FAN, DT_GAS, DT_ENERGY
from .services import BestinApiService as API
from .services import RoomService
from .services import ThermostatService

PLATFORMS = ['sensor', 'light', 'climate', 'switch', 'fan', 'button']

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema({vol.Required(CONF_URL): cv.string}),
            vol.Schema({vol.Required(CONF_UUID): cv.string}),
            vol.Schema({vol.Required(CONF_ROOMS): cv.string}),
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up local_ip from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {"api":{}, "room":{}, "thermostat": {}})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up bestin  from a config entry."""
    #api
    hass.data.setdefault(DOMAIN, {"api": {}, "room": {}, "thermostat": {}})

    api = API(hass, entry)

    if not api.is_token_available():
        _LOGGER.error(f'[{DOMAIN}] bestin_token.json is not exist.')
        await api.do_login()

    await api.do_login()

    hass.data[DOMAIN]["api"][entry.entry_id] = api

    try:
        await api.get_features()
    except Exception as ex:
        _LOGGER.error(f'[{DOMAIN}] api.get_features() Exception. -> %s', ex)

    #rooms
    room_info = {}

    for room in api.rooms:
        r = RoomService(room, api)

        if DT_LIGHT in api.devices:
            await r.fetch_light_state()

        if DT_OUTLET in api.devices:
            if room != 'l':
                await r.fetch_outlet_state()

        room_info[room] = r

    hass.data[DOMAIN]["room"][entry.entry_id] = room_info

    if DT_CLIMATE in api.devices:
        thermostat = ThermostatService(api)

        await thermostat.fetch_state()

        hass.data[DOMAIN]['thermostat'][entry.entry_id] = thermostat

    #async create task
    # MULTI
    # default sensor : login + sync
    platforms = ['sensor', 'switch']

    if DT_LIGHT in api.devices:
        platforms += ['light']

    if DT_CLIMATE in api.devices:
        platforms += ['climate']

    if DT_FAN in api.devices:
        platforms += ['fan']

    if DT_LIGHT in api.devices or DT_GAS in api.devices:
        platforms += ['button']

    # async forward entry setups
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # light room all off serivce
    async def room_light_all_off(service):
        room = service.data["room"]

        await api.light_all_off(room)

    hass.services.async_register(DOMAIN, "room_light_all_off", room_light_all_off)

    # elevator
    async def call_elevator(service):
        addr = service.data["address"]
        dir  = service.data["direction"]

        await api.call_elevator(addr, dir)

    hass.services.async_register(DOMAIN, "call_elevator", call_elevator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    #api
    api = hass.data[DOMAIN]["api"][config_entry.entry_id]

#    return await hass.config_entries.async_forward_entry_unload(entry, PLATFORM)
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    return unload_ok
