from typing import TypedDict, Optional, Annotated


def _replace(_old, new):
    """后写入的值直接覆盖旧值（支持 False 覆盖 True）。"""
    return new


class AgentState(TypedDict, total=False):
    user_id: int
    job_id: str
    job_description: str

    resume_content: Annotated[str, lambda x, y: y or x]
    original_resume: Annotated[Optional[dict], lambda x, y: y or x]
    optimized_resume: Annotated[Optional[dict], lambda x, y: y or x]
    applicant_name: Annotated[Optional[str], lambda x, y: y or x]
    resume_id: Annotated[Optional[int], lambda x, y: y or x]

    cover_letter: Annotated[Optional[str], lambda x, y: y or x]
    application_id: Annotated[Optional[int], lambda x, y: y or x]

    error_message: Annotated[Optional[str], lambda x, y: y or x]
    skip_generation: Annotated[bool, _replace]
    resume_saved_in_run: Annotated[bool, _replace]
