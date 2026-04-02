"""온도조절기(Thermostat) 제어 서비스."""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .api_service import BestinApiService


class ThermostatService:
    """전체 방의 온도조절기 상태 조회 및 제어를 담당한다."""

    def __init__(self, api: BestinApiService):
        self._api = api
        self.thermostats: Dict[str, str] = {}

    def _parse_field(self, room: str, index: int) -> str:
        return self.thermostats[room].split("/")[index]

    async def fetch_state(self) -> None:
        self.thermostats = await self._api.get_state("thermostat")

    async def set_hvac_mode(
        self, room: str, action: str, target_temp: str,
    ) -> None:
        await self._api.set_hvac_mode(room, action, target_temp)

    async def set_hvac_temperature(
        self, room: str, action: str, target_temp: str, cur_temp: str,
    ) -> None:
        await self._api.set_hvac_temperature(
            room, action, target_temp, cur_temp,
        )

    def is_on(self, room: str) -> str:
        return self._parse_field(room, 0)

    def get_target_temp(self, room: str) -> str:
        return self._parse_field(room, 1)

    def get_current_temp(self, room: str) -> str:
        return self._parse_field(room, 2)
