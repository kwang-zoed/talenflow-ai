"""Smart Apply 评测输出契约。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class OptimizedResumeEvalOutput(BaseModel):
    name: str = Field(min_length=1)
    phone: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    summary: Optional[str] = ""
    work_experience: Optional[str] = ""
    project_experience: Optional[str] = ""
