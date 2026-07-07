"""RAG 评测输出 Pydantic 契约。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RagResultItem(BaseModel):
    id: int
    title: str
    score: float = Field(description="混合检索 rag_score")


class RagEvalOutput(BaseModel):
    results: list[RagResultItem]
