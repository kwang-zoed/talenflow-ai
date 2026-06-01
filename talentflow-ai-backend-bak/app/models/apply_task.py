from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ApplyTask(SQLModel, table=True):
    """智能投递任务追踪（与 LangGraph thread_id / Celery task_id 关联）。"""

    __tablename__ = "apply_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False)
    job_id: str = Field(index=True, nullable=False)
    thread_id: str = Field(index=True, unique=True, nullable=False)
    celery_task_id: Optional[str] = Field(default=None, index=True)
    stage: str = Field(default="pending", description="当前阶段")
    status: str = Field(default="pending", description="pending|running|success|error|interrupted")
    error: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
