from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core import database, deps
from app.crud import crud
from app.models import base
from app.schemas.resume_schema import ResumeRead, ResumeUpdate, ResumeCreate
from app.services.location_service import apply_geocode_to_resume, get_or_create_user_profile, get_user_profile

router = APIRouter()


@router.get("/resume/list", response_model=List[ResumeRead])
def get_resume_list(
        db: Session = Depends(database.get_db),
        current_user: base.UserDB = Depends(deps.get_current_user)
):
    """获取当前用户的简历列表"""
    print(f"\n{'=' * 60}")
    print(f"[USER RESUME DEBUG] 用户 {current_user.id} 请求获取简历列表")
    
    from app.models.resume import Resume
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    
    print(f"[USER RESUME DEBUG] 查询到 {len(resumes)} 份简历")
    print(f"{'=' * 60}\n")
    
    return resumes


@router.get("/resume/{resume_id}", response_model=ResumeRead)
def get_resume_detail(
        resume_id: int,
        db: Session = Depends(database.get_db),
        current_user: base.UserDB = Depends(deps.get_current_user)
):
    """获取单份简历详情"""
    print(f"\n{'=' * 60}")
    print(f"[USER RESUME DEBUG] 用户 {current_user.id} 请求获取简历 {resume_id}")
    
    from app.models.resume import Resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        print(f"[USER RESUME DEBUG] 简历不存在或无权限")
        print(f"{'=' * 60}\n")
        raise HTTPException(status_code=404, detail="简历不存在或无权限")
    
    print(f"[USER RESUME DEBUG] 成功获取简历: {resume.name}")
    print(f"{'=' * 60}\n")
    return resume


@router.post("/resume", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(
        resume_data: ResumeCreate,
        db: Session = Depends(database.get_db),
        current_user: base.UserDB = Depends(deps.get_current_user)
):
    """创建新简历"""
    print(f"\n{'=' * 60}")
    print(f"[USER RESUME DEBUG] 用户 {current_user.id} 创建新简历")
    
    create_dict = resume_data.model_dump()
    create_dict['user_id'] = current_user.id
    if 'experience' in create_dict and create_dict.get('experience') is not None:
        try:
            create_dict['experience_years'] = int(str(create_dict.pop('experience')).replace('年', '').strip() or 0)
        except ValueError:
            create_dict.pop('experience', None)

    db_resume = crud.create_resume(db, create_dict)
    apply_geocode_to_resume(db_resume)
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    add_resume_to_vectorstore(db_resume)
    
    print(f"[USER RESUME DEBUG] 简历创建成功, ID: {db_resume.id}")
    print(f"{'=' * 60}\n")
    return db_resume


@router.put("/resume/{resume_id}", response_model=ResumeRead)
def update_resume(
        resume_id: int,
        resume_data: ResumeUpdate,
        db: Session = Depends(database.get_db),
        current_user: base.UserDB = Depends(deps.get_current_user)
):
    """更新简历信息"""
    print(f"\n{'=' * 60}")
    print(f"[USER RESUME DEBUG] 用户 {current_user.id} 更新简历 {resume_id}")
    
    from app.models.resume import Resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        print(f"[USER RESUME DEBUG] 简历不存在或无权限")
        print(f"{'=' * 60}\n")
        raise HTTPException(status_code=404, detail="简历不存在或无权限")
    
    update_data = resume_data.model_dump(exclude_unset=True)
    if 'experience' in update_data and update_data.get('experience') is not None:
        try:
            update_data['experience_years'] = int(str(update_data.pop('experience')).replace('年', '').strip() or 0)
        except ValueError:
            update_data.pop('experience', None)
    print(f"[USER RESUME DEBUG] 更新字段: {list(update_data.keys())}")
    
    db_updated = crud.update_resume(db, resume_id, update_data)
    if db_updated:
        apply_geocode_to_resume(db_updated)
        db.add(db_updated)
        db.commit()
        db.refresh(db_updated)
        add_resume_to_vectorstore(db_updated)
    
    print(f"[USER RESUME DEBUG] 简历更新成功")
    print(f"{'=' * 60}\n")
    return db_updated


@router.delete("/resume/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
        resume_id: int,
        db: Session = Depends(database.get_db),
        current_user: base.UserDB = Depends(deps.get_current_user)
):
    """删除简历"""
    print(f"\n{'=' * 60}")
    print(f"[USER RESUME DEBUG] 用户 {current_user.id} 删除简历 {resume_id}")
    
    from app.models.resume import Resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        print(f"[USER RESUME DEBUG] 简历不存在或无权限")
        print(f"{'=' * 60}\n")
        raise HTTPException(status_code=404, detail="简历不存在或无权限")
    
    success = crud.delete_resume(db, resume_id)
    if success:
        remove_resume_from_vectorstore(resume_id)
        print(f"[USER RESUME DEBUG] 简历删除成功")
    print(f"{'=' * 60}\n")
    return None


@router.post("/resume/default")
def set_default_resume(
        data: dict = Body(...),
        db: Session = Depends(database.get_db),
        current_user: base.UserDB = Depends(deps.get_current_user)
):
    """设置默认简历"""
    print(f"\n{'=' * 60}")
    resume_id = data.get('resume_id')
    print(f"[USER RESUME DEBUG] 用户 {current_user.id} 设置默认简历 {resume_id}")
    
    from app.models.resume import Resume
    
    db.query(Resume).filter(Resume.user_id == current_user.id).update({"is_default": 0})
    
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        print(f"[USER RESUME DEBUG] 简历不存在或无权限")
        print(f"{'=' * 60}\n")
        raise HTTPException(status_code=404, detail="简历不存在或无权限")
    
    resume.is_default = 1
    db.commit()
    
    print(f"[USER RESUME DEBUG] 默认简历设置成功")
    print(f"{'=' * 60}\n")
    return {"message": "设置成功"}
