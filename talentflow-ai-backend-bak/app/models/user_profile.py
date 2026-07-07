from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(unique=True, index=True, description="业务用户ID")
    name: Optional[str] = Field(default=None, max_length=100)
    skills: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    profile_summary: Optional[str] = Field(default=None)
    expected_position: Optional[str] = Field(default=None, max_length=100)
    expected_city: Optional[str] = Field(default=None, max_length=50)
    expected_industry: Optional[str] = Field(default=None, max_length=50)
    min_salary: Optional[int] = Field(default=None)
    job_type: Optional[str] = Field(default=None, max_length=20)
    residence_city: Optional[str] = Field(default=None, max_length=100, description="常住省市区")
    residence_address: Optional[str] = Field(default=None, max_length=255, description="详细住址")
    latitude: Optional[float] = Field(default=None, description="纬度")
    longitude: Optional[float] = Field(default=None, description="经度")
    geocoded_at: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
