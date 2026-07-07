"""LangSmith Trace → Dataset Example 转化。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.bootstrap import get_client, require_api_key, setup_paths
from core.dataset_io import upload_dataset

setup_paths()
import config  # noqa: E402


def _trace_project() -> str:
    from app.core.config import settings

    return (settings.LANGSMITH_PROJECT or "talentflow-smart-apply").strip()


def _fetch_resume_text(user_id: int) -> str | None:
    try:
        from app.core.database import SessionLocal
        from app.services.recommendation_service import RecommendationService

        with SessionLocal() as db:
            svc = RecommendationService(db)
            resume = svc.get_user_resume(user_id)
            if not resume:
                return None
            return svc.extract_user_resume_info(resume).get("search_text")
    except Exception:
        return None


def _fetch_job_description(job_id: str) -> str | None:
    try:
        from app.core.database import SessionLocal
        from app.models.job_position import JobPosition

        with SessionLocal() as db:
            job = db.get(JobPosition, int(job_id))
            if not job:
                return None
            skills = " ".join(job.required_skills or [])
            return (
                f"{job.title} @ {job.company}\n地点: {job.location}\n技能: {skills}\n"
                f"{job.description or ''}"
            ).strip()
    except Exception:
        return None


def _extract_smart_apply_example(run) -> dict | None:
    inputs = run.inputs or {}
    outputs = run.outputs or {}
    meta = (run.extra or {}).get("metadata") or getattr(run, "metadata", None) or {}
    user_id = meta.get("user_id") if isinstance(meta, dict) else None
    job_id = meta.get("job_id") if isinstance(meta, dict) else None
    user_id = user_id or inputs.get("user_id")
    job_id = job_id or inputs.get("job_id")

    job_description = inputs.get("job_description") or ""
    if not job_description and job_id:
        job_description = _fetch_job_description(str(job_id)) or ""

    resume_content = inputs.get("resume_content") or ""
    if not resume_content and user_id:
        resume_content = _fetch_resume_text(int(user_id)) or ""

    if not job_description or not resume_content:
        return None

    cover_letter = None
    if isinstance(outputs, dict):
        cover_letter = outputs.get("cover_letter") or outputs.get("outputs", {}).get("cover_letter")

    return {
        "inputs": {
            "eval_task": "cover_letter",
            "applicant_name": inputs.get("applicant_name") or "求职者",
            "resume_content": resume_content[:2000],
            "job_description": job_description[:2000],
            "trace_run_id": str(run.id),
            "trace_source": "langsmith_smart_apply",
        },
        "outputs": {
            "must_mention_keywords": [],
            "quality_rubric": "来自真实 Trace，需人工补充 keywords 与 rubric",
            "reference_cover_letter": (cover_letter or "")[:500] if cover_letter else None,
        },
    }


def _extract_rag_example(run) -> dict | None:
    inputs = run.inputs or {}
    outputs = run.outputs or {}
    query = (inputs.get("query") or "").strip()
    if not query:
        return None
    top_ids = [
        int(item["id"])
        for item in (outputs.get("results") or [])[:5]
        if isinstance(item, dict) and item.get("id") is not None
    ]
    if not top_ids:
        return None
    return {
        "inputs": {
            "query": query,
            "top_k": int(inputs.get("top_k") or 5),
            "trace_run_id": str(run.id),
            "trace_source": "langsmith_eval_rag",
        },
        "outputs": {
            "expected_job_ids": top_ids[:2],
            "keywords": [],
            "annotation_note": "Top-2 自动预标注，需人工复审",
        },
    }


def collect_traces(
    client,
    source: str,
    *,
    limit: int = 20,
    experiment: str | None = None,
) -> list[dict]:
    examples: list[dict] = []
    seen: set[str] = set()

    if source == "smart_apply":
        project = _trace_project()
        print(f"  [smart_apply] project={project} limit={limit}")
        runs = client.list_runs(
            project_name=project,
            run_type="chain",
            is_root=True,
            limit=limit,
            filter='eq(status, "success")',
        )
        extract = _extract_smart_apply_example
        key_fn = lambda ex: ex["inputs"].get("job_description", "")[:80]
    else:
        if not experiment:
            raise ValueError("eval_rag 需指定 experiment")
        print(f"  [eval_rag] experiment={experiment} limit={limit}")
        runs = client.list_runs(project_name=experiment, is_root=True, limit=limit)
        extract = _extract_rag_example
        key_fn = lambda ex: ex["inputs"]["query"]

    for run in runs:
        ex = extract(run)
        if not ex:
            continue
        k = key_fn(ex)
        if k in seen:
            continue
        seen.add(k)
        examples.append(ex)
    return examples


def export_traces(
    source: str,
    *,
    limit: int = 20,
    experiment: str | None = None,
    out: str | None = None,
    upload: bool = False,
    dataset: str | None = None,
    dry_run: bool = False,
) -> int:
    if not require_api_key():
        print("[FAIL] 未配置 LANGSMITH_API_KEY")
        return 1

    print("=" * 60)
    print("TalentFlow Eval — Trace 转化")
    print("=" * 60)

    client = get_client()
    try:
        examples = collect_traces(client, source, limit=limit, experiment=experiment)
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print(f"  转化成功: {len(examples)} 条")
    if not examples:
        print("[WARN] 无可用 Trace")
        return 0

    for i, ex in enumerate(examples, 1):
        preview = (
            ex["inputs"].get("applicant_name", "?")
            if source == "smart_apply"
            else ex["inputs"].get("query", "?")[:50]
        )
        print(f"  {i}. {preview}")

    if dry_run:
        print("[dry-run] 未写入")
        return 0

    if out:
        payload = {"source": source, "count": len(examples), "examples": examples}
        Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] 已写入 {out}")

    if upload:
        if not dataset:
            print("[FAIL] upload 需 --dataset")
            return 1
        upload_dataset(
            client, dataset, f"Trace 追加 {len(examples)} 条", examples, replace=False
        )
        print(f"[OK] 已追加到 Dataset「{dataset}」")

    if not out and not upload:
        print("提示: 使用 --out 或 --upload 持久化")
    return 0
