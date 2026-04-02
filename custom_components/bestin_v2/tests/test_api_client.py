"""BESTIN API 클라이언트 E2E 테스트.

Home Assistant 없이 API 서버와 직접 통신하여 로그인,
feature 조회, 상태 조회 등을 검증한다.

실행 방법:
  BESTIN_UUID=<your-uuid> pytest -s custom_components/bestin_v2/tests/

필수 패키지: pip install pytest pytest-asyncio aiohttp
"""
from __future__ import annotations

import json
import logging
import sys
import os
from typing import Any, Dict, Optional

import aiohttp
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
)

from bestin_v2.core.http_client import USER_AGENT
from bestin_v2.core.parsers import parse_units, parse_features

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://center.hdc-smart.com/v3/auth/login"
TIMEOUT = aiohttp.ClientTimeout(total=30)


class StandaloneApiClient:
    """HA 의존성 없이 BESTIN API를 직접 호출하는 경량 클라이언트.

    개발·디버깅 시 독립적으로 API 동작을 확인할 수 있다.
    """

    def __init__(self, session: aiohttp.ClientSession, uuid: str):
        self._session = session
        self._uuid = uuid
        self._base_url: Optional[str] = None
        self._access_token: Optional[str] = None

    def _base_headers(self) -> Dict[str, str]:
        return {"User-Agent": USER_AGENT}

    def _authed_headers(self) -> Dict[str, str]:
        headers = self._base_headers()
        if self._access_token:
            headers["access-token"] = self._access_token
        return headers

    async def login(self) -> Dict[str, Any]:
        """로그인 후 access-token 과 base_url 을 설정한다."""
        headers = {
            **self._base_headers(),
            "Content-Type": "application/json",
            "X-API-KEY": self._uuid,
        }
        async with self._session.post(
            LOGIN_URL, headers=headers, timeout=TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"로그인 실패: HTTP {resp.status}"
            data = await resp.json()

        self._access_token = data.get("access-token")
        self._base_url = data.get("url")

        _LOGGER.info("로그인 성공 - url=%s", self._base_url)
        return data

    async def get_features(self) -> Dict[str, int]:
        """적용 가능한 feature 목록을 조회한다."""
        assert self._base_url, "login() 을 먼저 호출하세요."
        url = f"{self._base_url}/v2/api/features/apply"

        async with self._session.get(
            url, headers=self._authed_headers(), timeout=TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"feature 조회 실패: HTTP {resp.status}"
            data = await resp.json()

        features = parse_features(data)
        _LOGGER.info("features: %s", features)
        return features

    async def get_state(
        self, feature: str, room: str = "1",
    ) -> Dict[str, str]:
        """특정 feature/room 의 상태를 조회한다."""
        assert self._base_url, "login() 을 먼저 호출하세요."
        url = f"{self._base_url}/v2/api/features/{feature}/{room}/apply"

        async with self._session.get(
            url, headers=self._authed_headers(), timeout=TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"상태 조회 실패: HTTP {resp.status}"
            data = await resp.json()

        units = parse_units(data)
        _LOGGER.info("state(%s, %s): %s", feature, room, units)
        return units

    async def get_site_info(self) -> Dict[str, Any]:
        """사이트 정보를 조회한다."""
        assert self._base_url, "login() 을 먼저 호출하세요."
        url = f"{self._base_url}/v2/api/refs/site"

        async with self._session.get(
            url, headers=self._authed_headers(), timeout=TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"사이트 정보 조회 실패: HTTP {resp.status}"
            return await resp.json()

    async def get_energy(self) -> Any:
        """에너지 사용량을 조회한다."""
        assert self._base_url, "login() 을 먼저 호출하세요."
        url = f"{self._base_url}/v2/api/meter/daily/energies?skip=0&limit=1"

        async with self._session.get(
            url, headers=self._authed_headers(), timeout=TIMEOUT,
        ) as resp:
            assert resp.status == 200, f"에너지 조회 실패: HTTP {resp.status}"
            return await resp.json()


# ── Test Cases ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login(http_session: aiohttp.ClientSession, bestin_uuid: str):
    """로그인이 정상 동작하고 access-token 과 url 이 반환되는지 확인."""
    client = StandaloneApiClient(http_session, bestin_uuid)
    data = await client.login()

    assert "access-token" in data, "응답에 access-token 이 없습니다."
    assert "url" in data, "응답에 url 이 없습니다."
    assert data["url"].startswith("http"), f"url 형식 이상: {data['url']}"

    _LOGGER.info("test_login PASSED - token=%s...", data["access-token"][:20])


@pytest.mark.asyncio
async def test_get_features(
    http_session: aiohttp.ClientSession, bestin_uuid: str,
):
    """로그인 후 feature 목록을 조회할 수 있는지 확인."""
    client = StandaloneApiClient(http_session, bestin_uuid)
    await client.login()

    features = await client.get_features()

    assert isinstance(features, dict), "features 는 dict 여야 합니다."
    assert len(features) > 0, "feature 가 하나도 없습니다."

    _LOGGER.info("test_get_features PASSED - %d features", len(features))


@pytest.mark.asyncio
async def test_get_site_info(
    http_session: aiohttp.ClientSession, bestin_uuid: str,
):
    """사이트 정보를 정상 조회할 수 있는지 확인."""
    client = StandaloneApiClient(http_session, bestin_uuid)
    await client.login()

    info = await client.get_site_info()

    assert isinstance(info, dict), "site_info 는 dict 여야 합니다."

    _LOGGER.info("test_get_site_info PASSED - %s", json.dumps(info, ensure_ascii=False)[:200])


@pytest.mark.asyncio
async def test_get_energy(
    http_session: aiohttp.ClientSession, bestin_uuid: str,
):
    """에너지 사용량 조회가 정상 동작하는지 확인."""
    client = StandaloneApiClient(http_session, bestin_uuid)
    await client.login()

    energy = await client.get_energy()

    assert energy is not None, "에너지 데이터가 None 입니다."

    _LOGGER.info("test_get_energy PASSED - %s", json.dumps(energy, ensure_ascii=False)[:200])


@pytest.mark.asyncio
async def test_thermostat_state(
    http_session: aiohttp.ClientSession, bestin_uuid: str,
):
    """온도조절기 상태 조회 e2e (feature 에 thermostat 이 있는 경우만)."""
    client = StandaloneApiClient(http_session, bestin_uuid)
    await client.login()

    features = await client.get_features()
    if "thermostat" not in features:
        pytest.skip("thermostat feature 가 없습니다.")

    state = await client.get_state("thermostat")

    assert isinstance(state, dict), "thermostat state 는 dict 여야 합니다."

    _LOGGER.info("test_thermostat_state PASSED - %s", state)


@pytest.mark.asyncio
async def test_light_state(
    http_session: aiohttp.ClientSession, bestin_uuid: str,
):
    """조명 상태 조회 e2e (feature 에 light 가 있는 경우만)."""
    client = StandaloneApiClient(http_session, bestin_uuid)
    await client.login()

    features = await client.get_features()
    if "light" not in features:
        pytest.skip("light feature 가 없습니다.")

    state = await client.get_state("light", "1")

    assert isinstance(state, dict), "light state 는 dict 여야 합니다."

    _LOGGER.info("test_light_state PASSED - %s", state)
