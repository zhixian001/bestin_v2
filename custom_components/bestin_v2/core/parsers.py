"""API 응답 파서 유틸리티."""
from __future__ import annotations

from typing import Any, Dict, List


def ensure_list(value: Any) -> List[Any]:
    """값을 리스트로 정규화한다. None/빈값 → [], 단일값 → [값]."""
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def parse_units(response: Dict[str, Any]) -> Dict[str, str]:
    """API 응답에서 unit → state 매핑을 추출한다."""
    units = response.get("units")
    if not units:
        return {}
    return {u["unit"]: u["state"] for u in units}


def parse_features(response: Dict[str, Any]) -> Dict[str, int]:
    """API 응답에서 활성 feature → quantity 매핑을 추출한다."""
    return {
        ft["name"]: ft["quantity"]
        for ft in response.get("features", [])
        if ft["quantity"] > 0
    }
