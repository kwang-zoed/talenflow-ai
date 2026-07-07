"""BadCase 分析与实验对比。"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from core.bootstrap import get_client, require_api_key, setup_paths

setup_paths()

RAG_BAD_RECALL = 1.0
RAG_BAD_RELEVANCE = 0.6
SA_BAD_JUDGE = 1.0


def fetch_run_feedbacks(client, experiment: str, limit: int = 100):
    runs = list(client.list_runs(project_name=experiment, is_root=True, limit=limit))
    run_map = {str(r.id): r for r in runs}
    run_ids = list(run_map.keys())
    feedbacks_by_run: dict[str, list] = defaultdict(list)
    if run_ids:
        for fb in client.list_feedback(run_ids=run_ids):
            feedbacks_by_run[str(fb.run_id)].append(fb)
    return run_map, feedbacks_by_run


def summarize_averages(feedbacks_by_run: dict) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for fbs in feedbacks_by_run.values():
        for fb in fbs:
            if fb.score is not None and fb.key:
                buckets[fb.key].append(float(fb.score))
    return {k: sum(v) / len(v) for k, v in buckets.items()}


def _is_bad(fb) -> bool:
    key = fb.key or ""
    score = fb.score
    if score is None:
        return False
    if key == "recall_at_k" and score < RAG_BAD_RECALL:
        return True
    if key == "relevance_score" and score < RAG_BAD_RELEVANCE:
        return True
    if key == "relevance_pass" and score < 1:
        return True
    if key in ("letter_quality_judge", "resume_quality_judge") and score < SA_BAD_JUDGE:
        return True
    if key == "valid_format" and score < 1:
        return True
    return False


def analyze_badcases(experiment: str, *, limit: int = 100, out: str | None = None) -> int:
    if not require_api_key():
        print("[FAIL] 未配置 LANGSMITH_API_KEY")
        return 1

    print("=" * 60)
    print(f"BadCase 分析 — {experiment}")
    print("=" * 60)

    client = get_client()
    run_map, feedbacks_by_run = fetch_run_feedbacks(client, experiment, limit)
    stats_lists: dict[str, list[float]] = defaultdict(list)
    for fbs in feedbacks_by_run.values():
        for fb in fbs:
            if fb.score is not None and fb.key:
                stats_lists[fb.key].append(float(fb.score))

    print("\n【维度均分】")
    for key, scores in sorted(stats_lists.items()):
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {key:28s} n={len(scores):3d}  avg={avg:.4f}")

    badcases: list[dict] = []
    for run_id, fbs in feedbacks_by_run.items():
        bad_fbs = [fb for fb in fbs if _is_bad(fb)]
        if not bad_fbs:
            continue
        run = run_map.get(run_id)
        inputs = (run.inputs if run else {}) or {}
        badcases.append(
            {
                "run_id": run_id,
                "inputs_preview": str(inputs)[:200],
                "issues": [
                    {"key": fb.key, "score": fb.score, "comment": (fb.comment or "")[:300]}
                    for fb in bad_fbs
                ],
            }
        )

    print(f"\n【BadCase 数量】 {len(badcases)} / {len(run_map)}")
    for i, bc in enumerate(badcases[:10], 1):
        keys = ", ".join(f"{x['key']}={x['score']}" for x in bc["issues"])
        print(f"  {i}. run={bc['run_id'][:8]}... | {keys}")
    if not badcases:
        print("  未发现低分样本。")

    if out:
        report = {
            "experiment": experiment,
            "total_runs": len(run_map),
            "badcase_count": len(badcases),
            "averages": summarize_averages(feedbacks_by_run),
            "badcases": badcases,
        }
        Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[OK] 报告已写入 {out}")
    return 0


def compare_experiments(baseline: str, candidate: str, *, out: str | None = None) -> int:
    if not require_api_key():
        print("[FAIL] 未配置 LANGSMITH_API_KEY")
        return 1

    client = get_client()

    def _avg(exp: str) -> dict[str, float]:
        _, fbs = fetch_run_feedbacks(client, exp)
        return summarize_averages(fbs)

    base = _avg(baseline)
    cand = _avg(candidate)
    keys = sorted(set(base) | set(cand))

    lines = [
        "# TalentFlow 评估实验对比",
        "",
        f"| 维度 | 基线 `{baseline}` | 候选 `{candidate}` | 变化 |",
        "|------|------|------|------|",
    ]
    print("=" * 70)
    print(f"{'维度':28s} {'基线':>10s} {'候选':>10s} {'Δ':>10s}")
    print("-" * 70)
    for key in keys:
        b, c = base.get(key), cand.get(key)
        b_s = f"{b:.4f}" if b is not None else "—"
        c_s = f"{c:.4f}" if c is not None else "—"
        d_s = f"{c - b:+.4f}" if b is not None and c is not None else "—"
        print(f"{key:28s} {b_s:>10s} {c_s:>10s} {d_s:>10s}")
        lines.append(f"| {key} | {b_s} | {c_s} | {d_s} |")

    if out:
        Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n[OK] 报告 → {out}")
    return 0
