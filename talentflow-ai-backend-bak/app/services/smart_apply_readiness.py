"""智能投递依赖就绪检查（本地 / Docker 排障用）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def _check_redis() -> Tuple[bool, str]:
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        return True, "Redis 可连接"
    except Exception as e:
        return False, f"Redis 不可用 ({settings.REDIS_URL}): {e}"


def _check_celery_workers() -> Tuple[bool, str]:
    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        ping = inspect.ping()
        if not ping:
            return False, "没有运行中的 Celery Worker（任务会一直排队 PENDING）"
        workers = ", ".join(sorted(ping.keys()))
        return True, f"Celery Worker 在线: {workers}"
    except Exception as e:
        return False, f"无法检查 Celery Worker（请先启动 Redis）: {e}"


async def _check_mcp() -> Tuple[bool, str]:
    url = (settings.MCP_SERVER_URL or "").strip()
    if not url:
        return False, "未配置 MCP_SERVER_URL"

    try:
        from fastmcp import Client

        async with Client(url) as client:
            await client.list_tools()
        return True, f"MCP 可连接: {url}"
    except Exception as e:
        return False, f"MCP 不可用 ({url}): {e}"


async def collect_smart_apply_readiness() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ok_redis, msg_redis = _check_redis()
    checks.append({"name": "redis", "ok": ok_redis, "detail": msg_redis})

    ok_celery, msg_celery = (False, "跳过（Redis 未就绪）")
    if ok_redis:
        ok_celery, msg_celery = _check_celery_workers()
    checks.append({"name": "celery_worker", "ok": ok_celery, "detail": msg_celery})

    ok_mcp, msg_mcp = await _check_mcp()
    checks.append({"name": "mcp_server", "ok": ok_mcp, "detail": msg_mcp})

    checks.append(
        {
            "name": "human_review",
            "ok": True,
            "detail": (
                "已开启人工审核（流程会在优化简历/求职信处暂停，需调用 resume 接口继续）"
                if settings.SMART_APPLY_HUMAN_REVIEW
                else "未开启人工审核（全流程自动跑完）"
            ),
        }
    )

    ready = ok_redis and ok_celery and ok_mcp
    hint = (
        "依赖就绪，可提交智能投递；提交后请轮询 GET /smart-apply/status/{task_id}"
        if ready
        else "请先启动 Redis、Celery Worker、MCP Server，再提交智能投递"
    )

    return {
        "ready": ready,
        "message": hint,
        "checks": checks,
        "langsmith_project": settings.LANGSMITH_PROJECT,
        "mcp_url": settings.MCP_SERVER_URL,
    }


def assert_smart_apply_ready() -> None:
    """同步预检：Redis + Celery（submit 入口用，不等待 MCP HTTP）。"""
    ok_redis, msg_redis = _check_redis()
    if not ok_redis:
        raise RuntimeError(msg_redis)
    ok_celery, msg_celery = _check_celery_workers()
    if not ok_celery:
        raise RuntimeError(msg_celery)
