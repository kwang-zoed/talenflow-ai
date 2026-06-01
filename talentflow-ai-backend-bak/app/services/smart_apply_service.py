"""智能投递 Celery 异步任务与共享业务逻辑。"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.resume import Resume
from app.models.user_resume_cache import UserResumeCache

logger = logging.getLogger(__name__)

NODE_PROGRESS: Dict[str, Dict[str, Any]] = {
    "fetch_resume": {
        "current": 1,
        "total": 5,
        "message": "正在获取简历...",
        "percent": 20,
    },
    "optimize_resume": {
        "current": 2,
        "total": 5,
        "message": "正在 AI 优化简历...",
        "percent": 40,
    },
    "save_optimized_resume": {
        "current": 3,
        "total": 5,
        "message": "正在保存优化简历...",
        "percent": 60,
    },
    "generate_letter": {
        "current": 4,
        "total": 5,
        "message": "正在生成求职信...",
        "percent": 80,
    },
    "save_record": {
        "current": 5,
        "total": 5,
        "message": "正在提交投递记录...",
        "percent": 95,
    },
}


def get_valid_resume_cache(db, user_id: int, job_id: str) -> Optional[UserResumeCache]:
    cache = (
        db.query(UserResumeCache)
        .filter(
            UserResumeCache.user_id == user_id,
            UserResumeCache.job_id == job_id,
        )
        .first()
    )
    if not cache:
        return None

    resume = db.query(Resume).filter(Resume.id == cache.optimized_resume_id).first()
    if resume:
        return cache

    logger.warning(
        "缓存关联的优化简历 ID %s 已不存在，清除缓存",
        cache.optimized_resume_id,
    )
    db.delete(cache)
    db.commit()
    return None


def build_initial_state(
    db,
    user_id: int,
    job_id: str,
    job_description: str,
    mode: str,
    resume_id: Optional[int],
) -> Tuple[Optional[Dict[str, Any]], bool, Optional[str]]:
    """返回 (initial_state, is_reused, error_message)。"""
    existing_cache = None
    is_reused = False

    if mode != "force_generate":
        existing_cache = get_valid_resume_cache(db, user_id, job_id)

    if mode == "force_reuse":
        if not existing_cache:
            return None, False, "未找到可复用的优化简历，请先使用 auto 或 force_generate 模式"
        is_reused = True
        initial_state = {
            "user_id": user_id,
            "job_id": job_id,
            "job_description": job_description,
            "resume_id": existing_cache.optimized_resume_id,
            "skip_generation": True,
        }
    elif existing_cache and mode == "auto":
        is_reused = True
        initial_state = {
            "user_id": user_id,
            "job_id": job_id,
            "job_description": job_description,
            "resume_id": existing_cache.optimized_resume_id,
            "skip_generation": True,
        }
    else:
        initial_state = {
            "user_id": user_id,
            "job_id": job_id,
            "job_description": job_description,
            "resume_id": resume_id,
            "skip_generation": False,
        }

    return initial_state, is_reused, None


def update_resume_cache(db, user_id: int, job_id: str, optimized_resume_id: int) -> None:
    cache = (
        db.query(UserResumeCache)
        .filter(
            UserResumeCache.user_id == user_id,
            UserResumeCache.job_id == job_id,
        )
        .first()
    )
    if cache:
        cache.optimized_resume_id = optimized_resume_id
        cache.updated_at = datetime.utcnow()
    else:
        db.add(
            UserResumeCache(
                user_id=user_id,
                job_id=job_id,
                optimized_resume_id=optimized_resume_id,
            )
        )
    db.commit()


def build_apply_response(result: Dict[str, Any], is_reused: bool) -> Dict[str, Any]:
    actually_reused = is_reused and not result.get("resume_saved_in_run")
    return {
        "success": True,
        "message": "简历复用成功" if actually_reused else "AI 生成并投递成功",
        "application_id": result.get("application_id"),
        "resume_id": result.get("resume_id"),
        "cover_letter": result.get("cover_letter"),
        "is_reused": actually_reused,
        "error": None,
    }


async def _run_graph_with_progress(
    celery_task,
    user_id: int,
    job_id: str,
    thread_id: str,
    apply_task_id: Optional[int],
    db,
    initial_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Celery Worker 内执行 LangGraph，写入共享 SQLite Checkpointer。
    每次 asyncio.run 使用独立 aiosqlite 连接，避免 event loop 冲突。
    """
    from app.agents.checkpoint_service import create_ephemeral_checkpointer, stage_from_node
    from app.agents.graph import build_graph
    from app.core.langsmith_tracing import build_langgraph_run_config
    from app.services.apply_task_service import update_apply_task_stage

    checkpointer, conn = await create_ephemeral_checkpointer()
    try:
        graph = build_graph(checkpointer=checkpointer)
        config = build_langgraph_run_config(
            thread_id,
            user_id=user_id,
            job_id=job_id,
            run_name="smart_apply_astream",
            metadata={
                "celery_task_id": getattr(getattr(celery_task, "request", None), "id", None),
            },
        )

        celery_task.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 5,
                "message": "智能投递任务已开始...",
                "percent": 5,
            },
        )
        if apply_task_id:
            update_apply_task_stage(db, apply_task_id, "fetch_resume", status="running")

        final_state: Dict[str, Any] = dict(initial_state)
        async for update in graph.astream(initial_state, config, stream_mode="updates"):
            for node_name, node_output in update.items():
                stage = stage_from_node(node_name)
                meta = NODE_PROGRESS.get(node_name)
                if meta:
                    celery_task.update_state(state="PROGRESS", meta=dict(meta))
                    logger.info("[SmartApply Worker] 节点完成: %s", node_name)
                if apply_task_id:
                    update_apply_task_stage(db, apply_task_id, stage, status="running")
                if isinstance(node_output, dict):
                    final_state.update(node_output)

        from app.agents.checkpoint_service import build_snapshot_response, extract_interrupt_info

        snapshot = await graph.aget_state(config)
        if snapshot and snapshot.interrupts:
            intr = extract_interrupt_info(snapshot)
            review_type = intr.get("review_type")
            stage = build_snapshot_response(thread_id, snapshot)["stage"]
            if apply_task_id:
                update_apply_task_stage(db, apply_task_id, stage, status="interrupted")
            return {
                "interrupted": True,
                "review_type": review_type,
                "message": intr.get("message") or "等待您的确认",
                "thread_id": thread_id,
                "stage": stage,
            }

        return final_state
    finally:
        await conn.close()


