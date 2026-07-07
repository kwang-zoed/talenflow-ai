"""Recall@K / Precision@K 检索准确性评估。"""

from __future__ import annotations

import config
from evaluators._common import get_outputs


def _extract_retrieved_ids(run_outputs: dict, k: int) -> list[int]:
    results = run_outputs.get("results") or []
    ids: list[int] = []
    for item in results[:k]:
        if isinstance(item, dict) and item.get("id") is not None:
            ids.append(int(item["id"]))
    return ids


def _extract_expected_ids(example_outputs: dict) -> list[int]:
    raw = example_outputs.get("expected_job_ids") or []
    return [int(x) for x in raw]


def recall_at_k(run, example) -> dict:
    k = config.EVAL_RECALL_K
    run_out = get_outputs(run)
    exp_out = get_outputs(example)
    expected = _extract_expected_ids(exp_out)

    if not expected:
        return {
            "key": "recall_at_k",
            "score": 0,
            "comment": "expected_job_ids 为空，跳过",
        }

    retrieved = _extract_retrieved_ids(run_out, k)
    hit = set(retrieved) & set(expected)
    score = len(hit) / len(expected)

    return {
        "key": "recall_at_k",
        "score": score,
        "comment": f"K={k} hit={sorted(hit)} expected={expected} retrieved={retrieved}",
    }


def precision_at_k(run, example) -> dict:
    k = config.EVAL_PRECISION_K
    run_out = get_outputs(run)
    exp_out = get_outputs(example)
    expected = _extract_expected_ids(exp_out)

    if not expected:
        return {
            "key": "precision_at_k",
            "score": 0,
            "comment": "expected_job_ids 为空，跳过",
        }

    retrieved = _extract_retrieved_ids(run_out, k)
    if not retrieved:
        return {
            "key": "precision_at_k",
            "score": 0,
            "comment": f"K={k} 检索结果为空",
        }

    hit = set(retrieved) & set(expected)
    score = len(hit) / k

    return {
        "key": "precision_at_k",
        "score": score,
        "comment": f"K={k} hit={sorted(hit)} expected={expected} retrieved={retrieved}",
    }
