# -*- coding: utf-8 -*-
"""
MCP Server：为 LangGraph Agent 提供简历读写、投递记录创建等工具。
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Union

from fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_

from app.agents.resume_format import (
    OPTIMIZED_RESUME_SOURCES,
    build_optimized_resume_title,
    resolve_candidate_name,
    strip_optimized_name_suffix,
    strip_title_job_prefix,
)
from app.models.bootstrap import load_all_models

load_all_models()

logger = logging.getLogger(__name__)
mcp = FastMCP("JobPlatform-Tools")


def _format_resume_content(resume) -> str:
    parts = []
    if resume.name:
        parts.append(f"姓名: {resume.name}")
    if resume.phone:
        parts.append(f"电话: {resume.phone}")
    if resume.email:
        parts.append(f"邮箱: {resume.email}")
    if resume.title:
        parts.append(f"职位: {resume.title}")
    if resume.education:
        parts.append(f"学历: {resume.education}")
    if resume.experience_years is not None:
        parts.append(f"工作年限: {resume.experience_years}")
    if resume.skills:
        skills = resume.skills if isinstance(resume.skills, list) else json.loads(resume.skills)
        parts.append(f"技能: {', '.join(skills)}")
    if resume.summary:
        parts.append(f"个人简介:\n{resume.summary}")
    if resume.work_experience:
        parts.append(f"工作经历:\n{resume.work_experience}")
    if resume.project_experience:
        parts.append(f"项目经验:\n{resume.project_experience}")
    return "\n\n".join(parts) if parts else "暂无简历内容"


def _resolve_job_position_id(db, job_id: Union[int, str]) -> Optional[int]:
    """将 job_id 解析为 job_positions 表的主键 id（支持数字 id 或外部编号如 JOB-001）。"""
    from app.models.job_position import JobPosition

    job_id_str = str(job_id).strip()

    if job_id_str.isdigit():
        job = db.query(JobPosition).filter(JobPosition.id == int(job_id_str)).first()
        if job:
            return job.id

    job = db.query(JobPosition).filter(JobPosition.job_id == job_id_str).first()
    if job:
        return job.id

    return None


def _base_resume_query(db, user_id: int):
    """智能投递优化时只应基于用户原始简历，而非历史优化副本。"""
    from app.models.resume import Resume

    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .filter(
            or_(
                Resume.source.is_(None),
                Resume.source == "user_upload",
                ~Resume.source.in_(list(OPTIMIZED_RESUME_SOURCES)),
            )
        )
        .order_by(Resume.is_default.desc(), Resume.updated_at.desc())
    )


@mcp.tool()
async def get_resume_content(user_id: int) -> dict:
    """根据用户ID获取简历纯文本内容"""
    from app.core.database import SessionLocal
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        resume = _base_resume_query(db, user_id).first()
        if not resume:
            return {"error": "未找到简历", "content": None}

        skills = resume.skills if isinstance(resume.skills, list) else json.loads(resume.skills or "[]")
        clean_name = strip_optimized_name_suffix(resume.name or "")

        return {
            "id": resume.id,
            "name": clean_name,
            "phone": resume.phone or "",
            "email": resume.email or "",
            "title": resume.title or "",
            "education": resume.education or "",
            "experience_years": resume.experience_years,
            "skills": skills,
            "summary": resume.summary or "",
            "work_experience": resume.work_experience or "",
            "project_experience": resume.project_experience or "",
            "content": _format_resume_content(resume),
        }
    except Exception as e:
        logger.error("get_resume_content 失败: %s", e, exc_info=True)
        return {"error": str(e), "content": None}
    finally:
        db.close()


@mcp.tool()
async def save_optimized_resume(
    user_id: int,
    job_id: str,
    resume_data: Dict[str, Any],
    original_name: Optional[str] = None,
) -> Dict[str, Any]:
    """保存 AI 优化后的简历（结构化字段写入对应列）"""
    from app.core.database import SessionLocal
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        from app.models.job_position import JobPosition

        name = resolve_candidate_name(
            resume_data,
            explicit_original_name=original_name,
        )
        logger.info("保存优化简历姓名: %s (original_name=%s)", name, original_name)

        job_pk = _resolve_job_position_id(db, job_id)
        job = db.query(JobPosition).filter(JobPosition.id == job_pk).first() if job_pk else None
        base_title = strip_title_job_prefix(str(resume_data.get("title") or ""))
        if job:
            resume_title = build_optimized_resume_title(
                job.title,
                base_title,
                job.company or "",
            )
        else:
            resume_title = base_title

        skills = resume_data.get("skills") or []
        if isinstance(skills, str):
            skills = json.loads(skills) if skills.startswith("[") else [skills]

        experience_years = resume_data.get("experience_years")
        if isinstance(experience_years, str) and experience_years.isdigit():
            experience_years = int(experience_years)

        new_resume = Resume(
            user_id=user_id,
            name=name,
            phone=resume_data.get("phone") or "",
            email=resume_data.get("email") or "",
            title=resume_title,
            education=resume_data.get("education") or "",
            experience_years=experience_years,
            skills=skills,
            summary=resume_data.get("summary") or "",
            work_experience=resume_data.get("work_experience") or "",
            project_experience=resume_data.get("project_experience") or "",
            source="agent_optimized",
            target_job_id=job_id,
            status="Active",
            is_default=0,
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)

        return {
            "status": "success",
            "message": "简历保存成功",
            "data": {
                "new_resume_id": new_resume.id,
                "resume_title": new_resume.title,
            },
        }
    except Exception as e:
        db.rollback()
        logger.error("save_optimized_resume 失败: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@mcp.tool()
async def create_application_record(
    user_id: Union[int, str],
    job_id: Union[int, str],
    cover_letter: str,
    resume_id: Optional[int] = None,
) -> dict:
    """创建投递记录"""
    from app.core.database import SessionLocal
    from app.models.application import Application

    uid = int(user_id)

    db = SessionLocal()
    try:
        job_id_int = _resolve_job_position_id(db, job_id)
        if job_id_int is None:
            return {"status": "error", "message": f"无效的职位ID: {job_id}"}

        application = Application(
            user_id=uid,
            job_id=job_id_int,
            resume_id=resume_id,
            cover_letter=cover_letter,
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(application)
        db.commit()
        db.refresh(application)

        return {
            "status": "success",
            "id": application.id,
            "application_id": application.id,
        }
    except Exception as e:
        db.rollback()
        logger.error("create_application_record 失败: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@mcp.tool()
async def delete_optimized_resume(resume_id: int) -> dict:
    """删除 AI 生成的优化简历（投递失败时回滚用）"""
    from app.core.database import SessionLocal
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return {"status": "error", "message": "简历不存在"}
        if resume.source != "agent_optimized":
            return {"status": "error", "message": "只能删除 AI 优化简历"}

        db.delete(resume)
        db.commit()
        return {"status": "success", "message": "已删除优化简历"}
    except Exception as e:
        db.rollback()
        logger.error("delete_optimized_resume 失败: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@mcp.tool()
async def get_resume_by_id(resume_id: int) -> dict:
    """根据简历ID获取简历详情"""
    from app.core.database import SessionLocal
    from app.models.resume import Resume

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return {"error": "简历不存在"}

        skills = resume.skills if isinstance(resume.skills, list) else json.loads(resume.skills or "[]")
        clean_name = strip_optimized_name_suffix(resume.name or "")
        return {
            "id": resume.id,
            "name": clean_name,
            "phone": resume.phone,
            "email": resume.email,
            "title": resume.title,
            "education": resume.education,
            "experience_years": resume.experience_years,
            "skills": skills,
            "summary": resume.summary,
            "work_experience": resume.work_experience,
            "project_experience": resume.project_experience,
            "content": _format_resume_content(resume),
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8002"))
    mcp.run(transport="http", host=host, port=port)
