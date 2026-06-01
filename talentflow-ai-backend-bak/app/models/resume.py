from sqlmodel import SQLModel, Field,Text
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, JSON

class Resume(SQLModel, table=True):
    __tablename__ = "resumes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(description="用户ID")
    name: str = Field(max_length=50, description="姓名")
    phone: Optional[str] = Field(max_length=20, description="电话")
    email: Optional[str] = Field(max_length=100, description="邮箱")
    title: Optional[str] = Field(max_length=100, description="职位标题")
    education: Optional[str] = Field(max_length=50, description="学历")
    experience_years: Optional[int] = Field( description="工作经验")
    skills: Optional[list] = Field(sa_column=Column(JSON), description="技能列表(JSON)")
    summary: Optional[str] = Field(sa_type=Text, description="个人简介")
    project_experience: Optional[str] = Field(sa_type=Text, description="项目经验")
    status: str = Field(max_length=20, default="Pending", description="状态")
    is_default: int = Field(default=0, description="是否默认简历")
    vector_id: Optional[str] = Field(max_length=100, description="向量ID")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="更新时间")
    work_experience: Optional[str] = Field(sa_type=Text, description="工作经验详情")
    source: str = Field(max_length=50, default="user_upload", description="来源")
    target_job_id: Optional[str] = Field(max_length=100, description="目标职位ID")