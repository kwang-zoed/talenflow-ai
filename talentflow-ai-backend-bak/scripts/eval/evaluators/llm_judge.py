"""
LLM-as-Judge：RAG 检索结果相关性评估（RelevanceScore 1-5）。

三层面：技术栈 / 经验职级 / 地域
边界案例：远程 vs 现场、Python vs 全栈含 Python 等（见 PDF RelevanceScore）
"""

from __future__ import annotations

import re
from functools import lru_cache

import config
from evaluators._common import get_inputs, get_outputs


def _query_text(run, example) -> str:
    run_in = get_inputs(run)
    ex_in = get_inputs(example)
    return (run_in.get("query") or ex_in.get("query") or "").strip()


def _format_top_jobs(run_outputs: dict, n: int | None = None) -> str:
    if n is None:
        n = config.EVAL_JUDGE_TOP_N
    lines: list[str] = []
    for i, item in enumerate((run_outputs.get("results") or [])[:n], 1):
        if not isinstance(item, dict):
            continue
        title = item.get("title") or "未知职位"
        passage = (item.get("passage") or "")[:200]
        job_id = item.get("id", "?")
        lines.append(f"{i}. [id={job_id}] {title}\n   {passage}")
    return "\n".join(lines) if lines else "（无检索结果）"


def _build_rag_judge_prompt(query: str, jobs_text: str) -> str:
    return f"""你是一位资深招聘专家。请评估以下检索结果与用户查询的整体相关性。

【评分标准 1-5】
1 = 完全无关
3 = 部分匹配（含目标技能但非核心，例如查 Python 推全栈含 Python）
5 = 高度精准（技术栈、经验、地域均高度匹配）

【三层面评估框架】
- 技术层面：是否匹配查询中的技术栈
- 经验层面：是否匹配职级/年限要求
- 地域层面：是否匹配工作地点偏好

【边界案例】
- 用户查「远程」，推荐现场岗位 → 1 分
- 用户查「Python」，推荐全栈含 Python → 3 分
- 技术、经验、地域三项均吻合 → 5 分

【用户查询】
{query}

【Top-{config.EVAL_JUDGE_TOP_N} 检索结果】
{jobs_text}

请综合以上检索结果与用户意图的整体匹配度，只输出一个 1-5 的整数，不要任何解释。"""


def _parse_binary_score(text: str) -> int | None:
    if not text:
        return None
    stripped = text.strip()
    if stripped in ("0", "1"):
        return int(stripped)
    m = re.search(r"\b(0|1)\b", stripped)
    return int(m.group(1)) if m else None


def _parse_relevance_score(text: str) -> int | None:
    if not text:
        return None
    # 优先匹配 1-5 独立数字
    m = re.search(r"\b([1-5])\b", text.strip())
    if m:
        return int(m.group(1))
    # 容错：首个数字
    m = re.search(r"([1-5])", text)
    return int(m.group(1)) if m else None


@lru_cache(maxsize=1)
def _get_judge_llm():
    from langchain_openai import ChatOpenAI

    kwargs: dict = {
        "api_key": config.EVAL_JUDGE_API_KEY,
        "model": config.get_judge_model(),
        "temperature": config.EVAL_JUDGE_TEMPERATURE,
    }
    base_url = config.get_judge_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _invoke_judge(prompt: str) -> tuple[int | None, str]:
    if not config.EVAL_JUDGE_API_KEY.strip():
        return None, "未配置 EVAL_JUDGE_API_KEY / API_KEY"

    try:
        llm = _get_judge_llm()
        response = llm.invoke(prompt)
        raw = (response.content or "").strip()
        score = _parse_relevance_score(raw)
        return score, raw
    except Exception as exc:
        return None, f"LLM 调用失败: {exc}"


def llm_judge_rag(run, example) -> list[dict]:
    """
    对 Top-N 检索结果打 RelevanceScore（1-5），返回两条 Feedback：
    - relevance_score: 归一化到 0~1（原始分/5）
    - relevance_pass: 原始分 >= 4 为 1，否则 0
    """
    run_out = get_outputs(run)
    query = _query_text(run, example)

    if run_out.get("error"):
        fail = {
            "key": "relevance_score",
            "score": 0,
            "comment": f"target 错误: {run_out['error']}",
        }
        return [fail, {"key": "relevance_pass", "score": 0, "comment": "target 错误"}]

    if not query:
        return [
            {"key": "relevance_score", "score": 0, "comment": "query 为空"},
            {"key": "relevance_pass", "score": 0, "comment": "query 为空"},
        ]

    jobs_text = _format_top_jobs(run_out)
    prompt = _build_rag_judge_prompt(query, jobs_text)
    raw_score, raw_response = _invoke_judge(prompt)

    if raw_score is None:
        return [
            {
                "key": "relevance_score",
                "score": 0,
                "comment": f"无法解析分数，原始响应: {raw_response[:200]}",
            },
            {"key": "relevance_pass", "score": 0, "comment": "解析失败"},
        ]

    normalized = raw_score / 5.0
    passed = 1 if raw_score >= config.EVAL_RELEVANCE_PASS_THRESHOLD else 0

    comment = (
        f"原始分={raw_score}/5 provider={config.EVAL_JUDGE_PROVIDER} "
        f"model={config.get_judge_model()}"
    )

    return [
        {"key": "relevance_score", "score": normalized, "comment": comment},
        {
            "key": "relevance_pass",
            "score": passed,
            "comment": f"阈值≥{config.EVAL_RELEVANCE_PASS_THRESHOLD}: {'通过' if passed else '未通过'} | {raw_response[:80]}",
        },
    ]


