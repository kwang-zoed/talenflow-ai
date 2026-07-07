"""距离计算工具（不依赖外部 API）。"""
import math
import re
from typing import Optional


REMOTE_KEYWORDS = ("远程", "不限", "remote", "居家", "全国")


def is_remote_location(text: Optional[str]) -> bool:
    if not text:
        return False
    lowered = str(text).strip().lower()
    return any(kw in lowered for kw in REMOTE_KEYWORDS)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def format_distance(km: Optional[float]) -> str:
    if km is None:
        return "距离未知"
    if km < 3:
        return "同城"
    if km < 1:
        return "约 1km"
    if km >= 500:
        return f"约 {int(round(km))}km"
    return f"约 {int(round(km))}km"


def extract_city_label(city_text: Optional[str]) -> Optional[str]:
    if not city_text:
        return None
    parts = [p.strip() for p in re.split(r"[/\-]", str(city_text)) if p.strip()]
    return parts[-1] if parts else str(city_text).strip()
