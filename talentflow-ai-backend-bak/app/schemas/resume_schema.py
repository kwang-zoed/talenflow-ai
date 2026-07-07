from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Union
from datetime import datetime


# ==================== 基础模型 ====================
class ResumeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    title: Optional[str] = Field(None, max_length=100, description="意向职位")
    education: Optional[str] = Field(None, max_length=50, description="学历背景")
    experience: Optional[str] = Field(None, max_length=50, description="工作经验年限")
    summary: Optional[str] = Field(None, description="个人简介")
    work_experience: Optional[str] = Field(None, description="详细工作经历")
    project_experience: Optional[str] = Field(None, description="项目经验")
    skills: Optional[Union[str, List[str]]] = Field(None, description="技能标签列表")
    status: str = Field("Pending", max_length=20, description="状态: Pending/Active/Archived")
    residence_city: Optional[str] = Field(None, max_length=100, description="常住省市区")
    residence_address: Optional[str] = Field(None, max_length=255, description="详细住址")
    use_profile_location: Optional[int] = Field(1, description="1=继承用户默认所在地")


# ==================== Request 请求模型 ====================

class ResumeCreate(ResumeBase):
    """创建简历 - 请求模型"""
    user_id: int = Field(default=1, description="关联用户ID")
    is_default: Optional[int] = Field(0, description="是否默认简历")
    source: Optional[str] = Field("user_upload", max_length=50, description="来源")
    target_job_id: Optional[str] = Field(None, max_length=100, description="目标职位ID")


class ResumeUpdate(BaseModel):
    """更新简历 - 请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    education: Optional[str] = Field(None, max_length=50)
    experience: Optional[str] = Field(None, max_length=50)
    summary: Optional[str] = Field(None)
    work_experience: Optional[str] = Field(None)
    project_experience: Optional[str] = Field(None)
    skills: Optional[Union[str, List[str]]] = Field(None)
    status: Optional[str] = Field(None, max_length=20)
    is_default: Optional[int] = Field(None)
    residence_city: Optional[str] = Field(None, max_length=100)
    residence_address: Optional[str] = Field(None, max_length=255)
    use_profile_location: Optional[int] = Field(None)


# ==================== Response 响应模型 ====================

class ResumeRead(ResumeBase):
    """简历详情/列表项 - 响应模型"""
    id: int
    user_id: int
    is_default: int
    residence_city: Optional[str] = None
    residence_address: Optional[str] = None
    use_profile_location: Optional[int] = 1
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ResumeParsed(BaseModel):
    """简历文件解析 - 响应模型（回填表单）"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    education: Optional[str] = None
    summary: Optional[str] = None
    work_experience: Optional[str] = None
    project_experience: Optional[str] = None
    skills: List[str] = Field(default_factory=list)


# ==================== HR 投递管理 - 多表联查响应 ====================

class ApplicationRead(BaseModel):
    """投递列表 - HR端"""
    id: int
    candidate_id: int
    candidate_name: str
    job_id: Optional[int]
    job_title: str
    job_skills: Optional[str]
    resume_id: int
    status: str
    applied_at: datetime
    experience_years: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
