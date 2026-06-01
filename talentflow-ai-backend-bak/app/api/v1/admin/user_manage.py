from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import time

from app.core import database, deps
from app.crud import crud
from app.schemas import user_schema as schemas

router = APIRouter()


def user_to_dict(user) -> dict:
    """将 User 对象转换为字典"""
    if user.role == 0:
        role_label = "求职者"
    elif user.role == 1:
        role_label = "管理员"
    elif user.role == 2:
        role_label = "HR"
    else:
        role_label = "未知"
    
    return {
        "id": user.id,
        "username": user.username,
        "email": getattr(user, 'email', None),
        "full_name": getattr(user, 'full_name', None),
        "role": user.role,
        "role_label": role_label,
        "is_active": getattr(user, 'is_active', True),
        "created_at": getattr(user, 'created_at', None)
    }


# ========== ========== 异步版查询类接口（改造） ========== ==========
@router.get("/users", response_model=List[dict])
async def get_users(
    skip: int = Query(0, description="偏移量"),
    limit: int = Query(10, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(database.get_async_db),
    current_user = Depends(deps.get_current_active_admin)
):
    """【异步版】获取用户列表，支持关键字搜索（用户名/真实姓名）"""
    start_time = time.time()
    print(f"[GET /admin/users] 异步接口开始: 协程ID={id(current_user)}")
    
    users, total = await crud.read_users_async(db, skip=skip, limit=limit, keyword=keyword)
    result = [user_to_dict(user) for user in users]
    
    print(f"[GET /admin/users] 异步接口完成: 耗时={time.time() - start_time:.3f}s, 用户数={len(result)}")
    return result


@router.get("/users/{user_id}", response_model=dict)
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(database.get_async_db),
    current_user = Depends(deps.get_current_active_admin)
):
    """【异步版】获取单个用户详情"""
    start_time = time.time()
    print(f"[GET /admin/users/{user_id}] 异步详情接口开始")
    
    db_user = await crud.get_user_by_id_async(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    print(f"[GET /admin/users/{user_id}] 异步详情接口完成: 耗时={time.time() - start_time:.3f}s")
    return user_to_dict(db_user)


# ========== ========== 命令类接口（暂时保留同步） ========== ==========
@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool = Query(...),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    """更新用户状态（启用/封禁）"""
    db_user = crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if db_user.role == 1 and not is_active:
        raise HTTPException(status_code=403, detail="禁止封禁其他管理员账号")
    
    db_user = crud.update_user_status(db, user_id, is_active)
    return {"message": "状态更新成功", "is_active": is_active}


@router.put("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    """重置用户密码为 123456"""
    db_user = crud.reset_user_password(db, user_id, "123456")
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "密码已重置为 123456"}


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_active_admin)
):
    """更新用户信息"""
    db_user = crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user_data = user_in.model_dump(exclude_unset=True)
    db_user = crud.update_user_info(db, user_id, user_data)
    return user_to_dict(db_user)