def _example_expected(example) -> dict:
    return get_outputs(example)


def _build_letter_judge_prompt(
    job_description: str,
    cover_letter: str,
    rubric: str,
    keywords: list[str],
) -> str:
    kw = "、".join(keywords) if keywords else "无"
    return f"""你是一位资深招聘 HR。请判断以下求职信是否达到可用标准。

【评判维度】
1. 与职位描述的匹配度（技能、经验、岗位诉求）
2. 是否编造简历中不存在的经历（若有编造倾向判 0）
3. 表达是否专业、简洁、有说服力

【补充要求】
- 评分标准：只输出 0 或 1（1=合格，0=不合格）
- 应尽量体现关键词：{kw}
- 细则：{rubric}

【职位描述】
{job_description}

【求职信】
{cover_letter}

请只输出 0 或 1，不要解释。"""


def _build_resume_judge_prompt(
    job_description: str,
    resume_text: str,
    rubric: str,
    keywords: list[str],
    preserve_name: str,
) -> str:
    kw = "、".join(keywords) if keywords else "无"
    return f"""你是一位资深招聘 HR。请判断以下 AI 优化后的简历是否达到可用标准。

【评判维度】
1. 与目标岗位的匹配度（关键词植入是否自然）
2. 是否编造原始简历没有的经历（若有编造判 0）
3. 结构是否完整、表述是否专业
4. 姓名必须保持为「{preserve_name}」，若姓名被改判 0

【补充要求】
- 评分标准：只输出 0 或 1（1=合格，0=不合格）
- 应体现关键词：{kw}
- 细则：{rubric}

【职位描述】
{job_description}

【优化后简历】
{resume_text}

请只输出 0 或 1，不要解释。"""


def llm_judge_smart_apply(run, example) -> dict:
    """按 eval_task 对求职信或优化简历做 0/1 质量裁判。"""
    run_out = get_outputs(run)
    ex_in = get_inputs(example)
    ex_out = _example_expected(example)
    eval_task = run_out.get("eval_task") or ex_in.get("eval_task")

    if run_out.get("error"):
        return {
            "key": "letter_quality_judge" if eval_task == "cover_letter" else "resume_quality_judge",
            "score": 0,
            "comment": f"target 错误: {run_out['error']}",
        }

    rubric = ex_out.get("quality_rubric", "评估生成质量与岗位匹配度")
    keywords = ex_out.get("must_mention_keywords") or []
    job_description = ex_in.get("job_description", "")

    if eval_task == "cover_letter":
        letter = (run_out.get("cover_letter") or "").strip()
        if not letter:
            return {"key": "letter_quality_judge", "score": 0, "comment": "求职信为空"}
        prompt = _build_letter_judge_prompt(job_description, letter, rubric, keywords)
        raw_score, raw_response = _invoke_judge_binary(prompt)
        key = "letter_quality_judge"
    elif eval_task == "optimize_resume":
        resume = run_out.get("optimized_resume") or {}
        from app.agents.resume_format import format_resume_text

        resume_text = format_resume_text(resume) if isinstance(resume, dict) else str(resume)
        preserve_name = ex_out.get("must_preserve_name") or ex_in.get("applicant_name", "")
        prompt = _build_resume_judge_prompt(
            job_description, resume_text, rubric, keywords, preserve_name
        )
        raw_score, raw_response = _invoke_judge_binary(prompt)
        key = "resume_quality_judge"
    else:
        return {"key": "quality_judge", "score": 0, "comment": f"未知 eval_task: {eval_task}"}

    if raw_score is None:
        return {
            "key": key,
            "score": 0,
            "comment": f"无法解析 0/1，原始响应: {raw_response[:200]}",
        }

    return {
        "key": key,
        "score": float(raw_score),
        "comment": f"Judge={raw_score} model={config.get_judge_model()} | {raw_response[:80]}",
    }


def _invoke_judge_binary(prompt: str) -> tuple[int | None, str]:
    if not config.EVAL_JUDGE_API_KEY.strip():
        return None, "未配置 EVAL_JUDGE_API_KEY / API_KEY"

    try:
        llm = _get_judge_llm()
        response = llm.invoke(prompt)
        raw = (response.content or "").strip()
        score = _parse_binary_score(raw)
        return score, raw
    except Exception as exc:
        return None, f"LLM 调用失败: {exc}"
