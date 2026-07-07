from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas import user_schema as schemas
from app.core import security, database
from app.core.config import settings
from app.crud import crud

router = APIRouter()


@router.post("/register", response_model=schemas.UserCreate, status_code=status.HTTP_201_CREATED)
def register(
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db),
):
    user = crud.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    if not user_in.tenant_id:
        raise HTTPException(status_code=400, detail="必须选择所属租户")

    return crud.create_user(db, user_in=user_in, tenant_id=user_in.tenant_id)


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    user = crud.get_user_by_username(db, username=form_data.username)

    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员",
        )

    tokens = security.issue_token_pair(user.id)
    return schemas.LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        user=user.model_dump(),
    )


@router.post("/refresh", response_model=schemas.TokenRefreshResponse)
async def refresh_access_token(
    body: schemas.RefreshTokenRequest,
    db: Session = Depends(database.get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="刷新令牌无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security.decode_token(body.refresh_token)
        if payload.get("type") != security.TOKEN_TYPE_REFRESH:
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_id(db, int(user_id)) if hasattr(crud, "get_user_by_id") else None
    if user is None:
        from app.models.user import User
        user = db.get(User, int(user_id))

    if user is None or not user.is_active:
        raise credentials_exception

    access_token = security.create_access_token(
        user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return schemas.TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer",
    )
