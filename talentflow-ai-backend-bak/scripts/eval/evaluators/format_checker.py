"""确定性格式评估：Pydantic / 规则校验输出结构。"""

from __future__ import annotations

from pydantic import ValidationError

from evaluators._common import get_inputs, get_outputs
from schemas.eval_output_schema import RagEvalOutput
from schemas.smart_apply_eval_schema import OptimizedResumeEvalOutput


def check_rag_format(run, example) -> dict:
    outputs = get_outputs(run)

    if outputs.get("error"):
        return {
            "key": "valid_format",
            "score": 0,
            "comment": f"target 返回错误: {outputs['error']}",
        }

    if "results" not in outputs:
        return {
            "key": "valid_format",
            "score": 0,
            "comment": "缺少 results 字段",
        }

    try:
        parsed = RagEvalOutput.model_validate(outputs)
        if not parsed.results:
            return {
                "key": "valid_format",
                "score": 0,
                "comment": "results 为空列表",
            }
        return {
            "key": "valid_format",
            "score": 1,
            "comment": f"格式合规，共 {len(parsed.results)} 条结果",
        }
    except ValidationError as exc:
        return {
            "key": "valid_format",
            "score": 0,
            "comment": f"Pydantic 校验失败: {exc.error_count()} 处错误",
        }


def check_smart_apply_format(run, example) -> dict:
    """Smart Apply：求职信非空 / 优化简历 JSON 结构合规。"""
    run_out = get_outputs(run)
    ex_in = get_inputs(example)
    ex_out = get_outputs(example)
    eval_task = run_out.get("eval_task") or ex_in.get("eval_task")

    if run_out.get("error"):
        return {
            "key": "valid_format",
            "score": 0,
            "comment": f"target 返回错误: {run_out['error']}",
        }

    if eval_task == "cover_letter":
        letter = (run_out.get("cover_letter") or "").strip()
        if len(letter) < 50:
            return {
                "key": "valid_format",
                "score": 0,
                "comment": f"求职信过短或为空（{len(letter)} 字）",
            }
        return {
            "key": "valid_format",
            "score": 1,
            "comment": f"求职信格式合规，长度 {len(letter)} 字",
        }

    if eval_task == "optimize_resume":
        resume = run_out.get("optimized_resume")
        if not isinstance(resume, dict):
            return {
                "key": "valid_format",
                "score": 0,
                "comment": "缺少 optimized_resume 对象",
            }
        try:
            parsed = OptimizedResumeEvalOutput.model_validate(resume)
        except ValidationError as exc:
            return {
                "key": "valid_format",
                "score": 0,
                "comment": f"简历 JSON 校验失败: {exc.error_count()} 处错误",
            }

        expected_name = ex_out.get("must_preserve_name") or ex_in.get("applicant_name")
        if expected_name and parsed.name.strip() != str(expected_name).strip():
            return {
                "key": "valid_format",
                "score": 0,
                "comment": f"姓名被修改: {parsed.name} != {expected_name}",
            }

        has_content = bool(
            (parsed.work_experience or "").strip()
            or (parsed.project_experience or "").strip()
        )
        if not has_content:
            return {
                "key": "valid_format",
                "score": 0,
                "comment": "工作经历与项目经验均为空",
            }

        return {
            "key": "valid_format",
            "score": 1,
            "comment": f"简历 JSON 合规，姓名={parsed.name}",
        }

    return {
        "key": "valid_format",
        "score": 0,
        "comment": f"未知 eval_task: {eval_task}",
    }
