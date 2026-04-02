"""Data transfer objects and enums for BESTIN API."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class FeatureType(str, Enum):
    """디바이스 feature 식별자."""
    LIGHT = "light"
    LIVING_LIGHT = "livinglight"
    DIMMING_LIGHT = "dimming_light"
    DIMMING_LIVING_LIGHT = "dimming_livinglight"
    THERMOSTAT = "thermostat"
    VENTIL = "ventil"
    GAS = "gas"
    ELECTRIC = "electric"


class DeviceState(str, Enum):
    """디바이스 상태 값."""
    ON = "on"
    OFF = "off"
    SET = "set"
    UNSET = "unset"
    CLOSE = "close"


@dataclass
class CommandPayload:
    """디바이스 명령 요청 DTO."""
    unit: str
    state: str
    mode: str = ""
    unit_mode: str = ""

    def to_dict(self, include_mode: bool = False) -> Dict[str, str]:
        base = {"unit": self.unit, "state": self.state}
        if include_mode:
            base["mode"] = self.mode
            base["unit_mode"] = self.unit_mode
        return base


@dataclass
class ElevatorPayload:
    """엘리베이터 호출 요청 DTO."""
    address: str
    direction: str

    def to_dict(self) -> Dict[str, str]:
        return {"address": self.address, "direction": self.direction}


@dataclass
class LoginResult:
    """로그인 응답 DTO."""
    success: bool
    data: Any = None

    @staticmethod
    def ok(data: Any) -> LoginResult:
        return LoginResult(success=True, data=data)

    @staticmethod
    def fail(reason: str = "unknown") -> LoginResult:
        return LoginResult(success=False, data=reason)
