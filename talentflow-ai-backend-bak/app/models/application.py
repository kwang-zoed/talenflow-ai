from sqlmodel import SQLModel, Field, Text
from datetime import datetime
from typing import Optional

class Application(SQLModel, table=True):
    __tablename__ = "applications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(description="用户ID", foreign_key="users.id")
    job_id: Optional[int] = Field(default=None, description="职位ID", foreign_key="job_positions.id")
    task_id: Optional[int] = Field(default=None, description="任务ID", foreign_key="tasks.id")
    resume_id: Optional[int] = Field(default=None, description="简历ID", foreign_key="resumes.id")
    cover_letter: Optional[str] = Field(sa_type=Text, description="求职信")
    status: str = Field(max_length=20, default="pending", description="状态")
    remark: Optional[str] = Field(sa_type=Text, default=None, description="审核备注")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
