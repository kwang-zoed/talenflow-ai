from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import database, deps
from app.models.base import UserDB
from app.schemas.user_profile_schema import UserProfileRead, UserProfileUpdate
from app.services.location_service import apply_geocode_to_profile, get_or_create_user_profile

router = APIRouter()


@router.get("/profile", response_model=UserProfileRead)
def get_profile(
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_user),
):
    profile = get_or_create_user_profile(db, current_user.id)
    return profile


@router.put("/profile", response_model=UserProfileRead)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(database.get_db),
    current_user: UserDB = Depends(deps.get_current_user),
):
    profile = get_or_create_user_profile(db, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    apply_geocode_to_profile(profile)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
