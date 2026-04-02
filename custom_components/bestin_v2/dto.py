"""DTOs and type definitions for BESTIN Smart Home v2 API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
from enum import Enum


class FeatureType(str, Enum):
    LIGHT = "light"
    LIVING_LIGHT = "livinglight"
    DIMMING_LIGHT = "dimming_light"
    DIMMING_LIVING_LIGHT = "dimming_livinglight"
    THERMOSTAT = "thermostat"
    VENTIL = "ventil"
    GAS = "gas"
    ELECTRIC = "electric"


class DeviceState(str, Enum):
    ON = "on"
    OFF = "off"
    SET = "set"
    UNSET = "unset"
    CLOSE = "close"


@dataclass
class CommandPayload:
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
    address: str
    direction: str

    def to_dict(self) -> Dict[str, str]:
        return {"address": self.address, "direction": self.direction}


@dataclass
class LoginResult:
    success: bool
    data: Any = None

    @staticmethod
    def ok(data: Any) -> LoginResult:
        return LoginResult(success=True, data=data)

    @staticmethod
    def fail(reason: str = "unknown") -> LoginResult:
        return LoginResult(success=False, data=reason)


class BestinApiException(Exception):
    """NestJS HttpException style custom exception."""

    def __init__(self, message: str, status_code: int = 500, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)
