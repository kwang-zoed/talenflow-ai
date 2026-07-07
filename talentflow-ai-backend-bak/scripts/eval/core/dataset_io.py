"""Golden Dataset 读写、上传、职位种子导入。"""

from __future__ import annotations

import json
from pathlib import Path

from core.bootstrap import setup_paths

setup_paths()
import config  # noqa: E402

DEFAULT_RAG_FILE = "talentflow_golden_set_v1.json"
DEFAULT_SA_FILE = "smart_apply_golden_set_v1.json"
SQL_FILE = config.DATASETS_DIR / "seed_eval_jobs.sql"
EVAL_JOB_ID_PREFIX = "eval-"


def default_golden_path(kind: str) -> Path:
    if kind == "rag":
        return config.DATASETS_DIR / DEFAULT_RAG_FILE
    if kind == "smart_apply":
        return config.DATASETS_DIR / DEFAULT_SA_FILE
    raise ValueError(f"未知 kind: {kind}")


def load_golden_file(path: Path | None = None, *, kind: str = "rag") -> tuple[str, str, list[dict]]:
    golden_path = path or default_golden_path(kind)
    if not golden_path.is_file():
        raise FileNotFoundError(f"找不到数据集文件: {golden_path}")
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    name = data.get("name", config.RAG_DATASET_NAME if kind == "rag" else config.SMART_APPLY_DATASET_NAME)
    description = data.get("description", "")
    examples = data.get("examples", [])
    if not examples:
        raise ValueError("examples 为空")
    return name, description, examples


def validate_rag_job_ids(examples: list[dict]) -> list[str]:
    warnings: list[str] = []
    try:
        from sqlmodel import select
        from app.core.database import SessionLocal
        from app.models.job_position import JobPosition

        all_expected: set[int] = set()
        for ex in examples:
            for jid in ex.get("outputs", {}).get("expected_job_ids", []):
                all_expected.add(int(jid))
        if not all_expected:
            return warnings

        with SessionLocal() as db:
            existing = set(
                db.execute(
                    select(JobPosition.id).where(JobPosition.id.in_(all_expected))
                ).scalars().all()
            )
        missing = sorted(all_expected - existing)
        if missing:
            warnings.append(
                f"以下 expected_job_id 在 DB 中不存在: {missing}。"
                f"请先运行: python scripts/eval/cli.py import-jobs"
            )
    except Exception as exc:
        warnings.append(f"DB 校验跳过（{exc}）")
    return warnings


def get_or_create_dataset(client, name: str, description: str):
    for ds in client.list_datasets(dataset_name=name):
        return ds
    return client.create_dataset(dataset_name=name, description=description)


def clear_dataset_examples(client, dataset_id: str) -> int:
    removed = 0
    for ex in client.list_examples(dataset_id=dataset_id):
        client.delete_example(example_id=ex.id)
        removed += 1
    return removed


def upload_dataset(
    client,
    name: str,
    description: str,
    examples: list[dict],
    *,
    replace: bool = False,
) -> int:
    dataset = get_or_create_dataset(client, name, description)
    if replace:
        clear_dataset_examples(client, str(dataset.id))
        client.create_examples(
            dataset_id=str(dataset.id),
            inputs=[e["inputs"] for e in examples],
            outputs=[e.get("outputs", {}) for e in examples],
        )
        return len(examples)

    existing = list(client.list_examples(dataset_id=str(dataset.id)))
    if existing:
        return 0
    client.create_examples(
        dataset_id=str(dataset.id),
        inputs=[e["inputs"] for e in examples],
        outputs=[e.get("outputs", {}) for e in examples],
    )
    return len(examples)


def run_sql_seed() -> None:
    from sqlalchemy import text
    from app.core.database import engine

    if not SQL_FILE.is_file():
        raise FileNotFoundError(f"找不到 SQL 文件: {SQL_FILE}")
    sql_text = SQL_FILE.read_text(encoding="utf-8")
    statements: list[str] = []
    buf: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buf))
            buf = []
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()
    print(f"[ok] 已执行 SQL 种子: {SQL_FILE.name} ({len(statements)} 条语句)")


def list_eval_jobs(db):
    from sqlmodel import select
    from app.models.job_position import JobPosition

    rows = db.execute(
        select(JobPosition).where(JobPosition.job_id.like(f"{EVAL_JOB_ID_PREFIX}%"))
    ).scalars().all()
    return sorted(rows, key=lambda j: j.id or 0)


def index_eval_jobs(db) -> int:
    from app.rag.vector_store import add_job_to_vectorstore, remove_job_from_vectorstore

    jobs = list_eval_jobs(db)
    if not jobs:
        print("[warn] 未找到 eval- 前缀职位")
        return 0
    indexed = 0
    for job in jobs:
        if job.id is None:
            continue
        remove_job_from_vectorstore(job.id)
        add_job_to_vectorstore(job)
        indexed += 1
        print(f"  [indexed] id={job.id} title={job.title}")
    return indexed


def verify_eval_jobs(db) -> bool:
    jobs = list_eval_jobs(db)
    print(f"[check] eval 职位数量: {len(jobs)}")
    if len(jobs) < 10:
        print("[FAIL] eval 职位不足 10 条")
        return False
    for job in jobs[:3]:
        skills = job.required_skills or []
        print(f"  - id={job.id} {job.title} @ {job.location} skills={skills[:3]}")
    return True


def import_eval_jobs(*, sql_only: bool = False, index_only: bool = False) -> int:
    from app.core.database import SessionLocal

    print("=" * 60)
    print("TalentFlow Eval — 导入评测职位种子")
    print("=" * 60)
    try:
        if not index_only:
            run_sql_seed()
        if sql_only:
            with SessionLocal() as db:
                return 0 if verify_eval_jobs(db) else 1
        with SessionLocal() as db:
            if not verify_eval_jobs(db):
                return 1
            print("[info] 开始写入 FAISS...")
            n = index_eval_jobs(db)
        print(f"\n[OK] 已索引 {n} 条 eval 职位到 FAISS。")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1
