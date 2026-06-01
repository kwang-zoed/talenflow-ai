"""简历文件解析：提示词构建与结果规范化（API / Celery Worker 共用）"""
import json
import os
import re
from typing import Any, Dict, List


def extract_info_from_filename(filename: str) -> Dict[str, str]:
    name = ""
    title = ""
    salary = ""

    name_patterns = [
        r"([\u4e00-\u9fa5]{2,4})[_-]",
        r"([\u4e00-\u9fa5]{2,4})[简历]",
        r"^([\u4e00-\u9fa5]{2,4})_",
    ]

    salary_patterns = [
        r"(\d+[kK]-?\d*[kK]?)",
        r"(\d+[kK]以上)",
        r"(\d+-\d+)[kK]",
        r"薪资(\d+[kK]-?\d*[kK]?)",
        r"(\d+[kK])",
    ]

    title_keywords = [
        "Java", "Python", "前端", "后端", "开发", "工程师", "产品", "经理",
        "测试", "运维", "架构", "算法", "数据", "分析师", "设计师", "运营",
    ]

    basename = os.path.splitext(filename)[0]

    for pattern in name_patterns:
        match = re.search(pattern, basename)
        if match:
            name = match.group(1)
            break

    for pattern in salary_patterns:
        match = re.search(pattern, basename)
        if match:
            salary = match.group(1)
            if salary:
                salary = salary.upper()
            break

    for keyword in title_keywords:
        if keyword in basename:
            title = keyword
            break

    return {"name": name, "title": title, "salary": salary}


def build_resume_parse_prompt(full_text: str, filename_info: Dict[str, str]) -> str:
    file_hints = (
        f"文件名线索: 姓名={filename_info['name']}, "
        f"职位={filename_info['title']}, 薪资={filename_info['salary']}"
    )
    return f"""你是一个专业的招聘简历解析助手。
请结合以下两部分信息，提取候选人的关键数据:

【线索信息 - 来自文件命名】:
{file_hints}

【简历正文内容】:
{full_text[:3000]}

要求：
1. 必须返回严格的 JSON 格式。
2. 如果某项信息在简历中找不到，请返回空字符串 "" 或空数组 []。
3. 技能列表（skills）请尽量提取技术栈、编程语言、软技能等。
4. 如果详细的工作经历和主要的项目经历超过了1500字，请对其进行摘要控制在1500字以内。

请严格按照以下 JSON 结构输出:
{{
    "name": "候选人姓名",
    "phone": "联系电话",
    "email": "电子邮箱",
    "title": "求职意向或当前职位",
    "education": "最高学历及学校专业",
    "summary": "个人优势或自我评价",
    "work_experience": "详细的工作经历",
    "project_experience": "主要项目经历",
    "skills": ["技能1", "技能2", "技能3"],
    "resume_language": "zh-CN" 或 "en-US"
}}
"""


def normalize_resume_parse_result(
    result: Any,
    filename_info: Dict[str, str],
) -> Dict[str, Any]:
    if isinstance(result, list) and len(result) > 0:
        result = result[0]
    elif not isinstance(result, dict):
        result = {}

    skills_raw = result.get("skills", [])
    if isinstance(skills_raw, str):
        try:
            skills: List[str] = json.loads(skills_raw)
        except (json.JSONDecodeError, TypeError):
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        skills = [s for s in skills_raw if s]
    else:
        skills = []

    return {
        "name": result.get("name") or filename_info.get("name") or "",
        "phone": result.get("phone") or "",
        "email": result.get("email") or "",
        "title": result.get("title") or filename_info.get("title") or "",
        "education": result.get("education") or "",
        "summary": result.get("summary") or "",
        "work_experience": result.get("work_experience") or "",
        "project_experience": result.get("project_experience") or "",
        "skills": skills,
    }
