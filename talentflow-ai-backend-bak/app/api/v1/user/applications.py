from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import cast, or_, String
from typing import List

from app.core import database, deps
from app.models.application import Application
from app.models.task import Task
from app.models.job_position import JobPosition

router = APIRouter()


def _job_position_join_condition():
    """applications.job_id 可能存主键 id（smart-apply）或外部编号（历史数据）。"""
    return or_(
        Application.job_id == JobPosition.id,
        cast(Application.job_id, String) == JobPosition.job_id,
    )


def status_to_display(status_db: str) -> str:
    """将数据库状态转为前端展示的中文状态"""
    if not status_db:
        return "待沟通"
    status_map = {
        "pending": "待沟通",
        "hired": "已录用",
        "rejected": "不合适"
    }
    return status_map.get(status_db.lower(), status_db if status_db in ["待沟通", "已录用", "不合适"] else "待沟通")


def build_user_app_response(app: Application, task: Task = None, job: JobPosition = None) -> dict:
    """构建用户端投递响应结构"""
    if job:
        title = job.title
        target_type = "职位"
    elif task:
        title = task.title
        target_type = "任务"
    else:
        title = "未知"
        target_type = "未知"
    
    skills = []
    if task and task.skills:
        task_skills = str(task.skills)
        skills = [s.strip() for s in task_skills.split(',') if s.strip()]
    elif job and job.required_skills:
        if isinstance(job.required_skills, list):
            skills = [str(s).strip() for s in job.required_skills if s and str(s).strip()]
        else:
            skills_raw = str(job.required_skills)
            skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
    
    return {
        "id": app.id,
        "title": title,
        "type": target_type,
        "skills": skills,
        "applied_at": app.created_at,
        "status": status_to_display(app.status),
        "remark": getattr(app, 'remark', None)
    }


@router.get("/applications", response_model=List[dict])
def get_my_applications(
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """用户: 获取自己的所有投递记录"""
    user_id = current_user.id
    
    query = (
        db.query(Application, Task, JobPosition)
        .outerjoin(Task, Application.task_id == Task.id)
        .outerjoin(JobPosition, _job_position_join_condition())
        .filter(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )
    
    results = query.all()
    
    response = []
    for app, task, job in results:
        response.append(build_user_app_response(app, task, job))
    
    return response
