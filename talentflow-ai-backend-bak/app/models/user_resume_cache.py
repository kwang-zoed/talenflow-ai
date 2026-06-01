from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class UserResumeCache(SQLModel, table=True):
    """用户 + 职位 -> 优化简历ID 的缓存映射"""

    __tablename__ = "user_resume_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, nullable=False, description="用户ID")
    job_id: str = Field(index=True, nullable=False, description="职位ID")
    optimized_resume_id: int = Field(nullable=False, description="优化后的简历ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
