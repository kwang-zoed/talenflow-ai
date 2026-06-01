from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime


class JobBase(SQLModel):
    title: str = Field(..., description="职位名称")
    job_id: Optional[str] = Field(None, description="职位编号")
    company: str = Field(..., description="公司名称")
    salary: Optional[str] = Field(None, description="薪资范围")
    location: Optional[str] = Field(None, description="工作地点，例如：东莞")
    experience_requirement: Optional[str] = Field(None, description="经验要求，例如：3-5年")
    education_requirement: Optional[str] = Field(None, description="学历要求，例如：本科")
    required_skills: Optional[List[str]] = Field(default_factory=list, description="技能标签")
    description: Optional[str] = Field(None, description="职位详情描述")


class JobRead(JobBase):
    """读取职位时返回的字段（包含ID、路径和时间戳）"""
    id: int
    pdf_path: Optional[str] = Field(None, description="PDF文件存储路径")
    mentor_id: Optional[int] = Field(None, description="发布职位的HR/导师ID")
    created_at: datetime


class JobCreate(JobBase):
    """创建职位时的请求体模型"""
    pass


class JobUpdate(SQLModel):
    """更新职位时的请求体模型"""
    title: Optional[str] = None
    job_id: Optional[str] = None
    company: Optional[str] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: Optional[List[str]] = None
    description: Optional[str] = None


class JobParseResponse(SQLModel):
    """解析职位文档时的响应体模型"""
    title: str = Field(..., description="职位名称")
    job_id: Optional[str] = Field(None, description="职位编号")
    company: str = Field(..., description="公司名称")
    salary: Optional[str] = Field(None, description="薪资范围")
    location: Optional[str] = Field(None, description="工作地点，例如：东莞")
    experience_requirement: Optional[str] = Field(None, description="经验要求，例如：3-5年")
    education_requirement: Optional[str] = Field(None, description="学历要求，例如：本科")
    required_skills: Optional[List[str]] = Field(default_factory=list, description="技能标签")
    description: Optional[str] = Field(None, description="职位详情描述")


class BatchJobParseResponse(SQLModel):
    """批量解析职位文档时的响应体模型 - 统一数据校验"""
    total: int = Field(..., description="解析到的职位总数")
    is_batch: bool = Field(True, description="是否批量解析")
    jobs: List[JobParseResponse] = Field(..., description="解析后的职位列表")
