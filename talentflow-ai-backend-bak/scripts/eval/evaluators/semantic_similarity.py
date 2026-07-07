"""Embedding 语义相似度评估（BGE 余弦相似度）。"""

from __future__ import annotations

import config
from app.rag.embeddings import embed_query
from evaluators._common import get_inputs, get_outputs


def _cosine(a: list[float], b: list[float]) -> float:
    # embed_query 已 normalize，点积即余弦相似度
    return float(sum(x * y for x, y in zip(a, b)))


def _query_text(run, example) -> str:
    run_in = get_inputs(run)
    ex_in = get_inputs(example)
    return (run_in.get("query") or ex_in.get("query") or "").strip()


def _passages(run_outputs: dict) -> list[str]:
    passages: list[str] = []
    for item in run_outputs.get("results") or []:
        if not isinstance(item, dict):
            continue
        passage = (item.get("passage") or item.get("title") or "").strip()
        if passage:
            passages.append(passage)
    return passages


def semantic_similarity_avg(run, example) -> dict:
    run_out = get_outputs(run)
    query = _query_text(run, example)
    passages = _passages(run_out)

    if not query:
        return {"key": "semantic_similarity_avg", "score": 0, "comment": "query 为空"}
    if not passages:
        return {"key": "semantic_similarity_avg", "score": 0, "comment": "无 passage 可比较"}

    q_vec = embed_query(query)
    sims = [_cosine(q_vec, embed_query(p)) for p in passages]
    avg = sum(sims) / len(sims)

    return {
        "key": "semantic_similarity_avg",
        "score": avg,
        "comment": f"Top-{len(sims)} 平均余弦相似度={avg:.4f}",
    }


def semantic_match_rate(run, example) -> dict:
    run_out = get_outputs(run)
    query = _query_text(run, example)
    passages = _passages(run_out)
    threshold = config.EVAL_SEMANTIC_THRESHOLD

    if not query or not passages:
        return {"key": "semantic_match_rate", "score": 0, "comment": "query 或 passage 为空"}

    q_vec = embed_query(query)
    sims = [_cosine(q_vec, embed_query(p)) for p in passages]
    matched = sum(1 for s in sims if s >= threshold)
    rate = matched / len(sims)

    return {
        "key": "semantic_match_rate",
        "score": rate,
        "comment": f"阈值={threshold} 命中 {matched}/{len(sims)} 条",
    }
