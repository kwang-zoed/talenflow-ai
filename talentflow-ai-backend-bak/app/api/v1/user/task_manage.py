from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import json

from app.core import database, deps
from app.crud import crud
from app.models.task import Task

router = APIRouter()


def is_task_expired(task: Task) -> bool:
    if not task.created_at or not task.duration:
        return False
    try:
        duration_days = int(float(task.duration))
        deadline = task.created_at + timedelta(days=duration_days)
        now = datetime.utcnow()
        is_expired = now > deadline
        
        task_status = str(task.status) if task.status else "0"
        if task_status == "5":
            task_status = "1"
        
        not_finished = task_status not in ["3", "4"]
        return is_expired and not_finished
    except (ValueError, TypeError):
        return False


def parse_skills(skills_str) -> list:
    if not skills_str:
        return []
    if isinstance(skills_str, list):
        return skills_str
    if isinstance(skills_str, str):
        try:
            return json.loads(skills_str)
        except (json.JSONDecodeError, TypeError):
            return [s.strip() for s in skills_str.split(',') if s.strip()]
    return []


def task_to_dict(task: Task) -> dict:
    display_status = int(task.status) if task.status else 0
    if display_status == 5:
        display_status = 1
    if is_task_expired(task):
        display_status = 5
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "skills": parse_skills(task.skills),
        "category": task.category,
        "price": task.price,
        "duration": task.duration,
        "difficulty": task.difficulty,
        "taken_by": task.taken_by,
        "status": display_status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "submission_count": 0
    }


@router.get("/")
def get_user_tasks(
    category: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_user)
):
    query = db.query(Task)
    
    if category:
        query = query.filter(Task.category == category)
    
    tasks = query.all()
    return {
        "items": [task_to_dict(task) for task in tasks],
        "total": len(tasks)
    }


@router.get("/{task_id}")
def get_user_task_detail(
    task_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_user)
):
    task = crud.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_to_dict(task)


@router.post("/{task_id}/apply")
def apply_user_task(
    task_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_user)
):
    from app.models.application import Application
    
    task = crud.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    existing = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.task_id == task_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="已申请过该任务")
    
    application = Application(
        user_id=current_user.id,
        task_id=task_id,
        status="pending"
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return {"message": "申请成功", "application_id": application.id}
