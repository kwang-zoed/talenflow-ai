from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserProfileBase(BaseModel):
    residence_city: Optional[str] = Field(None, max_length=100, description="常住省市区")
    residence_address: Optional[str] = Field(None, max_length=255, description="详细住址")
    expected_city: Optional[str] = Field(None, max_length=50, description="期望工作城市")


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileRead(UserProfileBase):
    id: int
    user_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocoded_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
