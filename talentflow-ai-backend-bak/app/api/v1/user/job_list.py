from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core import database, deps
from app.models.job_position import JobPosition
from app.crud import crud

router = APIRouter()


def parse_skills(skills) -> list:
    import json
    if not skills:
        return []
    if isinstance(skills, list):
        return skills
    if isinstance(skills, str):
        try:
            return json.loads(skills)
        except (json.JSONDecodeError, TypeError):
            return [s.strip() for s in skills.split(',') if s.strip()]
    return []


def job_to_dict(job: JobPosition) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "salary": job.salary,
        "required_skills": parse_skills(job.required_skills),
        "description": job.description,
        # 无外部编号时回退主键，避免智能投递请求体 job_id 为 null 导致 422
        "job_id": job.job_id if job.job_id else str(job.id),
        "location": job.location,
        "experience_requirement": job.experience_requirement,
        "education_requirement": job.education_requirement,
        "mentor_id": job.mentor_id,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }


@router.get("/job-list", response_model=List[dict])
def get_job_list(
    keyword: Optional[str] = Query(None, description="职位关键词搜索"),
    category: Optional[str] = Query(None, description="职位分类筛选"),
    db: Session = Depends(database.get_db),
    current_user=Depends(deps.get_current_active_user)
):
    """用户端：获取所有公开职位列表（可投递简历的职位大厅）"""
    jobs = crud.read_jobs(db, skip=0, limit=100, keyword=keyword)
    return [job_to_dict(job) for job in jobs]