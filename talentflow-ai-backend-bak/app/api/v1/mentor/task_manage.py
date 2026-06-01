from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional, Any
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
        "mentor": task.mentor_id,
        "status": display_status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "submission_count": 0
    }


@router.get("/tasks")
def get_mentor_tasks(
    title: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    tasks, total = crud.read_tasks(db, skip=skip, limit=limit, keyword=title, mentor_id=current_user.id)
    return {
        "items": [task_to_dict(task) for task in tasks],
        "total": total
    }


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_mentor_task(
    task_in: Any = Body(...),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    if hasattr(task_in, 'model_dump'):
        task_data = task_in.model_dump()
    else:
        task_data = dict(task_in)
    
    db_task = crud.create_task(db, task_data, current_user)
    return task_to_dict(db_task)


@router.put("/tasks/{task_id}")
def update_mentor_task(
    task_id: int,
    task_in: Any = Body(...),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    db_task = crud.get_task_by_id(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if hasattr(task_in, 'model_dump'):
        task_data = task_in.model_dump(exclude_unset=True)
    else:
        task_data = {k: v for k, v in dict(task_in).items() if v is not None}
    
    db_task = crud.update_task(db, task_id, task_data)
    return task_to_dict(db_task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mentor_task(
    task_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_mentor)
):
    success = crud.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return None
