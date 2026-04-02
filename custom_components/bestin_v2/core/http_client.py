"""BESTIN API HTTP 클라이언트 (HA aiohttp 세션 기반)."""
from __future__ import annotations

from typing import Any, Callable, Dict

from ..const import ACCESS_TOKEN, LOGIN_BODY, TIMEOUT_SEC
from .token_store import TokenStore

USER_AGENT = (
    "mozilla/5.0 (windows nt 10.0; win64; x64) "
    "applewebkit/537.36 (khtml, like gecko) "
    "chrome/78.0.3904.70 safari/537.36"
)


class BestinHttpClient:
    """인증 전략별 HTTP 메서드를 제공하는 클라이언트.

    Auth strategies:
      - Token: access-token 헤더 (get/put)
      - API Key: X-API-KEY 헤더 (login)
      - UUID: Authorization 헤더 (valley/elevator)
    """

    def __init__(
        self,
        session_factory: Callable[[], Any],
        token_store: TokenStore,
    ):
        self._session_factory = session_factory
        self._token_store = token_store

    @property
    def _session(self) -> Any:
        return self._session_factory()

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
        """API-key authenticated POST (login) — Legacy mode."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }
        return await self._session.post(
            url, headers=headers, timeout=TIMEOUT_SEC,
        )

    async def post_with_dual_auth(
        self, url: str, auth_token: str, api_key: str,
    ) -> Any:
        """Authorization + X-API-KEY dual-header POST (login)."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "Authorization": auth_token,
            "X-API-KEY": api_key,
        }
        return await self._session.post(
            url, headers=headers, data=LOGIN_BODY, timeout=TIMEOUT_SEC,
        )

    async def get_with_auth(self, url: str, auth_token: str) -> Any:
        """Authorization-header GET (valley)."""
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
        """Authorization-header POST (elevator)."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "Authorization": auth_token,
        }
        return await self._session.post(
            url, headers=headers, json=data, timeout=TIMEOUT_SEC,
        )
