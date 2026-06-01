from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from datetime import datetime
from app.schemas import user_schema as schemas
from app.core import security
from app.models import base
from sqlalchemy.orm import Session as SQLASession
from app.models import user as user_model
from app.models.job_position import JobPosition
from app.models.task import Task
from sqlalchemy import or_


def get_user_by_username(db: SQLASession, username: str):
    return db.query(user_model.User).filter(user_model.User.username == username).first()

def create_user(db: Session, user_in: schemas.UserCreate, tenant_id: int):
    hashed_password = security.get_password_hash(user_in.password)
    db_user = base.UserDB(
        username=user_in.username,
        password=hashed_password,
        tenant_id=tenant_id,
        role=0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
 
def get_user_by_id(db: Session, user_id: int):
    return db.query(user_model.User).filter(user_model.User.id == user_id).first()


# ==================== Job CRUD ====================

def read_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    mentor_id: Optional[int] = None
) -> List[JobPosition]:
    """获取职位列表，支持关键字搜索和mentor_id过滤"""
    query = db.query(JobPosition)
    if keyword:
        query = query.filter(
            or_(
                JobPosition.title.contains(keyword),
                JobPosition.company.contains(keyword)
            )
        )
    if mentor_id is not None:
        query = query.filter(JobPosition.mentor_id == mentor_id)
    return query.offset(skip).limit(limit).all()


def create_job(db: Session, job_data: dict) -> JobPosition:
    """创建职位"""
    db_job = JobPosition(
        title=job_data.get('title'),
        company=job_data.get('company'),
        job_id=job_data.get('job_id'),
        salary=job_data.get('salary'),
        location=job_data.get('location'),
        experience_requirement=job_data.get('experience_requirement'),
        education_requirement=job_data.get('education_requirement'),
        required_skills=job_data.get('required_skills', []),
        description=job_data.get('description', ''),
        mentor_id=job_data.get('mentor_id')
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def get_job_by_id(db: Session, job_id: int) -> Optional[JobPosition]:
    """根据ID获取职位"""
    return db.query(JobPosition).filter(JobPosition.id == job_id).first()


def update_job(db: Session, job_id: int, job_data: dict) -> Optional[JobPosition]:
    """更新职位"""
    db_job = get_job_by_id(db, job_id)
    if not db_job:
        return None
    
    for field, value in job_data.items():
        if value is not None and hasattr(db_job, field):
            setattr(db_job, field, value)
    
    db_job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_job)
    return db_job


def delete_job(db: Session, job_id: int) -> bool:
    """删除职位"""
    db_job = get_job_by_id(db, job_id)
    if not db_job:
        return False
    db.delete(db_job)
    db.commit()
    return True


# ==================== Task CRUD ====================

def read_tasks(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    mentor_id: Optional[int] = None
) -> Tuple[List[Task], int]:
    """获取任务列表，支持关键字搜索和mentor_id过滤，返回 (任务列表, 总数)"""
    query = db.query(Task)
    if keyword:
        query = query.filter(Task.title.contains(keyword))
    if mentor_id is not None:
        query = query.filter(Task.mentor_id == mentor_id)
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    return tasks, total


def get_task_by_id(db: Session, task_id: int) -> Optional[Task]:
    """根据ID获取任务"""
    return db.query(Task).filter(Task.id == task_id).first()


def parse_status(status_val) -> int:
    """确保 status 始终是整数"""
    if status_val is None or status_val == '':
        return 1
    if isinstance(status_val, int):
        return status_val
    if isinstance(status_val, str):
        if status_val.isdigit():
            return int(status_val)
        status_map = {'active': 1, 'pending': 0, 'paused': 2, 'completed': 3}
        return status_map.get(status_val.lower(), 1)
    return 1


