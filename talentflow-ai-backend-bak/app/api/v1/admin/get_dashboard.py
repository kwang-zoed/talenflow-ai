from typing import List, Dict
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from app.core.database import get_async_db
from app.models.base import UserDB
from app.models.job_position import JobPosition
from app.models.resume import Resume
from app.core.deps import get_current_active_admin

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_active_admin)
):
    """获取首页关键指标卡片数据"""
    user_count = (await db.execute(select(func.count(UserDB.id)))).scalar_one_or_none()
    job_count = (await db.execute(select(func.count(JobPosition.id)))).scalar_one_or_none()
    resume_count = (await db.execute(select(func.count(Resume.id)))).scalar_one_or_none()
    pending_resume_count = (
        await db.execute(
            select(func.count(Resume.id)).where(Resume.status == "pending")
        )
    ).scalar_one_or_none()

    return {
        "users": user_count or 0,
        "jobs": job_count or 0,
        "resumes": resume_count or 0,
        "pending_resumes": pending_resume_count or 0,
    }


@router.get("/resume-trend")
async def get_resume_trend(
    days: int = 7,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_active_admin)
):
    """获取简历增长趋势数据（用于折线图）"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    query = (
        select(
            func.date(Resume.created_at).label("date"),
            func.count(Resume.id).label("count"),
        )
        .where(Resume.created_at >= start_date)
        .group_by(func.date(Resume.created_at))
        .order_by(func.date(Resume.created_at))
    )

    results = (await db.execute(query)).all()

    return [{"date": str(row.date), "count": row.count} for row in results]


@router.get("/job-distribution")
async def get_job_distribution(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_active_admin)
):
    """获取职位地点分布数据（用于饼图）"""
    query = (
        select(
            JobPosition.location.label("name"),
            func.count(JobPosition.id).label("value"),
        )
        .group_by(JobPosition.location)
    )

    results = (await db.execute(query)).all()

    return [
        {"name": row.name or "不限", "value": row.value}
        for row in results
    ]
