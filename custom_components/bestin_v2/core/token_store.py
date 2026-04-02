"""토큰 영속화 저장소 (Repository 패턴)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from ..const import DOMAIN, BESTIN_TOKEN

_LOGGER = logging.getLogger(__name__)


class TokenStore:
    """bestin_token.json 파일 기반 토큰 관리."""

    def __init__(self, path: str = BESTIN_TOKEN):
        self._path = path

    def exists(self) -> bool:
        return os.path.isfile(self._path)

    def read(self) -> Dict[str, Any]:
        try:
            with open(self._path, "r") as f:
                return json.load(f)
        except Exception as ex:
            _LOGGER.error(
                "[%s] TokenStore.read() - %s 읽기 실패: %s",
                DOMAIN, self._path, ex,
            )
            return {}

    def save(self, data: Dict[str, Any]) -> bool:
        try:
            with open(self._path, "w") as f:
                json.dump(data, f, sort_keys=True, indent=1)
            return True
        except Exception:
            return False
