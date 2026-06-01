from sqlmodel import SQLModel, Field
from typing import Optional, List


class ActivityItem(SQLModel):
    """单条动态项"""
    date: str = Field(..., description="日期")
    title: str = Field(..., description="动态标题")
    description: str = Field(..., description="动态描述")


class ActivitiesList(SQLModel):
    """动态列表响应"""
    activities: List[ActivityItem] = Field(..., description="动态数据列表")