@celery_app.task(bind=True, name="app.services.smart_apply_service.smart_apply_task")
def smart_apply_task(self, payload: Dict[str, Any]):
    """Celery 后台执行智能投递 LangGraph 工作流。"""
    from app.core.langsmith_tracing import setup_langsmith_tracing

    setup_langsmith_tracing()

    user_id = int(payload["user_id"])
    job_id = str(payload["job_id"])
    job_description = payload["job_description"]
    mode = payload.get("mode", "auto")
    resume_id = payload.get("resume_id")
    thread_id = payload.get("thread_id")
    apply_task_id = payload.get("apply_task_id")

    db = SessionLocal()
    try:
        initial_state, is_reused, build_error = build_initial_state(
            db, user_id, job_id, job_description, mode, resume_id
        )
        if build_error:
            if apply_task_id:
                from app.services.apply_task_service import update_apply_task_stage
                update_apply_task_stage(db, apply_task_id, "pending", status="error", error=build_error)
            return {"status": "error", "message": build_error, "thread_id": thread_id}

        if not thread_id:
            run_id = getattr(getattr(self, "request", None), "id", None) or "run"
            from app.agents.checkpoint_service import make_thread_id
            thread_id = make_thread_id(user_id, job_id, str(run_id))

        if not apply_task_id:
            from app.services.apply_task_service import get_apply_task_by_thread
            row = get_apply_task_by_thread(db, thread_id, user_id)
            apply_task_id = row.id if row else None

        result = asyncio.run(
            _run_graph_with_progress(
                self, user_id, job_id, thread_id, apply_task_id, db, initial_state
            )
        )

        if result.get("interrupted"):
            review_type = result.get("review_type")
            stage = result.get("stage", "optimize")
            from app.agents.checkpoint_service import REVIEW_MESSAGES, STAGE_PERCENT

            message = result.get("message") or REVIEW_MESSAGES.get(review_type, "等待您的确认")
            percent = STAGE_PERCENT.get(stage, 40)
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 2 if review_type == "optimized_resume" else 4,
                    "total": 5,
                    "message": message,
                    "percent": percent,
                    "interrupted": True,
                    "review_type": review_type,
                    "thread_id": thread_id,
                },
            )
            return {
                "status": "interrupted",
                "message": message,
                "thread_id": thread_id,
                "review_type": review_type,
                "stage": stage,
            }

        if result.get("error_message"):
            logger.error("[SmartApply Worker] 失败: %s", result["error_message"])
            if apply_task_id:
                from app.services.apply_task_service import update_apply_task_stage
                update_apply_task_stage(
                    db, apply_task_id, "save_record", status="error", error=result["error_message"]
                )
            return {
                "status": "error",
                "message": result["error_message"],
                "thread_id": thread_id,
            }

        if result.get("resume_saved_in_run") and result.get("resume_id"):
            update_resume_cache(db, user_id, job_id, int(result["resume_id"]))

        if apply_task_id:
            from app.services.apply_task_service import update_apply_task_stage
            update_apply_task_stage(db, apply_task_id, "done", status="success")

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 5,
                "total": 5,
                "message": "投递完成",
                "percent": 100,
            },
        )

        return {
            "status": "success",
            "user_id": user_id,
            "job_id": job_id,
            "thread_id": thread_id,
            "result": build_apply_response(result, is_reused),
        }
    except Exception as e:
        logger.error("[SmartApply Worker] 异常: %s", e, exc_info=True)
        if apply_task_id:
            from app.services.apply_task_service import update_apply_task_stage
            update_apply_task_stage(db, apply_task_id, "save_record", status="error", error=str(e))
        return {"status": "error", "message": f"智能投递失败: {str(e)}", "thread_id": thread_id}
    finally:
        db.close()
