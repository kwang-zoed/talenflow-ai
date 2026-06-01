"""apply_tasks 表 CRUD。"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apply_task import ApplyTask


def create_apply_task(
    db: Session,
    user_id: int,
    job_id: str,
    thread_id: str,
    celery_task_id: str,
) -> ApplyTask:
    row = ApplyTask(
        user_id=user_id,
        job_id=job_id,
        thread_id=thread_id,
        celery_task_id=celery_task_id,
        stage="pending",
        status="running",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_apply_task_stage(
    db: Session,
    apply_task_id: int,
    stage: str,
    status: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    row = db.query(ApplyTask).filter(ApplyTask.id == apply_task_id).first()
    if not row:
        return
    row.stage = stage
    if status:
        row.status = status
    if error is not None:
        row.error = error[:500] if error else None
    row.updated_at = datetime.utcnow()
    db.commit()


def get_apply_task_by_thread(db: Session, thread_id: str, user_id: int) -> Optional[ApplyTask]:
    return (
        db.query(ApplyTask)
        .filter(ApplyTask.thread_id == thread_id, ApplyTask.user_id == user_id)
        .first()
    )


def get_apply_task_by_celery_id(db: Session, celery_task_id: str) -> Optional[ApplyTask]:
    return db.query(ApplyTask).filter(ApplyTask.celery_task_id == celery_task_id).first()


def set_apply_task_celery_id(db: Session, apply_task_id: int, celery_task_id: str) -> None:
    row = db.query(ApplyTask).filter(ApplyTask.id == apply_task_id).first()
    if not row:
        return
    row.celery_task_id = celery_task_id
    row.updated_at = datetime.utcnow()
    db.commit()


def list_apply_tasks(db: Session, user_id: int, limit: int = 20) -> List[ApplyTask]:
    return (
        db.query(ApplyTask)
        .filter(ApplyTask.user_id == user_id)
        .order_by(ApplyTask.updated_at.desc())
        .limit(limit)
        .all()
    )
