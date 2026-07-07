"""RAG 流水线：target + smoke + 评估器注册。"""

from __future__ import annotations

import json
import logging

from core.bootstrap import setup_paths

setup_paths()
import config  # noqa: E402
from evaluators import RAG_EVALUATORS, RAG_EVALUATORS_CORE  # noqa: E402

logger = logging.getLogger(__name__)

GOLDEN_FILE = config.DATASETS_DIR / "talentflow_golden_set_v1.json"


def rag_target(inputs: dict) -> dict:
    from app.core.database import SessionLocal
    from app.rag.retriever import get_hybrid_retriever

    query = (inputs.get("query") or "").strip()
    top_k = int(inputs.get("top_k") or 5)
    if not query:
        return {"results": [], "error": "query 为空"}

    try:
        with SessionLocal() as db:
            candidates = get_hybrid_retriever(db)(query, top_k)
        results = [
            {
                "id": int(item["job_id"]),
                "title": item["job_obj"].title or "",
                "score": float(item["rag_score"]),
                "passage": item.get("passage") or "",
            }
            for item in candidates
        ]
        return {"results": results, "query": query, "top_k": top_k}
    except Exception as exc:
        logger.exception("rag_target 失败: %s", exc)
        return {"results": [], "error": str(exc), "query": query, "top_k": top_k}


def smoke_rag(
    query: str | None = None,
    *,
    top_k: int = 5,
    run_all: bool = False,
    golden_file=None,
) -> int:
    path = golden_file or GOLDEN_FILE

    if run_all:
        if not path.is_file():
            print(f"[FAIL] 找不到 {path}")
            return 1
        examples = json.loads(path.read_text(encoding="utf-8")).get("examples", [])
        ok = 0
        for ex in examples:
            inp, out = ex["inputs"], ex.get("outputs", {})
            if _smoke_one(inp["query"], inp.get("top_k", top_k), out.get("expected_job_ids")):
                ok += 1
        print(f"通过: {ok}/{len(examples)}")
        return 0 if ok == len(examples) else 1

    if not query:
        return 1
    return 0 if _smoke_one(query, top_k, None) else 1


def _smoke_one(query: str, top_k: int, expected_ids: list | None) -> bool:
    print("-" * 60)
    print(f"Query: {query}")
    if expected_ids:
        print(f"Expected: {expected_ids}")

    out = rag_target({"query": query, "top_k": top_k})
    results = out.get("results") or []
    if not results:
        print("[FAIL] 召回为空")
        return False

    retrieved = []
    for i, item in enumerate(results, 1):
        retrieved.append(item["id"])
        print(f"  {i}. id={item['id']} score={item['score']:.4f} | {item['title']}")

    if expected_ids:
        hit = set(retrieved) & set(expected_ids)
        recall = len(hit) / len(expected_ids)
        print(f"Hit: {sorted(hit)} | Recall@{{top_k}} = {recall:.2f}")
        return bool(hit)
    return True


def get_evaluators(*, with_judge: bool = True):
    return RAG_EVALUATORS if with_judge else RAG_EVALUATORS_CORE
