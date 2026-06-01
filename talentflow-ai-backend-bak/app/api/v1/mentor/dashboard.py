from fastapi import APIRouter, Depends

from sqlmodel import Session, select, func
from app.models.task import Task
from app.models.application import Application
from app.models.user import User
from app.core.database import get_db
from app.core import deps
from app.schemas.dashboard_schema import ActivitiesList

router = APIRouter()


@router.get("/dashboard/stats")
def get_mentor_stats(
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    """获取 Mentor 仪表盘统计数据"""
    
    mentor_id = current_user.id
    
    statement_total = select(func.count(Task.id)).where(Task.mentor_id == mentor_id)
    total_tasks = db.execute(statement_total).scalar_one()
    
    statement_in_progress = select(func.count(Task.id)).where(
        Task.mentor_id == mentor_id,
        Task.status == '1'
    )
    in_progress = db.execute(statement_in_progress).scalar_one()
    
    statement_completed = select(func.count(Task.id)).where(
        Task.mentor_id == mentor_id,
        Task.status == '3'
    )
    completed = db.execute(statement_completed).scalar_one()
    
    statement_pending_review = select(func.count(Application.id)).join(
        Task, Application.task_id == Task.id
    ).where(
        Task.mentor_id == mentor_id,
        Application.status == 'pending'
    )
    pending_review = db.execute(statement_pending_review).scalar_one()
    
    return {
        "total_tasks": total_tasks,
        "in_progress": in_progress,
        "pending_review": pending_review,
        "completed": completed
    }

@router.get("/dashboard/activities", response_model=ActivitiesList)
def get_recent_activities(
    db: Session = Depends(get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    """获取最近活动"""
    mentor_id = current_user.id
    activities =  []
    # 获取最新的任务动态（只看当前Mentor自己的）
    statement_tasks = (
        select(Task)
        .where(Task.mentor_id == mentor_id)
        .order_by(Task.updated_at.desc())
        .limit(20)
    )
    tasks = db.execute(statement_tasks).scalars().all()

    for task in tasks:
        status_text = ""
        if task.status == '1':
            status_text = "状态变更为“进行中”"
        elif task.status == '3':
            status_text = "状态变更为“已完成”"

        if status_text:
            activities.append({
                "date": task.updated_at.strftime("%Y-%m-%d"),
                "title": task.title,
                "description": status_text
            })

    statement_apps = (
        select(Application, User)
        .join(User, Application.user_id == User.id)
        .join(Task, Application.task_id == Task.id)
        .where(Task.mentor_id == mentor_id)
        .where(Application.status == 'pending')
        .order_by(Application.updated_at.desc())
        .limit(20)
    )
    app_results = db.execute(statement_apps).all()
    for app, user in app_results:
        statement_task = select(Task).where(Task.id == app.task_id)
        task = db.execute(statement_task).scalar_one_or_none()
        if task:
            user_name = getattr(user, 'username', None) or getattr(user, 'full_name', None) or '用户'
            activities.append({
                "date": app.created_at.strftime("%Y-%m-%d"),
                "title": task.title,
                "description": f"{user_name} 提交了新投递"
            })

    # 合并排序
    activities.sort(key=lambda x: x["date"], reverse=True)
    return {"activities": activities}