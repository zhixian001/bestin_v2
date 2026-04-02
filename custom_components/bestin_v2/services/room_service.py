"""방(Room) 단위 디바이스 제어 서비스."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from ..const import _ROOMS
from ..core import DeviceState

if TYPE_CHECKING:
    from .api_service import BestinApiService


class RoomService:
    """특정 방의 조명·콘센트 상태 조회 및 제어를 담당한다."""

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
