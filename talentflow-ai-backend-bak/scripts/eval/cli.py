"""
TalentFlow LangSmith 评测统一入口。

用法（在 talentflow-ai-backend-bak 目录）:
  python scripts/eval/cli.py setup
  python scripts/eval/cli.py import-jobs
  python scripts/eval/cli.py seed --pipeline rag
  python scripts/eval/cli.py smoke --pipeline rag --all
  python scripts/eval/cli.py run --pipeline rag
  python scripts/eval/cli.py run --pipeline smart_apply
  python scripts/eval/cli.py trace --source smart_apply --out datasets/traces_export.json
  python scripts/eval/cli.py analyze --experiment <exp>
  python scripts/eval/cli.py compare --baseline <a> --candidate <b>
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

from core.bootstrap import get_client, require_api_key, setup_paths  # noqa: E402

setup_paths()
import config  # noqa: E402


def _cmd_setup(_args: argparse.Namespace) -> int:
    from core.setup import verify_setup

    return verify_setup()


def _cmd_import_jobs(args: argparse.Namespace) -> int:
    from core.dataset_io import import_eval_jobs

    return import_eval_jobs(sql_only=args.sql_only, index_only=args.index_only)


def _cmd_seed(args: argparse.Namespace) -> int:
    from core.dataset_io import (
        default_golden_path,
        load_golden_file,
        upload_dataset,
        validate_rag_job_ids,
    )

    kind = "rag" if args.pipeline == "rag" else "smart_apply"
    golden_path = Path(args.file) if args.file else default_golden_path(kind)
    if not golden_path.is_absolute():
        golden_path = config.DATASETS_DIR / golden_path

    print("=" * 60)
    print(f"TalentFlow Eval — 上传 Golden Dataset ({args.pipeline})")
    print("=" * 60)

    try:
        name, description, examples = load_golden_file(golden_path, kind=kind)
        print(f"  file       : {golden_path.name}")
        print(f"  dataset    : {name}")
        print(f"  examples   : {len(examples)}")

        if kind == "rag":
            for w in validate_rag_job_ids(examples):
                print(f"  [warn] {w}")

        if args.dry_run:
            for i, ex in enumerate(examples, 1):
                if kind == "rag":
                    exp = ex.get("outputs", {}).get("expected_job_ids", [])
                    print(f"  {i}. {ex['inputs']['query'][:40]}... -> {exp}")
                else:
                    print(f"  {i}. [{ex['inputs']['eval_task']}] {ex['inputs'].get('applicant_name')}")
            print("[dry-run] 未上传 LangSmith")
            return 0

        if not require_api_key():
            print("[FAIL] 未配置 LANGSMITH_API_KEY")
            return 1

        client = get_client()
        from core.dataset_io import get_or_create_dataset

        if args.replace:
            dataset = get_or_create_dataset(client, name, description)
            from core.dataset_io import clear_dataset_examples

            n = clear_dataset_examples(client, str(dataset.id))
            print(f"  [replace] 已删除 {n} 条旧 Example")

        uploaded = upload_dataset(client, name, description, examples, replace=args.replace)
        if uploaded:
            print(f"  [upload] 写入 {uploaded} 条 Example")
        elif not args.replace:
            print("  [skip] Dataset 已有 Example，使用 --replace 覆盖")

        dataset = get_or_create_dataset(client, name, description)
        read_back = list(client.list_examples(dataset_id=str(dataset.id)))
        print(f"\n[OK] LangSmith Dataset「{name}」共 {len(read_back)} 条 Example")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1


def _cmd_smoke(args: argparse.Namespace) -> int:
    if args.pipeline == "rag":
        from pipelines.rag import smoke_rag

        golden = config.DATASETS_DIR / args.file if args.file else None
        return smoke_rag(
            query=args.query,
            top_k=args.top_k,
            run_all=args.all,
            golden_file=golden,
        )

    from pipelines.smart_apply import smoke_smart_apply

    golden = config.DATASETS_DIR / args.file if args.file else None
    return smoke_smart_apply(task=args.task, index=args.index, golden_file=golden)


def _cmd_run(args: argparse.Namespace) -> int:
    from core.runner import run_evaluation

    if args.pipeline == "rag":
        from pipelines.rag import get_evaluators, rag_target

        with_judge = not args.no_judge
        evaluators = get_evaluators(with_judge=with_judge)
        description = (
            "TalentFlow RAG 核心指标（格式+Recall+Precision+Embedding）"
            if not with_judge
            else "TalentFlow RAG 完整评测含 RelevanceScore LLM Judge"
        )
        return run_evaluation(
            rag_target,
            evaluators,
            dataset=args.dataset or config.RAG_DATASET_NAME,
            experiment_prefix=args.prefix
            or os.getenv("EVAL_EXPERIMENT_PREFIX", "talentflow-rag-v1-full"),
            description=description,
            max_concurrency=args.max_concurrency,
            require_judge_key=with_judge,
        )

    from pipelines.smart_apply import get_evaluators, smart_apply_target

    return run_evaluation(
        smart_apply_target,
        get_evaluators(),
        dataset=args.dataset or config.SMART_APPLY_DATASET_NAME,
        experiment_prefix=args.prefix
        or os.getenv("EVAL_SA_EXPERIMENT_PREFIX", "talentflow-smart-apply-v1"),
        description="TalentFlow Smart Apply 生成质量评测",
        max_concurrency=args.max_concurrency,
        require_judge_key=True,
    )


def _cmd_trace(args: argparse.Namespace) -> int:
    from core.traces import export_traces

    return export_traces(
        args.source,
        limit=args.limit,
        experiment=args.experiment,
        out=args.out,
        upload=args.upload,
        dataset=args.dataset,
        dry_run=args.dry_run,
    )


def _cmd_analyze(args: argparse.Namespace) -> int:
    from core.analysis import analyze_badcases

    return analyze_badcases(args.experiment, limit=args.limit, out=args.out)


def _cmd_compare(args: argparse.Namespace) -> int:
    from core.analysis import compare_experiments

    return compare_experiments(args.baseline, args.candidate, out=args.out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="TalentFlow LangSmith 评测 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="阶段 0：LangSmith 连通性验收")

    p_import = sub.add_parser("import-jobs", help="导入 eval 职位种子到 MySQL + FAISS")
    p_import.add_argument("--sql-only", action="store_true")
    p_import.add_argument("--index-only", action="store_true")

    p_seed = sub.add_parser("seed", help="上传 golden set 到 LangSmith")
    p_seed.add_argument("--pipeline", choices=["rag", "smart_apply"], default="rag")
    p_seed.add_argument("--file", type=str, help="datasets/ 下 JSON 文件名或路径")
    p_seed.add_argument("--dry-run", action="store_true")
    p_seed.add_argument("--replace", action="store_true")

    p_smoke = sub.add_parser("smoke", help="单链路冒烟测试")
    p_smoke.add_argument("--pipeline", choices=["rag", "smart_apply"], required=True)
    p_smoke.add_argument("--query", type=str, help="RAG 单条 query")
    p_smoke.add_argument("--top-k", type=int, default=5)
    p_smoke.add_argument("--all", action="store_true", help="RAG：跑 golden set 全部")
    p_smoke.add_argument("--task", default="all", help="Smart Apply：cover_letter / optimize_resume / all")
    p_smoke.add_argument("--index", type=int, default=-1, help="Smart Apply：指定 example 下标")
    p_smoke.add_argument("--file", type=str, help="自定义 golden JSON 文件名")

    p_run = sub.add_parser("run", help="批量 LangSmith 评估实验")
    p_run.add_argument("--pipeline", choices=["rag", "smart_apply"], required=True)
    p_run.add_argument("--prefix", type=str)
    p_run.add_argument("--dataset", type=str)
    p_run.add_argument("--max-concurrency", type=int, default=int(os.getenv("EVAL_MAX_CONCURRENCY", "2")))
    p_run.add_argument("--no-judge", action="store_true", help="RAG：跳过 LLM Judge")

    p_trace = sub.add_parser("trace", help="LangSmith Trace → Dataset Example")
    p_trace.add_argument("--source", choices=["smart_apply", "eval_rag"], required=True)
    p_trace.add_argument("--limit", type=int, default=20)
    p_trace.add_argument("--experiment", type=str)
    p_trace.add_argument("--out", type=str)
    p_trace.add_argument("--upload", action="store_true")
    p_trace.add_argument("--dataset", type=str)
    p_trace.add_argument("--dry-run", action="store_true")

    p_analyze = sub.add_parser("analyze", help="BadCase 分析")
    p_analyze.add_argument("--experiment", required=True)
    p_analyze.add_argument("--limit", type=int, default=100)
    p_analyze.add_argument("--out", type=str)

    p_compare = sub.add_parser("compare", help="实验维度对比")
    p_compare.add_argument("--baseline", required=True)
    p_compare.add_argument("--candidate", required=True)
    p_compare.add_argument("--out", type=str)

    args = parser.parse_args(argv)
    handlers = {
        "setup": _cmd_setup,
        "import-jobs": _cmd_import_jobs,
        "seed": _cmd_seed,
        "smoke": _cmd_smoke,
        "run": _cmd_run,
        "trace": _cmd_trace,
        "analyze": _cmd_analyze,
        "compare": _cmd_compare,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
