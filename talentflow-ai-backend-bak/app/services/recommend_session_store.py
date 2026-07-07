import json
import logging
import time
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SESSION_KEY_PREFIX = "hr:recommend:session:"
SESSION_TTL_SECONDS = 3600

# Redis 不可用时的进程内兜底（单 worker 开发环境）
_memory_store: Dict[str, Dict[str, Any]] = {}


def _redis_client():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=3)


def _save_memory(session_id: str, data: Dict[str, Any]) -> None:
    _memory_store[session_id] = {
        **data,
        "_expires_at": time.time() + SESSION_TTL_SECONDS,
    }


def _load_memory(session_id: str) -> Optional[Dict[str, Any]]:
    entry = _memory_store.get(session_id)
    if not entry:
        return None
    if entry.get("_expires_at", 0) < time.time():
        _memory_store.pop(session_id, None)
        return None
    return {k: v for k, v in entry.items() if k != "_expires_at"}


def save_recommend_session(session_id: str, data: Dict[str, Any]) -> None:
    _save_memory(session_id, data)
    try:
        client = _redis_client()
        client.setex(
            SESSION_KEY_PREFIX + session_id,
            SESSION_TTL_SECONDS,
            json.dumps(data, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning("Redis 写入推荐会话失败，已使用进程内存 session_id=%s: %s", session_id, e)


def load_recommend_session(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        client = _redis_client()
        key = SESSION_KEY_PREFIX + session_id
        raw = client.get(key)
        if raw:
            client.expire(key, SESSION_TTL_SECONDS)
            return json.loads(raw)
    except Exception as e:
        logger.warning("Redis 读取推荐会话失败 session_id=%s: %s", session_id, e)
    return _load_memory(session_id)


def patch_recommend_session(session_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session = load_recommend_session(session_id)
    if not session:
        return None
    session.update(patch)
    save_recommend_session(session_id, session)
    return session
