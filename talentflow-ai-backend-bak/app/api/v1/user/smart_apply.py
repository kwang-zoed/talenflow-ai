import logging
import uuid

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.checkpoint_service import (
    STAGE_PERCENT,
    get_thread_checkpoint_state,
    make_thread_id,
    resume_thread_workflow,
)
from app.agents.graph import get_smart_apply_graph
from app.core import database, deps
from app.core.langsmith_tracing import build_langgraph_run_config
from app.core.celery_app import celery_app
from app.models import base
from app.schemas.smart_apply_schema import (
    ApplyRequest,
    ApplyResponse,
    ApplyTaskListResponse,
    ApplyTaskSummary,
    SmartApplyReadinessResponse,
    SmartApplyResumeRequest,
    SmartApplyResumeResponse,
    SmartApplySubmitResponse,
    SmartApplyTaskStatusResponse,
    SmartApplyThreadStateResponse,
)
from app.services.apply_task_service import (
    create_apply_task,
    get_apply_task_by_celery_id,
    get_apply_task_by_thread,
    list_apply_tasks,
    set_apply_task_celery_id,
    update_apply_task_stage,
)
from app.services.smart_apply_readiness import (
    assert_smart_apply_ready,
    collect_smart_apply_readiness,
)
from app.services.smart_apply_service import (
    build_apply_response,
    build_initial_state,
    smart_apply_task,
    update_resume_cache,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _execute_smart_apply_sync(
    data: ApplyRequest,
    db: Session,
    user_id: int,
) -> ApplyResponse:
    """同步执行（兼容旧接口，不推荐长耗时场景使用）。"""
    initial_state, is_reused, build_error = build_initial_state(
        db,
        user_id,
        data.job_id,
        data.job_description,
        data.mode,
        data.resume_id,
    )
    if build_error:
        raise HTTPException(status_code=404, detail=build_error)

    thread_id = f"apply_{user_id}_{data.job_id}"
    config = build_langgraph_run_config(
        thread_id,
        user_id=user_id,
        job_id=data.job_id,
        run_name="smart_apply_sync",
    )
    graph = await get_smart_apply_graph()
    result = await graph.ainvoke(initial_state, config)

    if result.get("error_message"):
        logger.error("Graph 执行失败: %s", result["error_message"])
        return ApplyResponse(
            success=False,
            message="投递流程执行失败",
            error=result["error_message"],
        )

    if result.get("resume_saved_in_run") and result.get("resume_id"):
        update_resume_cache(db, user_id, data.job_id, int(result["resume_id"]))

    payload = build_apply_response(result, is_reused)
    return ApplyResponse(**payload)


def _format_task_status(
    task_id: str,
    db: Session | None = None,
    user_id: int | None = None,
) -> SmartApplyTaskStatusResponse:
    apply_row = None
    if db is not None:
        apply_row = get_apply_task_by_celery_id(db, task_id)
        if apply_row and user_id is not None and apply_row.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权查看该任务")

    result = AsyncResult(task_id, app=celery_app)
    logger.debug("[smart-apply status] task_id=%s state=%s", task_id, result.state)

    thread_id = apply_row.thread_id if apply_row else None
    stage = apply_row.stage if apply_row else None

    if result.state == "PENDING":
        return SmartApplyTaskStatusResponse(
            status="processing",
            message=(
                "任务排队中：Celery Worker 可能未启动。"
                "请运行 celery -A app.core.celery_app worker --loglevel=info --pool=solo"
            ),
            percent=STAGE_PERCENT.get(stage or "pending", 0),
            thread_id=thread_id,
            stage=stage,
        )

    if result.state == "PROGRESS":
        meta = result.info if isinstance(result.info, dict) else {}
        if meta.get("interrupted"):
            return SmartApplyTaskStatusResponse(
                status="interrupted",
                message=meta.get("message", "等待您的确认"),
                percent=meta.get("percent") or STAGE_PERCENT.get(stage or "optimize", 40),
                thread_id=meta.get("thread_id") or thread_id,
                stage=stage,
                review_type=meta.get("review_type"),
                review_message=meta.get("message"),
            )
        percent = meta.get("percent")
        if percent is None and stage:
            percent = STAGE_PERCENT.get(stage, 0)
        return SmartApplyTaskStatusResponse(
            status="processing",
            message=meta.get("message", "智能投递进行中..."),
            percent=percent or 0,
            current=meta.get("current", 0),
            total=meta.get("total", 5),
            thread_id=thread_id,
            stage=stage,
        )

    if apply_row and apply_row.status == "interrupted" and result.state in ("SUCCESS", "PROGRESS"):
        return SmartApplyTaskStatusResponse(
            status="interrupted",
            message="等待您的确认后继续投递",
            percent=STAGE_PERCENT.get(apply_row.stage, 40),
            thread_id=thread_id,
            stage=apply_row.stage,
        )

    if result.state == "SUCCESS":
        task_output = result.result
        if isinstance(task_output, dict):
            thread_id = thread_id or task_output.get("thread_id")
            stage = stage or task_output.get("stage")
        if isinstance(task_output, dict) and task_output.get("status") == "interrupted":
            return SmartApplyTaskStatusResponse(
                status="interrupted",
                message=task_output.get("message", "等待您的确认"),
                percent=STAGE_PERCENT.get(task_output.get("stage") or stage or "optimize", 40),
                thread_id=thread_id,
                stage=task_output.get("stage") or stage,
                review_type=task_output.get("review_type"),
                review_message=task_output.get("message"),
            )
        if isinstance(task_output, dict) and task_output.get("status") == "success":
            return SmartApplyTaskStatusResponse(
                status="success",
                message="投递完成",
                percent=100,
                thread_id=thread_id,
                stage="done",
                data=task_output.get("result"),
            )
        if isinstance(task_output, dict) and task_output.get("status") == "error":
            return SmartApplyTaskStatusResponse(
                status="error",
                message=task_output.get("message", "投递失败"),
                thread_id=thread_id,
                stage=stage,
            )
        return SmartApplyTaskStatusResponse(
            status="success",
            message="投递完成",
            percent=100,
            thread_id=thread_id,
            stage="done",
            data=task_output,
        )

    if result.state == "FAILURE":
        info_str = str(result.info) if result.info else "未知错误"
        if "NotRegistered" in info_str or "smart_apply_task" in info_str:
            message = (
                "Celery Worker 未加载智能投递任务，请重启 Worker："
                "celery -A app.core.celery_app worker --loglevel=info --pool=solo"
            )
        else:
            message = f"投递失败: {info_str[:120]}"
        return SmartApplyTaskStatusResponse(
            status="error",
            message=message,
            thread_id=thread_id,
            stage=stage,
        )

    return SmartApplyTaskStatusResponse(
        status="processing",
        message=f"状态: {result.state}",
        percent=STAGE_PERCENT.get(stage or "pending", 0),
        thread_id=thread_id,
        stage=stage,
    )


def _to_task_summary(row) -> ApplyTaskSummary:
    return ApplyTaskSummary(
        id=row.id,
        job_id=row.job_id,
        thread_id=row.thread_id,
        celery_task_id=row.celery_task_id,
        stage=row.stage,
        status=row.status,
        error=row.error,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.get("/smart-apply/readiness", response_model=SmartApplyReadinessResponse)
async def smart_apply_readiness(
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """检查智能投递依赖（Redis / Celery / MCP）是否就绪。"""
    data = await collect_smart_apply_readiness()
    return SmartApplyReadinessResponse(**data)


@router.post("/smart-apply/submit", response_model=SmartApplySubmitResponse)
async def smart_apply_submit(
    data: ApplyRequest,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """提交智能投递异步任务，立即返回 task_id 与 thread_id。"""
    user_id = current_user.id
    logger.info(
        "用户 %s 提交智能投递任务 -> 职位 %s, 模式: %s",
        user_id,
        data.job_id,
        data.mode,
    )

    _, _, build_error = build_initial_state(
        db,
        user_id,
        data.job_id,
        data.job_description,
        data.mode,
        data.resume_id,
    )
    if build_error:
        raise HTTPException(status_code=404, detail=build_error)

    try:
        assert_smart_apply_ready()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": str(exc),
                "hint": "先 GET /api/v1/user/smart-apply/readiness 查看缺哪项；"
                "本地需同时启动 Redis、Celery Worker、MCP Server。",
            },
        ) from exc

    try:
        readiness = await collect_smart_apply_readiness()
        if not readiness.get("ready"):
            mcp_fail = next(
                (c for c in readiness.get("checks", []) if c.get("name") == "mcp_server" and not c.get("ok")),
                None,
            )
            if mcp_fail:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": mcp_fail.get("detail", "MCP 不可用"),
                        "hint": "在 backend 目录启动: python -m mcp_server.server 或 uvicorn（见 scripts/start_local_dev.ps1）",
                    },
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("MCP 预检异常（仍尝试提交）: %s", exc)

    run_id = uuid.uuid4().hex[:12]
    thread_id = make_thread_id(user_id, data.job_id, run_id)

    apply_row = create_apply_task(
        db,
        user_id=user_id,
        job_id=data.job_id,
        thread_id=thread_id,
        celery_task_id="pending",
    )

    payload = {
        "user_id": user_id,
        "job_id": data.job_id,
        "job_description": data.job_description,
        "mode": data.mode,
        "resume_id": data.resume_id,
        "thread_id": thread_id,
        "apply_task_id": apply_row.id,
    }
    task = smart_apply_task.delay(payload)
    set_apply_task_celery_id(db, apply_row.id, task.id)

    return SmartApplySubmitResponse(
        task_id=task.id,
        thread_id=thread_id,
        message="智能投递任务已提交，正在后台执行",
        job_id=data.job_id,
    )


@router.get("/smart-apply/status/{task_id}", response_model=SmartApplyTaskStatusResponse)
async def smart_apply_status(
    task_id: str,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """轮询智能投递任务进度与结果（含 thread_id / stage）。"""
    return _format_task_status(task_id, db=db, user_id=current_user.id)


@router.get("/smart-apply/tasks", response_model=ApplyTaskListResponse)
async def smart_apply_list_tasks(
    limit: int = 20,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """列出当前用户的智能投递任务（含 thread_id，便于查 Checkpointer）。"""
    rows = list_apply_tasks(db, current_user.id, limit=min(limit, 50))
    return ApplyTaskListResponse(
        tasks=[_to_task_summary(r) for r in rows],
        total=len(rows),
    )


@router.get("/smart-apply/thread/{thread_id}", response_model=SmartApplyThreadStateResponse)
async def smart_apply_get_thread(
    thread_id: str,
    include_details: bool = False,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """通过 LangGraph Checkpointer 查询 thread 快照与黑板关键字段。"""
    row = get_apply_task_by_thread(db, thread_id, current_user.id)
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在或无权访问")

    snapshot = await get_thread_checkpoint_state(thread_id, include_details=include_details)
    return SmartApplyThreadStateResponse(
        **snapshot,
        celery_task_id=row.celery_task_id,
        job_id=row.job_id,
    )


@router.post("/smart-apply/thread/{thread_id}/resume", response_model=SmartApplyResumeResponse)
async def smart_apply_resume_thread(
    thread_id: str,
    body: SmartApplyResumeRequest,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """从 Checkpointer 断点续跑；updates 非空时用于人工审核回填。"""
    row = get_apply_task_by_thread(db, thread_id, current_user.id)
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在或无权访问")

    try:
        out = await resume_thread_workflow(thread_id, body.updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("续跑失败 thread_id=%s: %s", thread_id, exc, exc_info=True)
        update_apply_task_stage(db, row.id, row.stage, status="error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"续跑失败: {exc}") from exc

    graph_result = out.get("result") or {}
    workflow_status = out.get("status", "running")
    apply_data = None

    if graph_result.get("error_message"):
        update_apply_task_stage(
            db, row.id, out.get("stage") or row.stage, status="error", error=graph_result["error_message"]
        )
        workflow_status = "error"
    elif graph_result.get("application_id"):
        update_apply_task_stage(db, row.id, "done", status="success")
        if graph_result.get("resume_saved_in_run") and graph_result.get("resume_id"):
            update_resume_cache(db, current_user.id, row.job_id, int(graph_result["resume_id"]))
        apply_data = ApplyResponse(**build_apply_response(graph_result, is_reused=False))
        workflow_status = "success"
    elif workflow_status == "interrupted":
        update_apply_task_stage(db, row.id, out.get("stage") or row.stage, status="interrupted")
    else:
        update_apply_task_stage(db, row.id, out.get("stage") or row.stage, status=workflow_status)

    message = out.get("review_message") or "续跑完成"
    if workflow_status == "success":
        message = "投递完成"
    elif workflow_status == "error":
        message = graph_result.get("error_message", "续跑失败")

    return SmartApplyResumeResponse(
        status=workflow_status,
        message=message,
        thread_id=thread_id,
        stage=out.get("stage"),
        review_type=out.get("review_type"),
        review_message=out.get("review_message"),
        percent=out.get("percent") or 0,
        state=out.get("state") or {},
        data=apply_data,
    )


@router.post("/smart-apply", response_model=ApplyResponse, deprecated=True)
async def smart_apply_endpoint(
    data: ApplyRequest,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """
    [已废弃] 同步智能投递，HTTP 会阻塞至全流程结束。
    请改用 POST /smart-apply/submit + GET /smart-apply/status/{task_id}。
    """
    return await _execute_smart_apply_sync(data, db, current_user.id)
