from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from typing import List, Optional
from datetime import datetime

from app.core import database, deps
from app.models.application import Application
from app.models.task import Task
from app.models.user import User
from app.models.resume import Resume
from app.models.job_position import JobPosition
from app.schemas.application_schema import ApplicationRead, ApplicationProcess, ResumePreviewRead

router = APIRouter()


def _job_position_join_condition():
    return or_(
        Application.job_id == JobPosition.id,
        cast(Application.job_id, String) == JobPosition.job_id,
    )


def _is_admin_user(user) -> bool:
    role = user.role
    return str(role) in ("1", "admin") or role == 1


def _resume_attachment_url(resume: Resume = None) -> Optional[str]:
    """仅当 source 字段本身是可访问的文件 URL 时才返回。"""
    if not resume or not resume.source:
        return None
    value = str(resume.source).strip()
    if value.startswith(("http://", "https://", "/uploads/")):
        return value
    return None


def _candidate_display_name(user: User, resume: Resume = None) -> str:
    if resume and resume.name and str(resume.name).strip():
        return str(resume.name).strip()
    return getattr(user, "full_name", None) or getattr(user, "username", None) or "用户"


def _format_experience_years(resume: Resume = None) -> str:
    """返回纯数字年限，由前端拼接「年经验」展示。"""
    if not resume or resume.experience_years is None:
        return ""
    return str(resume.experience_years)


def _parse_resume_skills(resume: Resume = None) -> list:
    if not resume or not resume.skills:
        return []
    skills_raw = resume.skills
    if isinstance(skills_raw, list):
        return [str(s).strip() for s in skills_raw if s and str(s).strip()]
    try:
        import json
        parsed = json.loads(skills_raw)
        if isinstance(parsed, list):
            return [str(s).strip() for s in parsed if s and str(s).strip()]
    except Exception:
        pass
    return [s.strip() for s in str(skills_raw).split(",") if s.strip()]


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


def status_to_db(status_display: str) -> str:
    """将前端中文状态转为数据库存储状态"""
    status_map = {
        "待沟通": "pending",
        "已录用": "hired",
        "不合适": "rejected"
    }
    return status_map.get(status_display, "pending")


def build_task_app_response(app: Application, task: Task, user: User, resume: Resume = None) -> dict:
    """构建任务投递的响应结构"""
    display_experience = _format_experience_years(resume)
    
    display_skills = []
    if resume and resume.skills:
        skills_raw = resume.skills
        if isinstance(skills_raw, list):
            display_skills = [str(s).strip() for s in skills_raw if s and str(s).strip()]
        elif isinstance(skills_raw, str):
            try:
                import json
                parsed = json.loads(skills_raw)
                if isinstance(parsed, list):
                    display_skills = [str(s).strip() for s in parsed if s and str(s).strip()]
                else:
                    display_skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
            except (json.JSONDecodeError, TypeError):
                display_skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
    elif task and task.skills:
        task_skills = str(task.skills)
        display_skills = [s.strip() for s in task_skills.split(',') if s.strip()]
    
    return {
        "id": app.id,
        "type": "task",
        "resume_id": app.resume_id,
        "candidate_name": _candidate_display_name(user, resume),
        "job_title": task.title if task else "",
        "job_skills": display_skills,
        "experience_years": display_experience,
        "applied_at": app.created_at,
        "status": status_to_display(app.status),
        "source": _resume_attachment_url(resume),
        "resume_source_type": resume.source if resume else None,
        "remark": getattr(app, 'remark', None)
    }


def build_job_app_response(app: Application, job: JobPosition, user: User, resume: Resume = None) -> dict:
    """构建职位投递的响应结构"""
    display_experience = _format_experience_years(resume)
    
    display_skills = []
    if resume and resume.skills:
        skills_raw = resume.skills
        if isinstance(skills_raw, list):
            display_skills = [str(s).strip() for s in skills_raw if s and str(s).strip()]
        elif isinstance(skills_raw, str):
            try:
                import json
                parsed = json.loads(skills_raw)
                if isinstance(parsed, list):
                    display_skills = [str(s).strip() for s in parsed if s and str(s).strip()]
                else:
                    display_skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
            except (json.JSONDecodeError, TypeError):
                display_skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
    elif job and job.required_skills:
        if isinstance(job.required_skills, list):
            display_skills = [str(s).strip() for s in job.required_skills if s and str(s).strip()]
        else:
            skills_raw = str(job.required_skills)
            display_skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
    
    return {
        "id": app.id,
        "type": "job",
        "resume_id": app.resume_id,
        "candidate_name": _candidate_display_name(user, resume),
        "job_title": job.title if job else "",
        "job_skills": display_skills,
        "experience_years": display_experience,
        "applied_at": app.created_at,
        "status": status_to_display(app.status),
        "source": _resume_attachment_url(resume),
        "resume_source_type": resume.source if resume else None,
        "remark": getattr(app, 'remark', None)
    }


