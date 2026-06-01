# 代码重复率优化实施计划

## 一、Repo 研究结论

当前项目存在严重的代码重复问题：

1. **通用工具函数重复**：至少5个文件中重复定义了 `extract_text_from_file`、`parse_llm_result`、`clean_job_data` 等函数
2. **Prompt模板硬编码且重复**：单个/批量职位解析的Prompt在至少3处不同地方硬编码
3. **数据转换逻辑重复**：多处定义 `xxx_to_dict` 手动转换，而未充分利用 Pydantic Schemas
4. **技能解析逻辑变种多**：技能数据格式化逻辑散落在各处至少7+处

## 二、涉及修改的文件和模块

### 2.1 新增文件
- `app/utils/__init__.py` - 工具模块初始化
- `app/utils/document_parser.py` - 文档文本提取通用函数
- `app/utils/llm_utils.py` - LLM结果解析和Prompt管理
- `app/utils/data_cleaner.py` - 数据清洗/格式化（技能、描述等）

### 2.2 修改文件（按依赖顺序）
1. **首先**：`app/core/celery_app.py` - 可能需要更新 include 路径
2. **其次**：`app/services/recommendation_service.py` - Celery任务改用通用函数
3. **最后**：API路由层
   - `app/api/v1/admin/job_manage.py`
   - `app/api/v1/mentor/job_manage.py`
   - `app/api/v1/admin/resume_manage.py`

### 2.3 现有 Schemas 检查
- `app/schemas/job_schema.py` - 现有 `JobParseResponse` 检查和扩展

## 三、具体修改步骤

### Step 1: 创建 utils 目录结构和通用函数

#### 1.1 document_parser.py - 文件文本提取
```python
import pdfplumber
import io
from docx import Document as DocxDocument

def extract_text_from_bytes(file_content: bytes, filename: str) -> str:
    """支持bytes输入（Celery用），统一从PDF/DOCX/TXT提取文本"""
    full_text = ""
    if filename.lower().endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + '\n'
    elif filename.lower().endswith(".docx"):
        doc = DocxDocument(io.BytesIO(file_content))
        parts = [p.text.strip() for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    parts.append(cell.text.strip())
        full_text = '\n'.join(parts)
    elif filename.lower().endswith(".txt"):
        if isinstance(file_content, bytes):
            full_text = file_content.decode('utf-8', errors='ignore')
        else:
            full_text = str(file_content)
    return full_text

# 向后兼容别名
def extract_text_from_file(contents, filename):
    """兼容旧版调用（contents可能是UploadFile.read()结果）"""
    return extract_text_from_bytes(contents, filename)
```

#### 1.2 llm_utils.py - LLM解析和Prompt管理
```python
from langchain_core.output_parsers import JsonOutputParser
from enum import Enum

class ParseMode(Enum):
    SINGLE = "single"    # 单个职位解析
    BATCH = "batch"      # 批量职位解析

def get_parse_prompt(full_text: str, mode: ParseMode = ParseMode.SINGLE) -> str:
    """根据解析模式返回对应Prompt - 统一管理，便于后续维护"""
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
    else:  # SINGLE
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
    """统一解析LLM返回的JSON结果"""
    parser = JsonOutputParser()
    return parser.parse(llm_text)
```

#### 1.3 data_cleaner.py - 数据清洗工具
```python
import json
from typing import List, Dict, Any, Optional

def clean_skills_data(skills_raw) -> List[str]:
    """统一清洗技能数据：无论输入是str/list/None，都确保返回字符串列表"""
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
    """
    清洗单个职位解析结果，并返回可直接通过Pydantic序列化的数据。
    这里只做清洗，不做dict拼接，让schemas来做实际的数据校验。
    """
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
    """清洗批量解析的结果列表"""
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
```

### Step 2: 扩展/检查 Schemas

优先复用现有 `JobParseResponse`，或者新增批量响应：

```python
# 在 job_schema.py 中添加
class BatchJobParseResponse(BaseModel):
    """批量职位解析的响应模型 - 统一校验，替代手动dict拼接"""
    total: int
    is_batch: bool = True
    jobs: List[JobParseResponse]
```

### Step 3: 重构现有代码以使用通用函数

#### 3.1 job_manage.py 改动
```python
# 顶部移除重复定义函数，改为导入:
from app.utils.document_parser import extract_text_from_file
from app.utils.llm_utils import parse_llm_json_result, get_parse_prompt, ParseMode
from app.utils.data_cleaner import clean_job_data_for_response, clean_batch_job_results

# 1. 单个解析处改为:
prompt = get_parse_prompt(full_text, ParseMode.SINGLE)
llm_output = ... 
result = parse_llm_json_result(llm_text)
return JobParseResponse(**clean_job_data_for_response(result, file.filename))

# 2. 批量解析处改为:
prompt = get_parse_prompt(full_text, ParseMode.BATCH)
llm_output = ...
result = parse_llm_json_result(llm_text)
jobs = clean_batch_job_results(result)
return BatchJobParseResponse(total=len(jobs), jobs=jobs).dict()
```

#### 3.2 recommendation_service.py 异步任务改动
同理，Celery 任务中的重复文本提取、Prompt 构建全部替换。

### Step 4: resume_manage.py 复用工具
同理，简历中用到 `extract_text_from_file` 和 `parse_llm_result` 地方也统一。

## 四、依赖和注意事项

### 4.1 现有依赖检查
- `pdfplumber`, `langchain_core`, `python-docx` - 均已安装
- Celery 任务模块需要更新到 utils 的可序列化导入路径

### 4.2 兼容方案
- 保留老函数名作为别名（如 `extract_text_from_file`），允许增量迁移

### 4.3 测试要求
- `/jobs/parse` 单个解析 - 验证
- `/jobs/parse/submit` -> Celery 异步 - 验证
- `/jobs/batch-parse` 批量 - 验证

## 五、风险处理

| 风险 | 处理方案 |
|-----|---------|
| 某文件漏改导致行为不一致 | 全局搜索旧函数调用 |
| `python-docx` 在 worker 中导入问题 | 在 utils 统一管控导入 |
| 现有的接口字段别名 | 改动前先跑一遍现有行为并记录字段返回样本 |
| Pydantic Schemas 缺少字段默认值 | 在 Schema 里给可选字段加 default |

## 六、Schemas 直接校验替代 xxx_to_dict 的说明

原 `job_to_dict` 可直接废弃，改为:
1. ORM 对象数据直接 feed 给 Pydantic `from_orm` / `model_validate`
2. 由 schemas 统一完成「有/无此字段」「默认值」「别名（alias）」
3. 既确保了字段校验，又减少了重复映射代码
