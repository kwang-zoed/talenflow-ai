"""按依赖顺序预加载所有 SQLModel 模型，避免 MCP 独立进程中的 Mapper 初始化失败。"""


def load_all_models() -> None:
    from app.models.user import User  # noqa: F401
    from app.models.task import Task  # noqa: F401
    from app.models.job_position import JobPosition  # noqa: F401
    from app.models.resume import Resume  # noqa: F401
    from app.models.application import Application  # noqa: F401
    from app.models.user_resume_cache import UserResumeCache  # noqa: F401
    from app.models.apply_task import ApplyTask  # noqa: F401
