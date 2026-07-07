from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.core import database, deps
from app.crud import crud
from app.models.base import UserDB
from app.models.job_position import JobPosition
from app.rag.vector_store import add_job_to_vectorstore, remove_job_from_vectorstore
from app.schemas.job_schema import JobParseResponse, BatchJobParseResponse
from app.utils.celery_task_status import build_celery_task_status
from app.utils.data_cleaner import clean_skills_data
from app.services.location_service import apply_geocode_to_job


router = APIRouter()


def job_to_dict(job: JobPosition) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "salary": job.salary,
        "required_skills": clean_skills_data(job.required_skills),
        "description": job.description,
        "job_id": job.job_id,
        "location": job.location,
        "work_address": job.work_address,
        "latitude": job.latitude,
        "longitude": job.longitude,
        "experience_requirement": job.experience_requirement,
        "education_requirement": job.education_requirement,
        "mentor_id": job.mentor_id,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }


@router.get("/jobs", response_model=List[dict])
def get_jobs(
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_mentor)
):
    jobs = crud.read_jobs(db, skip=skip, limit=limit, keyword=keyword, mentor_id=current_user.id)
    return [job_to_dict(job) for job in jobs]


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
        title: str = Form(...),
        company: str = Form(...),
        salary: Optional[str] = Form(None),
        required_skills: Optional[str] = Form(None),
        description: str = Form(''),
        job_id: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        work_address: Optional[str] = Form(None),
        experience_requirement: Optional[str] = Form(None),
        education_requirement: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_mentor)
):
    skills = []
    if required_skills:
        try:
            skills = json.loads(required_skills)
        except (json.JSONDecodeError, TypeError):
            pass

    job_data = {
        "title": title,
        "company": company,
        "salary": salary,
        "description": description,
        "job_id": job_id,
        "location": location,
        "work_address": work_address,
        "experience_requirement": experience_requirement,
        "education_requirement": education_requirement,
        "required_skills": skills,
        "mentor_id": current_user.id
    }

    db_job = crud.create_job(db, job_data=job_data)
    apply_geocode_to_job(db_job)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    add_job_to_vectorstore(db_job)
    
    return job_to_dict(db_job)


@router.put("/jobs/{job_id}")
def update_job(
        job_id: int,
        title: Optional[str] = Form(None),
        company: Optional[str] = Form(None),
        salary: Optional[str] = Form(None),
        required_skills: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        job_id_field: Optional[str] = Form(None, alias="job_id"),
        location: Optional[str] = Form(None),
        work_address: Optional[str] = Form(None),
        experience_requirement: Optional[str] = Form(None),
        education_requirement: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_mentor)
):
    db_job = crud.get_job_by_id(db, job_id)
    if not db_job:
        raise HTTPException(status_code=404, detail="职位不存在")

    job_data = {}
    if title is not None:
        job_data["title"] = title
    if company is not None:
        job_data["company"] = company
    if salary is not None:
        job_data["salary"] = salary
    if description is not None:
        job_data["description"] = description
    if job_id_field is not None:
        job_data["job_id"] = job_id_field
    if location is not None:
        job_data["location"] = location
    if work_address is not None:
        job_data["work_address"] = work_address
    if experience_requirement is not None:
        job_data["experience_requirement"] = experience_requirement
    if education_requirement is not None:
        job_data["education_requirement"] = education_requirement

    if required_skills is not None:
        try:
            job_data["required_skills"] = json.loads(required_skills)
        except (json.JSONDecodeError, TypeError):
            pass

    db_job = crud.update_job(db, job_id, job_data)
    if db_job:
        apply_geocode_to_job(db_job)
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
    return job_to_dict(db_job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
        job_id: int,
        db: Session = Depends(database.get_db),
        current_user=Depends(deps.get_current_active_mentor)
):
    success = crud.delete_job(db, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    remove_job_from_vectorstore(job_id)
    
    return None


@router.post("/jobs/parse", response_model=JobParseResponse, deprecated=True)
async def parse_job_document(
        file: UploadFile = File(...),
        current_user: UserDB = Depends(deps.get_current_active_mentor)
):
    """【已废弃】同步职位解析。请使用 POST /jobs/parse/submit + GET /jobs/parse/status/{task_id}"""
    raise HTTPException(
        status_code=410,
        detail="同步职位解析已废弃，请使用 POST /mentor/jobs/parse/submit 与 GET /mentor/jobs/parse/status/{task_id}",
    )


@router.post("/jobs/batch-parse", response_model=BatchJobParseResponse, deprecated=True)
async def batch_parse_job_documents(
        file: UploadFile = File(...),
        current_user: UserDB = Depends(deps.get_current_active_mentor)
):
    """【已废弃】同步批量职位解析。请使用 POST /jobs/parse/submit?is_batch=true"""
    raise HTTPException(
        status_code=410,
        detail="同步批量解析已废弃，请使用 POST /mentor/jobs/parse/submit（is_batch=true）与 GET /mentor/jobs/parse/status/{task_id}",
    )


@router.post("/jobs/parse/submit")
async def submit_parse_task(
    file: UploadFile = File(...),
    is_batch: bool = Form(False),
    current_user: UserDB = Depends(deps.get_current_active_mentor)
):
    if not file.filename.endswith((".pdf", '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="请上传PDF、DOCX或TXT文件")
    
    contents = await file.read()
    filename = file.filename
    
    from app.services.recommendation_service import parse_document_task
    task = parse_document_task.delay(contents, filename, is_batch)
    
    print(f"[HR parse submit] 任务已提交: task_id={task.id}, file={filename}, is_batch={is_batch}")
    return {
        "task_id": task.id,
        "filename": filename,
        "is_batch": is_batch,
        "message": "解析任务已提交，正在后台执行"
    }


@router.get("/jobs/parse/status/{task_id}")
async def get_parse_status(
    task_id: str,
    current_user=Depends(deps.get_current_active_mentor)
):
    return build_celery_task_status(task_id)
