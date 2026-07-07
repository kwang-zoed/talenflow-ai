from fastapi import Depends,HTTPException,status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.models import user as user_model
from sqlalchemy import select
from jose import jwt
from app.core import security,database
from app.core.config import settings

# 定义OAuth2认证方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 获取当前用户
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(database.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type != security.TOKEN_TYPE_ACCESS:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.execute(
        select(user_model.User).where(user_model.User.id == int(user_id))
    ).scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user

# 获取当前活跃用户
async def get_current_active_user(current_user: user_model.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员"
        )
    return current_user

# 获取当前活跃的管理员用户
def get_current_active_admin(current_user: user_model.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员"
        )
    role = current_user.role
    if str(role) != '1' and role != 'admin' and role != 1:
        raise HTTPException(status_code=403, detail="权限不足：仅管理员可操作")
    return current_user


# 获取当前活跃的HR/Mentor用户
def get_current_active_mentor(current_user: user_model.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员"
        )
    role = current_user.role
    is_mentor = (str(role) == '2' or role == 'hr' or role == 2 or 
                  str(role) == '1' or role == 'admin' or role == 1)
    if not is_mentor:
        raise HTTPException(status_code=403, detail="权限不足：仅HR/管理员可操作")
    return current_user