"""LangSmith 自定义评估器（RAG：核心指标 + LLM Judge）。"""

from __future__ import annotations

from evaluators.format_checker import check_rag_format, check_smart_apply_format
from evaluators.llm_judge import llm_judge_rag, llm_judge_smart_apply
from evaluators.recall_precision import precision_at_k, recall_at_k
from evaluators.semantic_similarity import semantic_match_rate, semantic_similarity_avg

# 阶段 2：不含 LLM Judge
RAG_EVALUATORS_CORE = [
    check_rag_format,
    recall_at_k,
    precision_at_k,
    semantic_similarity_avg,
    semantic_match_rate,
]

# 阶段 3：完整 RAG 评测矩阵
RAG_EVALUATORS = RAG_EVALUATORS_CORE + [llm_judge_rag]

SMART_APPLY_EVALUATORS = [
    check_smart_apply_format,
    llm_judge_smart_apply,
]

__all__ = [
    "RAG_EVALUATORS",
    "RAG_EVALUATORS_CORE",
    "check_rag_format",
    "recall_at_k",
    "precision_at_k",
    "semantic_similarity_avg",
    "semantic_match_rate",
    "llm_judge_rag",
    "SMART_APPLY_EVALUATORS",
    "check_smart_apply_format",
    "llm_judge_smart_apply",
]
