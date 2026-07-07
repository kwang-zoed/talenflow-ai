from pydantic import BaseModel, Field
from typing import List, Optional, Any


class JobRecommendRequest(BaseModel):
    user_id: int
    top_k: int = Field(5, ge=1, le=20, description="返回推荐数量")


class JobRecommendItem(BaseModel):
    job_id: Optional[int] = None
    id: Optional[int] = None
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: Optional[List[str]] = None
    employment_type: Optional[str] = None
    is_active: Optional[bool] = None
    
    rag_score: Optional[float] = None
    skill_score: Optional[float] = None
    final_score: Optional[float] = None
    rerank_score: Optional[float] = None
    distance_km: Optional[float] = None
    distance_text: Optional[str] = None
    candidate_city: Optional[str] = None
    job_location: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobRecommendResponse(BaseModel):
    data: List[Any]
    count: int


class ResumeRecommendRequest(BaseModel):
    job_id: int
    top_k: int = Field(5, ge=1, le=20, description="返回推荐数量")


class ResumeRecommendItem(BaseModel):
    resume_id: Optional[int] = None
    name: Optional[str] = None
    title: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = None
    score: Optional[int] = None
    matched_skills: Optional[List[str]] = None
    rag_score: Optional[float] = None
    skill_score: Optional[float] = None
    final_score: Optional[float] = None
    distance_km: Optional[float] = None
    distance_text: Optional[str] = None
    candidate_city: Optional[str] = None
    job_location: Optional[str] = None

    class Config:
        from_attributes = True


class ResumeRecommendResponse(BaseModel):
    data: List[Any]
    count: int
