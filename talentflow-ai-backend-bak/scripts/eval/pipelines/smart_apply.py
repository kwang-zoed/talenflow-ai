"""Smart Apply 流水线：target + smoke + 评估器注册。"""

from __future__ import annotations

import asyncio
import json
import logging

from core.bootstrap import setup_paths

setup_paths()
import config  # noqa: E402
from evaluators import SMART_APPLY_EVALUATORS  # noqa: E402

logger = logging.getLogger(__name__)
GOLDEN_FILE = config.DATASETS_DIR / "smart_apply_golden_set_v1.json"


async def _smart_apply_async(inputs: dict) -> dict:
    eval_task = (inputs.get("eval_task") or "").strip()
    applicant_name = (inputs.get("applicant_name") or "求职者").strip()
    resume_content = (inputs.get("resume_content") or "").strip()
    job_description = (inputs.get("job_description") or "").strip()

    if not eval_task:
        return {"error": "eval_task 为空"}
    if not resume_content or not job_description:
        return {"error": "resume_content 或 job_description 为空", "eval_task": eval_task}

    state = {
        "resume_content": resume_content,
        "job_description": job_description,
        "applicant_name": applicant_name,
        "original_resume": inputs.get("original_resume") or {"name": applicant_name},
    }

    if eval_task == "cover_letter":
        from app.agents.nodes import generate_letter_node

        out = await generate_letter_node(state)
        if out.get("error_message"):
            return {"error": out["error_message"], "eval_task": eval_task}
        return {"eval_task": eval_task, "cover_letter": out.get("cover_letter"), "applicant_name": applicant_name}

    if eval_task == "optimize_resume":
        from app.agents.nodes import optimize_resume_node

        out = await optimize_resume_node(state)
        if out.get("error_message"):
            return {"error": out["error_message"], "eval_task": eval_task}
        return {
            "eval_task": eval_task,
            "optimized_resume": out.get("optimized_resume"),
            "applicant_name": out.get("applicant_name") or applicant_name,
        }

    return {"error": f"未知 eval_task: {eval_task}", "eval_task": eval_task}


def smart_apply_target(inputs: dict) -> dict:
    try:
        return asyncio.run(_smart_apply_async(inputs))
    except Exception as exc:
        logger.exception("smart_apply_target 失败: %s", exc)
        return {"error": str(exc), "eval_task": inputs.get("eval_task")}


def smoke_smart_apply(
    *,
    task: str = "all",
    index: int = -1,
    golden_file=None,
) -> int:
    path = golden_file or GOLDEN_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    examples = data["examples"]
    if index >= 0:
        examples = [examples[index]]

    ok = 0
    for ex in examples:
        inp = ex["inputs"]
        if task != "all" and inp["eval_task"] != task:
            continue
        print("-" * 60)
        print(f"[{inp['eval_task']}] {inp.get('applicant_name')}")
        out = smart_apply_target(inp)
        if out.get("error"):
            print(f"[FAIL] {out['error']}")
            continue
        if inp["eval_task"] == "cover_letter":
            letter = out.get("cover_letter", "")
            print(f"[OK] 求职信 {len(letter)} 字")
        else:
            r = out.get("optimized_resume", {})
            print(f"[OK] 简历 name={r.get('name')}")
        ok += 1
    print(f"完成: {ok} 条")
    return 0 if ok else 1


def get_evaluators():
    return SMART_APPLY_EVALUATORS
