"""
LangSmith 追踪配置（LangGraph / LangChain）。

在进程启动时调用 setup_langsmith_tracing()，之后 graph.ainvoke / astream 会自动上报 trace。
文档: https://docs.smith.langchain.com/
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_tracing_initialized = False
_tracing_active = False


def is_langsmith_enabled() -> bool:
    return _tracing_active or os.getenv("LANGCHAIN_TRACING_V2", "").lower() in (
        "1",
        "true",
        "yes",
    )


def setup_langsmith_tracing() -> bool:
    """
    通过环境变量启用 LangSmith。需在首次执行 LangGraph 前调用（main / Celery worker 启动时）。
    """
    global _tracing_initialized, _tracing_active

    if _tracing_initialized:
        return _tracing_active

    from app.core.config import settings

    _tracing_initialized = True

    if not settings.LANGSMITH_TRACING_ENABLED:
        logger.debug("LangSmith 追踪未启用（LANGSMITH_TRACING=false）")
        return False

    api_key = (settings.LANGSMITH_API_KEY or "").strip()
    if not api_key:
        logger.warning(
            "已开启 LANGSMITH_TRACING，但未配置 LANGSMITH_API_KEY（或 LANGCHAIN_API_KEY）"
        )
        return False

    project = (settings.LANGSMITH_PROJECT or "talentflow-smart-apply").strip()

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGSMITH_PROJECT"] = project

    endpoint = (settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com").strip()
    os.environ["LANGSMITH_ENDPOINT"] = endpoint

    _tracing_active = True
    logger.info("LangSmith 追踪已启用，project=%s", project)
    return True


def build_langgraph_run_config(
    thread_id: str,
    *,
    user_id: Optional[int] = None,
    job_id: Optional[str] = None,
    run_name: str = "smart_apply_workflow",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    extra_configurable: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    构建 LangGraph 调用的 config，在 LangSmith 中按 run_name / tags / metadata 分组。
    """
    configurable: Dict[str, Any] = {"thread_id": thread_id}
    if extra_configurable:
        configurable.update(extra_configurable)

    config: Dict[str, Any] = {
        "configurable": configurable,
        "run_name": run_name,
    }

    if is_langsmith_enabled():
        tag_list: List[str] = ["talentflow", "smart-apply", "langgraph"]
        if tags:
            tag_list.extend(tags)
        if user_id is not None:
            tag_list.append(f"user-{user_id}")
        if job_id:
            tag_list.append(f"job-{job_id}")
        config["tags"] = tag_list

        meta: Dict[str, Any] = {
            "thread_id": thread_id,
            "workflow": "smart_apply",
            "graph": "talentflow_smart_apply",
        }
        if metadata:
            meta.update(metadata)
        if user_id is not None:
            meta["user_id"] = user_id
        if job_id:
            meta["job_id"] = str(job_id)
        config["metadata"] = meta

    return config
