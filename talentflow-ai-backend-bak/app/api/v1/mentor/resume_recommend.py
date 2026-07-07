import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from celery.result import AsyncResult

from app.core import deps, database
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.crud import crud
from app.models.base import UserDB
from app.services.recommendation_service import generate_resume_recommendation_task, RecommendationService
from sqlalchemy.orm import Session
from app.models.resume import Resume

router = APIRouter()


def _is_task_not_registered(info) -> bool:
    """仅 Celery 未注册任务时返回 True，避免普通任务失败误触发同步降级。"""
    if info is None:
        return False
    return "NotRegistered" in str(info)


def _run_sync_recommend(job_id: int, top_k: int = 5):
    db = SessionLocal()
    try:
        service = RecommendationService(db)
        results = service.recommend_resumes(job_id, top_k)
        return {"status": "success", "data": results, "job_id": job_id, "sync": True}
    finally:
        db.close()


@router.post("/recommend/session")
async def create_recommend_session(
    job_id: int = Body(..., embed=True),
    page_size: int = Body(10, embed=True),
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_active_mentor),
):
    """创建推荐会话：首屏同步返回粗排结果，后台 Celery 精排。"""
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    if job.mentor_id and job.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该职位")

    service = RecommendationService(db)
    result = service.create_recommend_session(job_id, min(max(page_size, 1), 20))
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "创建失败"))
    return result


@router.get("/recommend/session/{session_id}/more")
def get_recommend_session_more(
    session_id: str,
    exclude_ids: str = Query("", description="已展示的 resume_id，逗号分隔"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_active_mentor),
):
    """翻页加载更多（exclude_ids 去重，精排完成后自动切换精排池）。"""
    parsed_exclude = []
    for part in (exclude_ids or "").split(","):
        part = part.strip()
        if part.isdigit():
            parsed_exclude.append(int(part))

    service = RecommendationService(db)
    result = service.get_recommend_session_more(session_id, parsed_exclude, limit)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "会话不存在"))
    return result


@router.get("/recommend/session/{session_id}/status")
def get_recommend_session_status(
    session_id: str,
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_active_mentor),
):
    """查询会话精排状态（coarse_ready / rerank_queued / reranking / rerank_ready）。"""
    service = RecommendationService(db)
    result = service.get_recommend_session_status(session_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "会话不存在"))
    return result


@router.post("/recommend/session/{session_id}/apply-rerank")
def apply_recommend_session_rerank(
    session_id: str,
    limit: int = Query(10, ge=1, le=100, description="按精排顺序返回条数"),
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_active_mentor),
):
    """应用精排：按精排池重新排序并更新匹配分数。"""
    service = RecommendationService(db)
    result = service.apply_session_rerank_view(session_id, limit)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "应用精排失败"))
    return result


@router.post("/recommend/submit")
async def resume_recommend_submit(
    job_id: int = Body(..., embed=True),
    top_k: int = Body(5, embed=True),
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_active_mentor),
):
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    if job.mentor_id and job.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该职位")

    task = generate_resume_recommendation_task.delay(job_id, top_k)
    return {
        "message": "任务已接受，AI计算中...",
        "task_id": task.id,
        "job_id": job_id,
        "code": 200,
    }


@router.get("/recommend/status/{task_id}")
async def get_resume_recommend_status(
    task_id: str,
    job_id: int | None = Query(None, description="Celery 未注册任务时用于同步降级"),
    top_k: int = Query(5, ge=1, le=20),
):
    task_result = AsyncResult(task_id, app=celery_app)
    if not task_result.ready():
        return {"status": "processing"}

    if task_result.successful():
        result = task_result.result
        if isinstance(result, dict) and result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("result", []),
                "job_id": result.get("job_id"),
            }
        return {
            "status": "error",
            "message": result.get("message", "未知错误") if isinstance(result, dict) else "未知错误",
        }

    info = task_result.info
    if _is_task_not_registered(info):
        if job_id is not None:
            return await asyncio.to_thread(_run_sync_recommend, job_id, top_k)
        return {
            "status": "error",
            "message": (
                "Celery Worker 未加载简历推荐任务。"
                "请重启 Celery：celery -A app.core.celery_app worker --loglevel=info --pool=solo"
            ),
        }

    return {
        "status": "error",
        "message": str(info) if info else "任务执行失败",
    }


@router.get("/resumes/{resume_id}")
def get_resume_detail_for_hr(
    resume_id: int,
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_active_mentor),
):
    resume = db.get(Resume, resume_id)
    if not resume or resume.status == "Archived":
        raise HTTPException(status_code=404, detail="简历不存在")
    service = RecommendationService(db)
    return service._resume_to_dict(resume, mask_contact=False)
