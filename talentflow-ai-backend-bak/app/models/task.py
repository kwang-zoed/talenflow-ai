from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional,List

class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=150, description="任务标题")
    description: Optional[str] = Field(description="任务描述")
    skills: Optional[str] = Field(max_length=255, description="技能要求")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")
    category: Optional[str] = Field(max_length=20, description="分类")
    price: Optional[int] = Field(description="悬赏金额")
    duration: Optional[str] = Field(max_length=20, description="时长")
    difficulty: Optional[str] = Field(max_length=20, default="中等", description="难度")
    taken_by: Optional[int] = Field(default=None,foreign_key="users.id",description="接单人ID")
    mentor_id: Optional[int] = Field(default=None,foreign_key="users.id",description="发布者ID")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="更新时间")
    status: Optional[str] = Field(default="1", description="状态")

    mentor: Optional['User'] = Relationship(
        back_populates="tasks",
        sa_relationship_kwargs={"foreign_keys":"[Task.mentor_id]"})

    taker: Optional['User'] = Relationship(
        back_populates="accepted_tasks",
        sa_relationship_kwargs={"foreign_keys":"[Task.taken_by]"})
