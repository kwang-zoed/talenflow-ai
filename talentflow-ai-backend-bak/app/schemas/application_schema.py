from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime


class ApplicationRead(SQLModel):
    """投递记录读取模型"""
    id: int
    type: Optional[str] = Field(None, description="投递类型: task / job")
    resume_id: Optional[int] = Field(None, description="关联简历ID")
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None
    job_skills: Optional[List[str]] = None
    experience_years: Optional[str] = None
    applied_at: Optional[datetime] = None
    status: Optional[str] = None
    source: Optional[str] = Field(None, description="简历附件URL，仅当有真实文件时返回")
    resume_source_type: Optional[str] = Field(None, description="简历来源: user_upload / agent_optimized")
    remark: Optional[str] = None


class ResumePreviewRead(SQLModel):
    """HR 查看投递关联的简历详情"""
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    education: Optional[str] = None
    experience_years: Optional[int] = None
    skills: Optional[List[str]] = None
    summary: Optional[str] = None
    work_experience: Optional[str] = None
    project_experience: Optional[str] = None
    source: Optional[str] = None


class ApplicationProcess(SQLModel):
    """审核处理请求模型"""
    status: str = Field(..., description="处理状态：待沟通/已录用/不合适")
    remark: Optional[str] = Field(None, description="处理备注")
