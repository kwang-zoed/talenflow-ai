"""高德地理编码服务。"""
import hashlib
import logging
from typing import Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
_memory_cache: dict[str, Tuple[float, float]] = {}


def build_geocode_query(city: Optional[str], address: Optional[str]) -> str:
    parts = []
    if city:
        parts.append(str(city).strip().replace("/", ""))
    if address:
        parts.append(str(address).strip())
    return "".join(parts)


def _cache_key(query: str) -> str:
    return hashlib.md5(query.encode("utf-8")).hexdigest()


def geocode(city: Optional[str], address: Optional[str] = None) -> Optional[Tuple[float, float]]:
    query = build_geocode_query(city, address)
    if not query:
        return None

    key = _cache_key(query)
    if key in _memory_cache:
        return _memory_cache[key]

    if not settings.AMAP_GEOCODE_ENABLED or not settings.AMAP_WEB_KEY:
        logger.debug("地理编码已禁用或未配置 AMAP_WEB_KEY: %s", query)
        return None

    try:
        resp = httpx.get(
            _GEOCODE_URL,
            params={"key": settings.AMAP_WEB_KEY, "address": query},
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if str(data.get("status")) != "1":
            logger.warning("高德地理编码失败 query=%s info=%s", query, data.get("info"))
            return None
        geocodes = data.get("geocodes") or []
        if not geocodes:
            return None
        location = geocodes[0].get("location") or ""
        if "," not in location:
            return None
        lng_str, lat_str = location.split(",", 1)
        coords = (float(lat_str), float(lng_str))
        _memory_cache[key] = coords
        return coords
    except Exception as exc:
        logger.warning("地理编码异常 query=%s err=%s", query, exc)
        return None