def create_task(db: Session, task_data: dict,current_user) -> Task:
    """创建任务"""
    skills = task_data.get('skills')
    if isinstance(skills, list):
        import json
        skills = json.dumps(skills, ensure_ascii=False)
    
    status = parse_status(task_data.get('status'))
    
    db_task = Task(
        title=task_data.get('title'),
        description=task_data.get('description'),
        skills=skills,
        category=task_data.get('category'),
        price=task_data.get('price'),
        duration=task_data.get('duration'),
        difficulty=task_data.get('difficulty', '中等'),
        taken_by=task_data.get('taken_by'),
        mentor_id=current_user.id,
        status=status
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task_id: int, task_data: dict) -> Optional[Task]:
    """更新任务"""
    db_task = get_task_by_id(db, task_id)
    if not db_task:
        return None
    
    skills = task_data.get('skills')
    if isinstance(skills, list):
        import json
        task_data['skills'] = json.dumps(skills, ensure_ascii=False)
    
    if 'status' in task_data:
        task_data['status'] = parse_status(task_data['status'])
    
    for field, value in task_data.items():
        if value is not None and hasattr(db_task, field):
            setattr(db_task, field, value)
    
    if hasattr(db_task, 'updated_at'):
        db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> bool:
    """删除任务"""
    db_task = get_task_by_id(db, task_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True


# ==================== User Admin CRUD ====================

def read_users(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    keyword: Optional[str] = None
) -> Tuple[List[user_model.User], int]:
    """获取用户列表，支持关键字搜索，返回 (列表, 总数)"""
    query = db.query(user_model.User)
    
    if keyword:
        query = query.filter(
            or_(
                user_model.User.username.contains(keyword),
                user_model.User.full_name.contains(keyword) if hasattr(user_model.User, 'full_name') else False
            )
        )
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return users, total


def update_user_status(db: Session, user_id: int, is_active: bool) -> Optional[user_model.User]:
    """更新用户状态"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    if not db_user:
        return None
    db_user.is_active = is_active
    db.commit()
    db.refresh(db_user)
    return db_user


def reset_user_password(db: Session, user_id: int, new_password: str = "123456") -> Optional[user_model.User]:
    """重置用户密码"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    if not db_user:
        return None
    
    from app.core import security
    db_user.password = security.get_password_hash(new_password)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: int) -> Optional[user_model.User]:
    """根据ID获取用户"""
    return db.query(user_model.User).filter(user_model.User.id == user_id).first()


