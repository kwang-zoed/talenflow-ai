from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional, List
from sqlalchemy import JSON, Column


class JobPosition(SQLModel, table=True):
    __tablename__ = "job_positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    job_id: Optional[str] = Field(
        default=None,
        description="职位编号(可选, 用于外部系统关联)"
    )
    
    title: str = Field(description="职位名称")
    
    company: str = Field(description="公司名称")
    
    salary: Optional[str] = Field(default=None, description="薪资范围")

    location: Optional[str] = Field(
        default=None,
        description="工作地点, 例如: 东莞"
    )
    work_address: Optional[str] = Field(default=None, max_length=255, description="详细工作地址")
    latitude: Optional[float] = Field(default=None, description="纬度")
    longitude: Optional[float] = Field(default=None, description="经度")
    geocoded_at: Optional[datetime] = Field(default=None)
    
    experience_requirement: Optional[str] = Field(
        default=None,
        description="经验要求, 例如: 3-5年"
    )
    
    education_requirement: Optional[str] = Field(
        default=None,
        description="学历要求, 例如: 本科"
    )
    
    required_skills: List[str] = Field(
        default=[],
        sa_column=Column(JSON),
        description="职位要求技能列表"
    )
    
    description: str = Field(description="职位详细描述(用于向量化)")
    
    mentor_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        description="发布职位的HR/导师ID"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    @property
    def skills(self) -> List[str]:
        return self.required_skills

    @skills.setter
    def skills(self, skills: List[str]):
        self.required_skills = skills

    @property
    def salary_range(self) -> Optional[str]:
        return self.salary

    @salary_range.setter
    def salary_range(self, salary: str):
        self.salary = salary