@router.get("/applications", response_model=List[ApplicationRead])
def get_applications(
    type: Optional[str] = Query(None, description="筛选类型: task-任务投递, job-职位投递, 默认全部"),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    """HR: 获取自己的投递记录，支持按类型筛选"""
    mentor_id = current_user.id
    response = []
    
    if type is None or type == 'task':
        task_query = (
            db.query(Application, Task, User, Resume)
            .join(Task, Application.task_id == Task.id)
            .join(User, Application.user_id == User.id)
            .outerjoin(Resume, Application.resume_id == Resume.id)
            .filter(Application.job_id.is_(None))
        )
        if not _is_admin_user(current_user):
            task_query = task_query.filter(Task.mentor_id == mentor_id)
        task_query = task_query.order_by(Application.created_at.desc())
        task_results = task_query.all()
        for app, task, user, resume in task_results:
            response.append(build_task_app_response(app, task, user, resume))
    
    if type is None or type == 'job':
        job_query = (
            db.query(Application, JobPosition, User, Resume)
            .join(JobPosition, _job_position_join_condition())
            .join(User, Application.user_id == User.id)
            .outerjoin(Resume, Application.resume_id == Resume.id)
            .filter(Application.task_id.is_(None))
        )
        if not _is_admin_user(current_user):
            job_query = job_query.filter(JobPosition.mentor_id == mentor_id)
        job_query = job_query.order_by(Application.created_at.desc())
        job_results = job_query.all()
        for app, job, user, resume in job_results:
            response.append(build_job_app_response(app, job, user, resume))
    
    response.sort(key=lambda x: x['applied_at'], reverse=True)
    return response


def _get_application_for_mentor(db: Session, app_id: int, mentor_id: int, allow_admin: bool):
    task_query = (
        db.query(Application, Task, User, Resume)
        .join(Task, Application.task_id == Task.id)
        .join(User, Application.user_id == User.id)
        .outerjoin(Resume, Application.resume_id == Resume.id)
        .filter(Application.id == app_id)
    )
    if not allow_admin:
        task_query = task_query.filter(Task.mentor_id == mentor_id)
    result = task_query.first()
    if result:
        return result

    job_query = (
        db.query(Application, JobPosition, User, Resume)
        .join(JobPosition, _job_position_join_condition())
        .join(User, Application.user_id == User.id)
        .outerjoin(Resume, Application.resume_id == Resume.id)
        .filter(Application.id == app_id)
        .filter(Application.task_id.is_(None))
    )
    if not allow_admin:
        job_query = job_query.filter(JobPosition.mentor_id == mentor_id)
    return job_query.first()


@router.get("/applications/{app_id}", response_model=ApplicationRead)
def get_application_detail(
    app_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    """HR: 获取单条投递详情"""
    result = _get_application_for_mentor(
        db, app_id, current_user.id, _is_admin_user(current_user)
    )
    if not result:
        raise HTTPException(status_code=404, detail="投递记录不存在或无权查看")

    app, first, user, resume = result
    if app.task_id:
        return build_task_app_response(app, first, user, resume)
    return build_job_app_response(app, first, user, resume)


@router.get("/applications/{app_id}/resume", response_model=ResumePreviewRead)
def get_application_resume(
    app_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor),
):
    """HR: 查看投递关联的简历内容（结构化数据，非文件下载）"""
    result = _get_application_for_mentor(
        db, app_id, current_user.id, _is_admin_user(current_user)
    )
    if not result:
        raise HTTPException(status_code=404, detail="投递记录不存在或无权查看")

    app, _, _, resume = result
    if not resume:
        raise HTTPException(status_code=404, detail="该投递未关联简历")

    return ResumePreviewRead(
        id=resume.id,
        name=resume.name,
        phone=resume.phone,
        email=resume.email,
        title=resume.title,
        education=resume.education,
        experience_years=resume.experience_years,
        skills=_parse_resume_skills(resume),
        summary=resume.summary,
        work_experience=resume.work_experience,
        project_experience=resume.project_experience,
        source=resume.source,
    )


@router.patch("/applications/{app_id}/process")
def process_application(
    app_id: int,
    process_data: ApplicationProcess,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    """HR: 审核处理投递记录"""
    mentor_id = current_user.id
    
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    
    has_permission = False
    if app.task_id:
        task = db.query(Task).filter(Task.id == app.task_id, Task.mentor_id == mentor_id).first()
        has_permission = task is not None
    elif app.job_id:
        job = db.query(JobPosition).filter(JobPosition.id == app.job_id, JobPosition.mentor_id == mentor_id).first()
        has_permission = job is not None
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="无权处理该投递记录")
    
    app.status = status_to_db(process_data.status)
    if process_data.remark:
        app.remark = process_data.remark
    app.updated_at = datetime.now()
    
    db.commit()
    db.refresh(app)
    
    return {
        "success": True,
        "message": "处理成功",
        "data": {
            "id": app.id,
            "status": status_to_display(app.status),
            "remark": app.remark,
            "updated_at": app.updated_at
        }
    }
