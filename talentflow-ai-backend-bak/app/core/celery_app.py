
import os
from celery import Celery

_redis_password = os.getenv("REDIS_PASSWORD", "123456")
_redis_host = os.getenv("REDIS_HOST", "localhost")
_redis_port = os.getenv("REDIS_PORT", "6379")
_default_broker = f"redis://:{_redis_password}@{_redis_host}:{_redis_port}/0"
_default_backend = f"redis://:{_redis_password}@{_redis_host}:{_redis_port}/1"

_broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", _default_broker))
_result_backend = os.getenv("CELERY_RESULT_BACKEND", _default_backend)

celery_app = Celery(
    "worker",
    broker=_broker_url,
    backend=_result_backend,
)

# 自动发现并加载任务模块
celery_app.autodiscover_tasks(["app.services"])

# 显式导入非标准命名的任务模块（autodiscover 只找 tasks.py）
_result_expires = int(os.getenv("CELERY_RESULT_EXPIRES", str(60 * 60 * 24)))

celery_app.conf.update(
    include=[
        "app.services.recommend_session_tasks",
        "app.services.recommendation_service",
        "app.services.smart_apply_service",
    ],
    result_expires=_result_expires,
)

# Worker 启动时必须 import 任务模块，否则 delay() 后状态轮询会报 NotRegistered
import app.services.recommend_session_tasks  # noqa: F401, E402
import app.services.recommendation_service  # noqa: F401, E402
import app.services.smart_apply_service  # noqa: F401, E402

from app.core.langsmith_tracing import setup_langsmith_tracing  # noqa: E402

setup_langsmith_tracing()
