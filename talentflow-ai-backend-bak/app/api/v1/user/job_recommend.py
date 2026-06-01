from fastapi import APIRouter, Depends, Query, Body, HTTPException
from app.core import deps
from app.models import base
from app.core.celery_app import celery_app
from app.services.recommendation_service import generate_recommendation_task

router = APIRouter()


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
