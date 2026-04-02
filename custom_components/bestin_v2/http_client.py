"""HTTP client and token storage for BESTIN API (NestJS HttpService pattern)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, BESTIN_TOKEN, ACCESS_TOKEN, TIMEOUT_SEC

_LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "mozilla/5.0 (windows nt 10.0; win64; x64) "
    "applewebkit/537.36 (khtml, like gecko) "
    "chrome/78.0.3904.70 safari/537.36"
)


class TokenStore:
    """Token persistence layer (Repository pattern)."""

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


class BestinHttpClient:
    """Centralized HTTP client (NestJS HttpService pattern).

    Auth strategies:
      - Token auth: access-token header from TokenStore (get/put)
      - API key auth: X-API-KEY header (login)
      - UUID auth: Authorization header (valley/elevator)
    """

    def __init__(self, hass: HomeAssistant, token_store: TokenStore):
        self._hass = hass
        self._token_store = token_store

    @property
    def _session(self):
        return async_get_clientsession(self._hass)

    def _base_headers(self) -> Dict[str, str]:
        return {"User-Agent": USER_AGENT}

    def _token_headers(self) -> Dict[str, str]:
        headers = self._base_headers()
        token_data = self._token_store.read()
        if ACCESS_TOKEN in token_data:
            headers[ACCESS_TOKEN] = token_data[ACCESS_TOKEN]
        return headers

    async def get(self, url: str) -> Any:
        """Token-authenticated GET."""
        return await self._session.get(
            url, headers=self._token_headers(), timeout=TIMEOUT_SEC,
        )

    async def put(self, url: str, data: Dict[str, Any]) -> Any:
        """Token-authenticated PUT."""
        headers = {**self._token_headers(), "Content-Type": "application/json"}
        return await self._session.put(
            url, headers=headers, json=data, timeout=TIMEOUT_SEC,
        )

    async def post_with_api_key(self, url: str, api_key: str) -> Any:
        """API-key authenticated POST (for login)."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }
        return await self._session.post(
            url, headers=headers, timeout=TIMEOUT_SEC,
        )

    async def get_with_auth(self, url: str, auth_token: str) -> Any:
        """Authorization-header GET (for valley)."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "Authorization": auth_token,
        }
        return await self._session.get(
            url, headers=headers, timeout=TIMEOUT_SEC,
        )

    async def post_with_auth(
        self, url: str, auth_token: str, data: Dict[str, Any],
    ) -> Any:
        """Authorization-header POST (for elevator)."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "Authorization": auth_token,
        }
        return await self._session.post(
            url, headers=headers, json=data, timeout=TIMEOUT_SEC,
        )
