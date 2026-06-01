import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth
from app.api.v1.admin import (
    get_dashboard,
    job_manage,
    resume_manage,
    task_manage,
    user_manage,
)
from app.api.v1.mentor import (
    applications,
    dashboard,
    job_manage as hr_job_manage,
    task_manage as mentor_task_manage,
)
from app.api.v1.user import (
    applications as user_applications,
    job_list as user_job_list,
    job_recommend as user_job_recommend,
    resume_manage as user_resume_manage,
    smart_apply as user_smart_apply,
    task_manage as user_task_manage,
)
from app.core.config import settings
from app.core.langsmith_tracing import setup_langsmith_tracing

logger = logging.getLogger(__name__)

# 尽早启用 LangSmith（需在 LangGraph / LangChain 首次运行前）
if setup_langsmith_tracing():
    logger.info("LangSmith 已就绪，project=%s", settings.LANGSMITH_PROJECT)
else:
    logger.warning(
        "LangSmith 未启用：请设置 LANGSMITH_TRACING=true 与 LANGSMITH_API_KEY "
        "（Docker 需写在 talentflow-ai/.env；本地可写在 talentflow-ai-backend-bak/.env）"
    )
_warmup_task: asyncio.Task | None = None


async def _background_warmup() -> None:
    """后台预热大模型，避免阻塞 HTTP 接口。"""
    try:
        print("[MAIN] 后台预热 embedding...")
        from app.rag.embeddings import embed_documents

        embed_documents(["warmup"])
        print("[MAIN] embedding 预热完成")

        print("[MAIN] 后台预热 reranker...")
        from app.rag.reranker import get_reranker

        get_reranker()
        print("[MAIN] reranker 预热完成")

        print("[MAIN] 后台初始化智能投递 LangGraph...")
        from app.agents.graph import init_smart_apply_graph

        await init_smart_apply_graph()
        print("[MAIN] 智能投递图预热完成")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning("后台预热失败（不影响其它接口）: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _warmup_task

    print("[MAIN] 应用启动中...")
    os.makedirs("uploads/jobs", exist_ok=True)

    try:
        from app.models.bootstrap import load_all_models

        load_all_models()
        print("[MAIN] ORM 模型注册完成")
    except Exception as e:
        print(f"[MAIN] 模型注册失败: {e}")

    try:
        from sqlmodel import SQLModel

        from app.core.database import engine
        from app.models.user_resume_cache import UserResumeCache
        from app.models.apply_task import ApplyTask

        SQLModel.metadata.create_all(
            engine, tables=[UserResumeCache.__table__, ApplyTask.__table__]
        )
        print("[MAIN] user_resume_cache / apply_tasks 表就绪")
    except Exception as e:
        print(f"[MAIN] user_resume_cache 表初始化失败: {e}")

    if settings.PRELOAD_MODELS_ON_STARTUP:
        _warmup_task = asyncio.create_task(_background_warmup())
        print("[MAIN] 已启动后台预热（接口无需等待预热完成）")
    else:
        print("[MAIN] 已跳过启动预热（首次推荐/智能投递时再加载模型）")

    yield

    print("[MAIN] 正在关闭服务...")
    if _warmup_task and not _warmup_task.done():
        _warmup_task.cancel()
        try:
            await _warmup_task
        except asyncio.CancelledError:
            pass

    try:
        from app.agents.graph import shutdown_smart_apply_graph

        await shutdown_smart_apply_graph()
    except Exception as e:
        print(f"[MAIN] LangGraph 资源释放失败: {e}")

    print("[MAIN] 服务已关闭")


app = FastAPI(title="Smart Customer Service API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(job_manage.router, prefix="/api/v1/admin", tags=["管理员-职位管理"])
app.include_router(task_manage.router, prefix="/api/v1/admin", tags=["管理员-任务管理"])
app.include_router(user_manage.router, prefix="/api/v1/admin", tags=["管理员-用户管理"])
app.include_router(resume_manage.router, prefix="/api/v1/admin", tags=["管理员-简历管理"])
app.include_router(get_dashboard.router, prefix="/api/v1/admin/stats", tags=["管理员-数据统计"])
app.include_router(mentor_task_manage.router, prefix="/api/v1/mentor", tags=["Mentor-任务管理"])
app.include_router(dashboard.router, prefix="/api/v1/mentor", tags=["Mentor-仪表盘"])
app.include_router(applications.router, prefix="/api/v1/mentor", tags=["Mentor-投递管理"])
app.include_router(applications.router, prefix="/hr", tags=["Mentor-投递管理-兼容"])
app.include_router(applications.router, prefix="/api/v1/hr", tags=["Mentor-投递管理-兼容-v1"])
app.include_router(hr_job_manage.router, prefix="/hr", tags=["HR-职位管理-兼容"])
app.include_router(hr_job_manage.router, prefix="/api/v1/hr", tags=["HR-职位管理-兼容-v1"])
app.include_router(hr_job_manage.router, prefix="/api/v1/mentor", tags=["Mentor-职位管理"])
app.include_router(user_resume_manage.router, prefix="/api/v1", tags=["用户端-简历管理"])
app.include_router(user_task_manage.router, prefix="/api/v1/user/tasks", tags=["用户端-任务管理"])
app.include_router(user_job_recommend.router, prefix="/api/v1/user", tags=["用户端-职位推荐"])
app.include_router(user_applications.router, prefix="/api/v1/user", tags=["用户端-投递管理"])
app.include_router(user_job_list.router, prefix="/api/v1/user", tags=["用户端-职位列表"])
app.include_router(user_smart_apply.router, prefix="/api/v1/user", tags=["用户端-智能投递"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {"message": "Welcome to Smart Customer Service API"}
