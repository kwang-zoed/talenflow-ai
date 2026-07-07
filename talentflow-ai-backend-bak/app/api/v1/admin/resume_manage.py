from fastapi import APIRouter, Depends, Query, HTTPException, status, Body, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import json
from datetime import datetime

from app.core import database, deps
from app.crud import crud
from app.schemas import resume_schema as schemas
from app.utils.celery_task_status import build_celery_task_status
from app.rag.vector_store import add_resume_to_vectorstore, remove_resume_from_vectorstore

router = APIRouter()


def resume_to_dict(resume) -> dict:
    """将 Resume ORM 对象转换为前端需要的字典格式"""
    # 处理 skills 字段：确保返回数组
    skills = resume.skills
    if isinstance(skills, str):
        try:
            skills = json.loads(skills)
        except (json.JSONDecodeError, TypeError):
            skills = []
    elif not skills:
        skills = []

    # 状态兼容: 前端判断 'Active' (首字母大写) 才显示已激活
    status = resume.status or 'Active'
    if isinstance(status, str):
        status_lower = status.lower()
        if status_lower == 'active':
            status = 'Active'
        elif status_lower == 'archived':
            status = 'Archived'

    return {
        "id": resume.id,
        "name": resume.name,
        "title": resume.title,
        "phone": resume.phone,
        "email": resume.email,
        "education": resume.education,
        "summary": resume.summary,
        "work_experience": resume.work_experience,
        "project_experience": resume.project_experience,
        "skills": skills,
        "status": status,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        "is_default": resume.is_default if hasattr(resume, 'is_default') else 0
    }


# ========== ========== 异步版查询类接口 ========== ==========
@router.get("/resumes")
async def get_resumes(
        page: int = Query(1, description="页码"),
        size: int = Query(10, description="每页条数"),
        q: Optional[str] = Query(None, description="搜索关键词（姓名/职位）"),
        db: AsyncSession = Depends(database.get_async_db),
        current_user=Depends(deps.get_current_active_admin)
):
    """【异步版】获取简历列表 - 管理员端"""
    import time as time_module
    start_time = time_module.time()
    print(f"[GET /admin/resumes] 异步接口开始")
    
    resumes, total = await crud.read_resumes_async(db, page=page, size=size, q=q)
    result = [resume_to_dict(r) for r in resumes]
    
    print(f"[GET /admin/resumes] 异步接口完成: 耗时={time_module.time() - start_time:.3f}s, 简历数={len(result)}")
    return result


@router.get("/resumes/{resume_id}")
async def get_resume_detail(
        resume_id: int,
        db: AsyncSession = Depends(database.get_async_db),
        current_user=Depends(deps.get_current_active_admin)
):
    """【异步版】获取简历详情"""
    from fastapi import HTTPException
    from sqlalchemy import select as sa_select
    from app.models.resume import Resume
    
    result = await db.execute(
        sa_select(Resume).filter(Resume.id == resume_id)
    )
    db_resume = result.scalar_one_or_none()
    
    if not db_resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    return resume_to_dict(db_resume)


@router.post("/resumes", status_code=status.HTTP_201_CREATED)
def create_resume(
        resume_in: dict = Body(...),
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_admin)
):
    """创建简历 - 管理员手动录入"""
    db_resume = crud.create_resume(db, resume_in)
    add_resume_to_vectorstore(db_resume)
    return resume_to_dict(db_resume)


@router.put("/resumes/{resume_id}")
def update_resume(
        resume_id: int,
        resume_in: dict = Body(...),
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_admin)
):
    """更新简历"""
    db_resume = crud.update_resume(db, resume_id, resume_in)
    if not db_resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    add_resume_to_vectorstore(db_resume)
    return resume_to_dict(db_resume)


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
        resume_id: int,
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_admin)
):
    """删除简历"""
    success = crud.delete_resume(db, resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="简历不存在")
    remove_resume_from_vectorstore(resume_id)


@router.post("/resumes/parse", response_model=schemas.ResumeParsed, deprecated=True)
async def parse_resume(
        file: UploadFile = File(...),
        current_user=Depends(deps.get_current_active_admin)
):
    """【已废弃】同步简历解析。请使用 POST /resumes/parse/submit + GET /resumes/parse/status/{task_id}"""
    raise HTTPException(
        status_code=410,
        detail="同步简历解析已废弃，请使用 POST /admin/resumes/parse/submit 与 GET /admin/resumes/parse/status/{task_id}",
    )


@router.post("/resumes/parse/submit")
async def submit_resume_parse_task(
        file: UploadFile = File(...),
        current_user=Depends(deps.get_current_active_admin)
):
    """提交简历解析 Celery 任务"""
    if not file.filename.endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=400, detail="请上传 PDF、DOCX 或 TXT 文件")

    contents = await file.read()
    filename = file.filename

    from app.services.recommendation_service import parse_resume_task

    task = parse_resume_task.delay(contents, filename)
    print(f"[resume parse submit] 任务已提交: task_id={task.id}, file={filename}")
    return {
        "task_id": task.id,
        "filename": filename,
        "message": "简历解析任务已提交，正在后台执行",
    }


@router.get("/resumes/parse/status/{task_id}")
async def get_resume_parse_status(
        task_id: str,
        current_user=Depends(deps.get_current_active_admin)
):
    """轮询简历解析任务状态"""
    return build_celery_task_status(task_id)
