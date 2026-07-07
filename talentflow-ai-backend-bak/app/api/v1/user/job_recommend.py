from fastapi import APIRouter, Depends, Query, Body, HTTPException
from app.core import deps, database
from app.models import base
from app.core.celery_app import celery_app
from app.services.recommendation_service import generate_recommendation_task, RecommendationService
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/recommend/session")
async def create_job_recommend_session(
    page_size: int = Body(10, embed=True),
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """创建职位推荐会话：首屏同步返回粗排结果，后台 Celery 精排。"""
    service = RecommendationService(db)
    result = service.create_job_recommend_session(current_user.id, min(max(page_size, 1), 20))
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "创建失败"))
    return result


@router.get("/recommend/session/{session_id}/more")
def get_job_recommend_session_more(
    session_id: str,
    exclude_ids: str = Query("", description="已展示的 job_id，逗号分隔"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """翻页加载更多职位推荐。"""
    parsed_exclude = []
    for part in (exclude_ids or "").split(","):
        part = part.strip()
        if part.isdigit():
            parsed_exclude.append(int(part))

    service = RecommendationService(db)
    result = service.get_recommend_session_more(session_id, parsed_exclude, limit)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "会话不存在"))
    if result.get("user_id") and result["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该推荐会话")
    return result


@router.get("/recommend/session/{session_id}/status")
def get_job_recommend_session_status(
    session_id: str,
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """查询职位推荐会话精排状态。"""
    service = RecommendationService(db)
    result = service.get_recommend_session_status(session_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "会话不存在"))
    if result.get("user_id") and result["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该推荐会话")
    return result


@router.post("/recommend/session/{session_id}/apply-rerank")
def apply_job_recommend_session_rerank(
    session_id: str,
    limit: int = Query(10, ge=1, le=100, description="按精排顺序返回条数"),
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_user),
):
    """应用精排：按精排池重新排序职位列表。"""
    service = RecommendationService(db)
    result = service.apply_session_rerank_view(session_id, limit)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "应用精排失败"))
    if result.get("user_id") and result["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该推荐会话")
    return result


# ========== 图二：提交推荐任务接口 ==========
@router.post("/recommend/submit")
async def recommend_submit(
    user_id: int = Body(..., embed=True),
    top_k: int = Body(5, embed=True),
    current_user: base.UserDB = Depends(deps.get_current_user)
):
    """提交推荐任务"""
    # 调用 Celery 异步任务
    task = generate_recommendation_task.delay(user_id, top_k)
    
    return {
        "message": "任务已接受，AI计算中...",
        "task_id": task.id,
        "code": 200
    }


# ========== 图三：获取推荐结果接口 ==========
@router.get("/recommend/status/{task_id}")
async def get_recommend_status(task_id: str):
    """获取推荐结果"""
    # 获取 AsyncResult 对象
    from celery.result import AsyncResult
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.ready():
        # 任务完成
        if task_result.successful():
            result = task_result.result
            if isinstance(result, dict) and result.get("status") == "success":
                return {
                    "status": "success",
                    "data": result.get("result", [])
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("message", "未知错误")
                }
        else:
            return {
                "status": "error",
                "message": str(task_result.info) if task_result.info else "任务执行失败"
            }
    else:
        # 任务进行中
        return {
            "status": "processing"
        }


# ========== 同步接口（已废弃）==========
@router.get("/recommend/{user_id}", deprecated=True)
def get_job_recommendations(
    user_id: int,
    top_k: int = Query(5, ge=1, le=20),
    current_user: base.UserDB = Depends(deps.get_current_user)
):
    """【已废弃】同步推荐。请使用 POST /recommend/submit + GET /recommend/status/{task_id}"""
    raise HTTPException(
        status_code=410,
        detail="同步推荐已废弃，请使用 POST /user/recommend/submit 与 GET /user/recommend/status/{task_id}",
    )
