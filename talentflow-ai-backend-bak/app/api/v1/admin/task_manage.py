from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from datetime import datetime, timedelta
import json
import time

from app.core import database, deps
from app.crud import crud
from app.models.task import Task
from app.schemas import task_schema as schemas

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


# ========== ========== 异步版查询类接口 ========== ==========
@router.get("/projects", response_model=List[dict])
async def get_projects(
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_async_db),
    current_user = Depends(deps.get_current_active_admin)
):
    """【异步版】获取任务列表"""
    start_time = time.time()
    print(f"[GET /admin/projects] 异步接口开始")
    
    tasks, total = await crud.read_tasks_async(db, skip=skip, limit=limit, keyword=keyword)
    
    print(f"[GET /admin/projects] 异步接口完成: 耗时={time.time() - start_time:.3f}s, 任务数={len(tasks)}")
    return [task_to_dict(task) for task in tasks]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    task_in: Any = Body(...),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    if hasattr(task_in, 'model_dump'):
        task_data = task_in.model_dump()
    else:
        task_data = dict(task_in)
    
    db_task = crud.create_task(db, task_data, current_user)
    return task_to_dict(db_task)


@router.put("/projects/{project_id}")
def update_project(
    project_id: int,
    task_in: Any = Body(...),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    db_task = crud.get_task_by_id(db, project_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if hasattr(task_in, 'model_dump'):
        task_data = task_in.model_dump(exclude_unset=True)
    else:
        task_data = {k: v for k, v in dict(task_in).items() if v is not None}
    
    db_task = crud.update_task(db, project_id, task_data)
    return task_to_dict(db_task)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    success = crud.delete_task(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return None
