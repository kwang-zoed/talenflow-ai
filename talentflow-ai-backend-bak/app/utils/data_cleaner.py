import json
from typing import List, Dict, Any, Optional

def clean_skills_data(skills_raw) -> List[str]:
    if not skills_raw:
        return []
    if isinstance(skills_raw, list):
        return [str(s).strip() for s in skills_raw if s]
    if isinstance(skills_raw, str):
        try:
            parsed = json.loads(skills_raw)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if s]
        except (json.JSONDecodeError, TypeError):
            pass
        return [s.strip() for s in skills_raw.split(',') if s.strip()]
    return []

def clean_job_data_for_response(result: Dict[str, Any], filename: Optional[str] = None):
    skills_clean = clean_skills_data(result.get("required_skills", []))
    description = result.get("description", "")[:800]
    
    suffix = filename.split('.')[0] if filename else None
    
    return {
        "title": result.get("title") or (f"解析职位-{suffix}" if suffix else "未命名职位"),
        "company": result.get("company") or (f"未知公司-{suffix}" if suffix else "未知公司"),
        "salary": result.get("salary") or "面议",
        "location": result.get("location") or "不限",
        "experience_requirement": result.get("experience_requirement") or "不限",
        "education_requirement": result.get("education_requirement") or "不限",
        "required_skills": skills_clean,
        "description": description
    }

def clean_batch_job_results(result_list):
    if not isinstance(result_list, list):
        if isinstance(result_list, dict):
            result_list = [result_list]
        else:
            result_list = []
    
    jobs = []
    for item in result_list:
        if isinstance(item, dict):
            cleaned = clean_job_data_for_response(item)
            jobs.append(cleaned)
    
    return jobs
