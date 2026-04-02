"""Custom exceptions for BESTIN API."""
from __future__ import annotations

from typing import Any


class BestinApiException(Exception):
    """API 호출 실패 시 발생하는 예외."""

    def __init__(self, message: str, status_code: int = 500, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)
