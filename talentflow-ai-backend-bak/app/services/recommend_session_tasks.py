"""推荐会话 Celery 任务（独立模块，确保 Worker 启动时可靠注册）。"""
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.recommend_session_store import patch_recommend_session

logger = logging.getLogger(__name__)

TASK_NAME = "app.recommendation_service.rerank_recommend_session_task"


@celery_app.task(bind=True, name=TASK_NAME, soft_time_limit=360, time_limit=420)
def rerank_recommend_session_task(self, session_id: str):
    """后台精排推荐会话（仅精排，不阻塞首屏）。"""
    try:
        from app.services.recommendation_service import RecommendationService

        db = SessionLocal()
        try:
            service = RecommendationService(db)
            service.complete_session_rerank(session_id)
            return {"status": "success", "session_id": session_id}
        finally:
            db.close()
    except Exception as e:
        logger.error("[Celery Worker] 会话精排失败 session_id=%s: %s", session_id, e, exc_info=True)
        patch_recommend_session(session_id, {"status": "coarse_ready"})
        return {"status": "error", "message": str(e)}
