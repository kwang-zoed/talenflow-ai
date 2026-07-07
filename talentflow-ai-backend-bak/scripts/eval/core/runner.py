"""langsmith.evaluate 通用执行器。"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from core.bootstrap import ensure_langsmith_env, get_client, require_api_key, setup_paths

setup_paths()
import config  # noqa: E402


def run_evaluation(
    target: Callable[[dict], dict],
    evaluators: Sequence[Callable],
    *,
    dataset: str,
    experiment_prefix: str,
    description: str,
    max_concurrency: int = 2,
    require_judge_key: bool = False,
) -> int:
    if not require_api_key():
        print("[FAIL] 未配置 LANGSMITH_API_KEY")
        return 1

    if require_judge_key and not config.EVAL_JUDGE_API_KEY.strip():
        print("[FAIL] 未配置 EVAL_JUDGE_API_KEY / API_KEY")
        return 1

    ensure_langsmith_env()
    client = get_client()
    experiment_name = f"{experiment_prefix}-{datetime.now():%Y%m%d}"

    print("=" * 60)
    print("TalentFlow Eval — 批量评估")
    print("=" * 60)
    print(f"  dataset         : {dataset}")
    print(f"  experiment      : {experiment_name}")
    print(f"  evaluators      : {[getattr(e, '__name__', str(e)) for e in evaluators]}")
    print(f"  max_concurrency : {max_concurrency}")
    print("-" * 60)

    try:
        from langsmith import evaluate

        results = evaluate(
            target,
            data=dataset,
            evaluators=list(evaluators),
            experiment_prefix=experiment_prefix,
            max_concurrency=max_concurrency,
            client=client,
            description=description,
        )
        print()
        print("[OK] 评估实验已完成。")
        if hasattr(results, "experiment_name"):
            print(f"     Experiment: {results.experiment_name}")
        print(f"     LangSmith → Datasets → {dataset} → Experiments")
        return 0
    except Exception as exc:
        print(f"[FAIL] 评估运行失败: {exc}")
        import traceback

        traceback.print_exc()
        return 1
