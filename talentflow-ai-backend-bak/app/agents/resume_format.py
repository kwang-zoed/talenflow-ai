import json
import re
from typing import Any, Dict, List, Optional


OPTIMIZED_NAME_SUFFIXES = ("_Optimized", "_optimized", "_OPTIMIZED")
OPTIMIZED_RESUME_SOURCES = frozenset({"agent_optimized", "smart_apply_optimized"})


RESUME_JSON_SCHEMA = """
{
  "name": "姓名（字符串，必须与原始简历完全一致）",
  "phone": "电话（字符串）",
  "email": "邮箱（字符串）",
  "title": "意向职位/简历标题（字符串，可润色岗位表述，勿加姓名后缀）",
  "education": "学历（字符串）",
  "experience_years": 10,
  "skills": ["技能1", "技能2"],
  "summary": "个人简介（纯文本，不含工作经历和项目经验）",
  "work_experience": "工作经历（纯文本或 Markdown，可多段）",
  "project_experience": "项目经验（纯文本或 Markdown，可多段）"
}
"""


def parse_resume_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _coerce_skills(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [part.strip() for part in re.split(r"[,，、;；]", value) if part.strip()]
    return []


def strip_optimized_name_suffix(name: str) -> str:
    """去掉历史/模型/MCP 误加的 Optimized 后缀，保留真实姓名。"""
    n = (name or "").strip()
    for suffix in OPTIMIZED_NAME_SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    n = re.sub(r"[_\-]?\s*[Oo]ptimized\s*$", "", n).strip()
    n = re.sub(r"[（(]\s*[Oo]?ptimized\s*[）)]\s*$", "", n).strip()
    return n or "求职者"


def resolve_candidate_name(
    resume_data: Optional[Dict[str, Any]] = None,
    original: Optional[Dict[str, Any]] = None,
    explicit_original_name: Optional[str] = None,
) -> str:
    """优先使用原始简历真实姓名，绝不保留 _Optimized 后缀。"""
    for candidate in (
        explicit_original_name,
        (original or {}).get("name"),
        (resume_data or {}).get("name"),
    ):
        if candidate is not None and str(candidate).strip():
            return strip_optimized_name_suffix(str(candidate))
    return "求职者"


def strip_title_job_prefix(title: str) -> str:
    """去掉 title 上已有的【投递职位】前缀，避免重复拼接。"""
    return re.sub(r"^【[^】]+】", "", (title or "").strip()).strip()


def build_optimized_resume_title(
    job_title: str,
    base_title: str = "",
    job_company: str = "",
    max_len: int = 100,
) -> str:
    """在 title 中标注投递职位，用于区分多份优化简历。"""
    base = strip_title_job_prefix(base_title)
    job_label = (job_title or "").strip()
    if job_company:
        job_label = f"{job_label}·{job_company.strip()}" if job_label else job_company.strip()
    if not job_label:
        return base[:max_len] if base else ""

    prefix = f"【{job_label}】"
    result = f"{prefix}{base}" if base else prefix
    if len(result) > max_len:
        return result[: max_len - 1] + "…"
    return result


def _coerce_experience_years(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def normalize_resume_data(
    parsed: Dict[str, Any],
    original: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    original = original or {}

    def pick(key: str, default: Any = None) -> Any:
        value = parsed.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            return original.get(key, default)
        return value

    name = resolve_candidate_name(parsed, original)
    return {
        "name": name,
        "phone": pick("phone"),
        "email": pick("email"),
        "title": pick("title"),
        "education": pick("education"),
        "experience_years": _coerce_experience_years(
            parsed.get("experience_years", original.get("experience_years"))
        ),
        "skills": _coerce_skills(parsed.get("skills", original.get("skills"))),
        "summary": pick("summary", ""),
        "work_experience": pick("work_experience", ""),
        "project_experience": pick("project_experience", ""),
    }


def format_resume_text(resume_data: Dict[str, Any]) -> str:
    parts = []
    if resume_data.get("name"):
        parts.append(f"姓名: {resume_data['name']}")
    if resume_data.get("phone"):
        parts.append(f"电话: {resume_data['phone']}")
    if resume_data.get("email"):
        parts.append(f"邮箱: {resume_data['email']}")
    if resume_data.get("title"):
        parts.append(f"职位: {resume_data['title']}")
    if resume_data.get("education"):
        parts.append(f"学历: {resume_data['education']}")
    if resume_data.get("experience_years") is not None:
        parts.append(f"工作年限: {resume_data['experience_years']}")
    if resume_data.get("skills"):
        parts.append(f"技能: {', '.join(resume_data['skills'])}")
    if resume_data.get("summary"):
        parts.append(f"个人简介:\n{resume_data['summary']}")
    if resume_data.get("work_experience"):
        parts.append(f"工作经历:\n{resume_data['work_experience']}")
    if resume_data.get("project_experience"):
        parts.append(f"项目经验:\n{resume_data['project_experience']}")
    return "\n\n".join(parts)