def update_user_info(db: Session, user_id: int, user_data: dict) -> Optional[user_model.User]:
    """更新用户信息"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    for field, value in user_data.items():
        if value is not None and hasattr(db_user, field) and field != 'password':
            setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


# ==================== Resume CRUD ====================

def read_resumes(
    db: Session,
    page: int = 1,
    size: int = 10,
    q: Optional[str] = None
) -> Tuple[List, int]:
    """获取简历列表，支持搜索（姓名/技能）"""
    from app.models.resume import Resume
    
    query = db.query(Resume)
    
    if q:
        query = query.filter(
            or_(
                Resume.name.contains(q),
                Resume.title.contains(q)
            )
        )
    
    total = query.count()
    skip = (page - 1) * size
    resumes = query.offset(skip).limit(size).all()
    return resumes, total


def get_resume_by_id(db: Session, resume_id: int):
    """根据ID获取简历"""
    from app.models.resume import Resume
    return db.query(Resume).filter(Resume.id == resume_id).first()


def create_resume(db: Session, resume_data: dict):
    """创建新简历"""
    from app.models.resume import Resume
    import json
    
    # 处理 skills: 数组转 JSON 字符串
    if 'skills' in resume_data and isinstance(resume_data['skills'], list):
        resume_data['skills'] = json.dumps(resume_data['skills'])
    
    db_resume = Resume(**resume_data)
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume


def update_resume(db: Session, resume_id: int, resume_data: dict):
    """更新简历"""
    from app.models.resume import Resume
    import json
    
    db_resume = get_resume_by_id(db, resume_id)
    if not db_resume:
        return None
    
    for field, value in resume_data.items():
        if value is not None and hasattr(db_resume, field):
            # skills 特殊处理
            if field == 'skills' and isinstance(value, list):
                value = json.dumps(value)
            setattr(db_resume, field, value)
    
    db.commit()
    db.refresh(db_resume)
    return db_resume


def delete_resume(db: Session, resume_id: int) -> bool:
    """删除简历"""
    from app.models.resume import Resume
    
    db_resume = get_resume_by_id(db, resume_id)
    if not db_resume:
        return False
    
    db.delete(db_resume)
    db.commit()
    return True


# ========== ========== 异步 CRUD 函数（新增） ========== ==========
from sqlalchemy import select as sa_select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession as DBAsyncSession
import time


async def get_user_by_id_async(db: DBAsyncSession, user_id: int):
    """异步版：根据ID获取用户"""
    print(f"[crud async] 开始查询用户 {user_id}")
    start_time = time.time()
    
    result = await db.execute(
        sa_select(user_model.User).filter(user_model.User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    print(f"[crud async] 查询用户 {user_id} 完成，耗时: {time.time() - start_time:.3f}s")
    return user


async def read_users_async(
    db: DBAsyncSession,
    skip: int = 0,
    limit: int = 10,
    keyword: str = None
):
    """异步版：获取用户列表，支持关键字搜索"""
    print(f"[crud async] 开始查询用户列表: skip={skip}, limit={limit}, keyword={keyword}")
    start_time = time.time()
    
    query = sa_select(user_model.User)
    
    if keyword:
        query = query.filter(
            or_(
                user_model.User.username.contains(keyword),
                user_model.User.full_name.contains(keyword)
            )
        )
    
    # Count 查询
    count_stmt = sa_select(sa_func.count()).select_from(query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # 分页查询
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    
    print(f"[crud async] 查询用户列表完成: {len(users)} users, 耗时: {time.time() - start_time:.3f}s")
    return list(users), total


async def read_jobs_async(
    db: DBAsyncSession,
    skip: int = 0,
    limit: int = 100,
    keyword: str = None,
    mentor_id: int = None
):
    """异步版：获取职位列表"""
    print(f"[crud async] 开始查询职位列表")
    start_time = time.time()
    
    query = sa_select(JobPosition)
    
    if keyword:
        query = query.filter(
            or_(
                JobPosition.title.contains(keyword),
                JobPosition.company.contains(keyword)
            )
        )
    
    if mentor_id is not None:
        query = query.filter(JobPosition.mentor_id == mentor_id)
    
    result = await db.execute(query.offset(skip).limit(limit))
    jobs = result.scalars().all()
    
    print(f"[crud async] 查询职位列表完成: {len(jobs)} jobs, 耗时: {time.time() - start_time:.3f}s")
    return list(jobs)


async def get_job_by_id_async(db: DBAsyncSession, job_id: int):
    """异步版：根据ID获取职位"""
    result = await db.execute(
        sa_select(JobPosition).filter(JobPosition.id == job_id)
    )
    return result.scalar_one_or_none()


async def read_tasks_async(
    db: DBAsyncSession,
    skip: int = 0,
    limit: int = 100,
    keyword: str = None,
    mentor_id: int = None
):
    """异步版：获取任务列表"""
    print(f"[crud async] 开始查询任务列表")
    start_time = time.time()
    
    query = sa_select(Task)
    
    if keyword:
        query = query.filter(Task.title.contains(keyword))
    
    if mentor_id is not None:
        query = query.filter(Task.mentor_id == mentor_id)
    
    # Count
    count_stmt = sa_select(sa_func.count()).select_from(query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # 分页
    result = await db.execute(query.offset(skip).limit(limit))
    tasks = result.scalars().all()
    
    print(f"[crud async] 查询任务列表完成: {len(tasks)} tasks, 耗时: {time.time() - start_time:.3f}s")
    return list(tasks), total


async def get_task_by_id_async(db: DBAsyncSession, task_id: int):
    """异步版：根据ID获取任务"""
    result = await db.execute(
        sa_select(Task).filter(Task.id == task_id)
    )
    return result.scalar_one_or_none()


async def read_resumes_async(
    db: DBAsyncSession,
    page: int = 1,
    size: int = 10,
    q: str = None
):
    """异步版：获取简历列表"""
    from app.models.resume import Resume
    
    query = sa_select(Resume)
    
    if q:
        query = query.filter(
            or_(
                Resume.name.contains(q),
                Resume.title.contains(q)
            )
        )
    
    # Count
    count_stmt = sa_select(sa_func.count()).select_from(query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()
    
    # 分页
    skip = (page - 1) * size
    result = await db.execute(query.offset(skip).limit(size))
    resumes = result.scalars().all()
    
    return list(resumes), total