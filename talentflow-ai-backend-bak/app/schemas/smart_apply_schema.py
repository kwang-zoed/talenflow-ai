from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ApplyRequest(BaseModel):
    job_id: Optional[Union[str, int]] = Field(
        None,
        description="外部职位编号 job_positions.job_id；无编号时可省略",
    )
    id: Optional[int] = Field(
        None,
        description="职位主键 job_positions.id，当 job_id 为空时使用",
    )
    position_id: Optional[int] = Field(
        None,
        description="同 id，职位主键",
    )
    job_description: str = Field(..., description="职位描述")
    resume_id: Optional[int] = Field(None, description="原始简历ID，可选")
    mode: Literal["auto", "force_generate", "force_reuse"] = Field(
        "auto",
        description="auto: 自动判断; force_generate: 强制AI生成; force_reuse: 强制复用",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_job_identifier(cls, data: Any) -> Any:
        """job_positions.job_id 为空时，允许仅传主键 id / position_id。"""
        if not isinstance(data, dict):
            return data

        raw_job_id = data.get("job_id")
        pk = data.get("position_id")
        if pk is None:
            pk = data.get("id")

        if raw_job_id is None or (isinstance(raw_job_id, str) and not raw_job_id.strip()):
            if pk is not None:
                data["job_id"] = str(int(pk))
        elif isinstance(raw_job_id, int):
            data["job_id"] = str(raw_job_id)
        elif isinstance(raw_job_id, str):
            data["job_id"] = raw_job_id.strip()

        return data

    @model_validator(mode="after")
    def require_job_identifier(self):
        if not self.job_id or not str(self.job_id).strip():
            raise ValueError(
                "缺少职位标识：请传 job_id（职位编号）或 id/position_id（职位主键）"
            )
        object.__setattr__(self, "job_id", str(self.job_id).strip())
        return self


class ApplyResponse(BaseModel):
    success: bool
    message: str
    application_id: Optional[int] = None
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None
    is_reused: bool = False
    error: Optional[str] = None


class SmartApplyCheckItem(BaseModel):
    name: str
    ok: bool
    detail: str


class SmartApplyReadinessResponse(BaseModel):
    ready: bool
    message: str
    checks: list[SmartApplyCheckItem] = Field(default_factory=list)
    langsmith_project: Optional[str] = None
    mcp_url: Optional[str] = None


class SmartApplySubmitResponse(BaseModel):
    task_id: str
    thread_id: str
    message: str
    job_id: str


class SmartApplyTaskStatusResponse(BaseModel):
    status: str
    message: str = ""
    percent: int = 0
    current: Optional[int] = None
    total: Optional[int] = None
    thread_id: Optional[str] = None
    stage: Optional[str] = None
    review_type: Optional[str] = None
    review_message: Optional[str] = None
    data: Optional[ApplyResponse] = None


class SmartApplyResumeResponse(BaseModel):
    status: str
    message: str = ""
    thread_id: str
    stage: Optional[str] = None
    review_type: Optional[str] = None
    review_message: Optional[str] = None
    percent: int = 0
    state: Dict[str, Any] = Field(default_factory=dict)
    data: Optional[ApplyResponse] = None


class ApplyTaskSummary(BaseModel):
    id: int
    job_id: str
    thread_id: str
    celery_task_id: Optional[str] = None
    stage: str
    status: str
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ApplyTaskListResponse(BaseModel):
    tasks: list[ApplyTaskSummary]
    total: int


class SmartApplyThreadStateResponse(BaseModel):
    thread_id: str
    found: bool
    stage: str
    status: str
    percent: int = 0
    next_nodes: list[str] = Field(default_factory=list)
    interrupts: bool = False
    review_type: Optional[str] = None
    review_message: Optional[str] = None
    state: Dict[str, Any] = Field(default_factory=dict)
    celery_task_id: Optional[str] = None
    job_id: Optional[str] = None


class SmartApplyResumeRequest(BaseModel):
    updates: Optional[Dict[str, Any]] = Field(
        None,
        description="人工审核回填字段，如 optimized_resume / cover_letter；为空则从断点直接续跑",
    )
