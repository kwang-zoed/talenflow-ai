from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
from datetime import timedelta
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.schemas import user_schema as schemas
from app.core import security, database
from app.models import base
from app.core.config import settings
from app.crud import crud

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=schemas.UserCreate, status_code=status.HTTP_201_CREATED)
def register(
        user_in: schemas.UserCreate,
        db: Session = Depends(database.get_db)
):
    user = crud.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="用户名已存在",
        )

    if not user_in.tenant_id:
        raise HTTPException(status_code=400, detail="必须选择所属租户")

    user = crud.create_user(db, user_in=user_in, tenant_id=user_in.tenant_id)

    return user


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(database.get_db)
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

    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=30)
    )

    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.model_dump()
    )
