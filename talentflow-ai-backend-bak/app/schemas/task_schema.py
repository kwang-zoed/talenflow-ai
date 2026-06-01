from sqlmodel import SQLModel, Field
from typing import Optional, List, Union
from datetime import datetime


class TaskBase(SQLModel):
    title: str = Field(..., description="任务标题", max_length=150)
    description: Optional[str] = Field(None, description="任务描述")
    skills: Optional[Union[str, List[str]]] = Field(None, description="技能要求")
    category: Optional[str] = Field(None, description="分类", max_length=20)
    price: Optional[int] = Field(None, description="悬赏金额")
    duration: Optional[str] = Field(None, description="时长", max_length=20)
    difficulty: Optional[str] = Field("中等", description="难度", max_length=20)
    taken_by: Optional[int] = Field(None, description="接单人ID")
    status: Optional[int] = Field(1, description="状态")


class TaskRead(TaskBase):
    """读取任务时返回的字段"""
    id: int
    created_at: datetime
    updated_at: datetime
    submission_count: Optional[int] = Field(0, description="投稿数")


class TaskCreate(TaskBase):
    """创建任务时的请求体模型"""
    pass


class TaskUpdate(SQLModel):
    """更新任务时的请求体模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[Union[str, List[str]]] = None
    category: Optional[str] = None
    price: Optional[int] = None
    duration: Optional[str] = None
    difficulty: Optional[str] = None
    taken_by: Optional[int] = None
    status: Optional[int] = None
