"""E2E 테스트 공용 fixture.

사용법:
  1. .env 파일 또는 환경 변수로 BESTIN_UUID 를 설정한다.
  2. pytest -s custom_components/bestin_v2/tests/ 로 실행한다.

필수 패키지: pip install pytest pytest-asyncio aiohttp
"""
from __future__ import annotations

import os

import aiohttp
import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def bestin_uuid() -> str:
    """BESTIN_UUID 환경 변수에서 UUID를 읽는다."""
    uuid = os.environ.get("BESTIN_UUID", "")
    if not uuid:
        pytest.skip("BESTIN_UUID 환경 변수가 설정되지 않았습니다.")
    return uuid


@pytest_asyncio.fixture
async def http_session() -> aiohttp.ClientSession:
    """aiohttp 세션을 생성하고 테스트 후 정리한다."""
    async with aiohttp.ClientSession() as session:
        yield session
