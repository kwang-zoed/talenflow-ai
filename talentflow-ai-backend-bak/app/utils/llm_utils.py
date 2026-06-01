from langchain_core.output_parsers import JsonOutputParser
from enum import Enum

class ParseMode(Enum):
    SINGLE = "single"
    BATCH = "batch"

def get_parse_prompt(full_text: str, mode: ParseMode = ParseMode.SINGLE) -> str:
    if mode == ParseMode.BATCH:
        return f"""你是一个专业的招聘文档批量解析助手
请仔细阅读以下文档内容，提取出所有职位的关键信息

要求：
1. 文档可能包含多个职位，请逐一解析所有职位。
2. 如果文档中没有明确提及某项信息，用合理默认值填充。
3. 返回格式必须是一个JSON数组，每个元素包含一个职位的信息：
[
    {{
        "title": "职位标题",
        "company": "公司名称",
        "salary": "薪资范围或面议",
        "location": "工作地点或不限",
        "experience_requirement": "经验要求或不限",
        "education_requirement": "学历要求或不限",
        "required_skills": ["技能1", "技能2"],
        "description": "职位描述"
    }}
]

请只返回严格的JSON数组，不要包含任何其他解释文字。

文档内容：{full_text[:4000]}
"""
    else:
        return f"""你是一个专业的招聘文档解析助手
请仔细阅读以下文档内容，提取出职位的关键信息

要求：
1. 如果文档中没有明确提及薪资，返回"面议"。
2. 技能列表（required_skills）请尽量提取技术栈、编程语言、工具等。
3. 请尝试从文档推断或提取以下信息：
    -location：工作地点如东莞，深圳，远程等等。
    -experience_requirement：经验要求如3年以上，5年以上等。
    -education_requirement：学历要求如本科以上，硕士以上等。

文档内容：{full_text[:3000]}

请以严格的JSON格式输出，不要包含其他文字：
{{
    "title": "职位标题",
    "company": "公司名称",
    "salary": "薪资范围",
    "location": "工作地点",
    "experience_requirement": "经验要求",
    "education_requirement": "学历要求",
    "required_skills": ["技能1", "技能2", "技能3"],
    "description": "职位描述"
}}
"""

def parse_llm_json_result(llm_text: str):
    parser = JsonOutputParser()
    return parser.parse(llm_text)
