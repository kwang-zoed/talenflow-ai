# 文档解析序列图

> 预览：安装 **Markdown Preview Mermaid Support**，打开本文件 `Ctrl+Shift+V`；或复制 `mermaid` 到 [Mermaid Live Editor](https://mermaid.live)。

---

## 30 秒读懂

管理员或 HR 上传 **PDF / DOCX / TXT** → `POST .../parse/submit` 返回 `task_id` → **Celery Worker** 提取文本 → **LLM 结构化 JSON** → 清洗 → 前端轮询 `GET .../parse/status/{task_id}` → 表单预填。

竖线 **激活条** 用 `activate` / `deactivate` 标注生命周期。参与者 ID 用 `SVR`（显示名 FastAPI），**不要用 `API`**。

---

## 文档解析交互序列图

```mermaid
sequenceDiagram
    autonumber
    actor A as 管理员或 HR
    participant FE as Admin或HrJobs页面
    participant SVR as FastAPI
    participant RQ as Redis队列
    participant RB as RedisResult
    participant WK as CeleryWorker
    participant DP as 文档解析器
    participant LLM as DeepSeek
    participant CLN as 数据清洗

    A->>FE: 选择文件上传
    FE->>SVR: POST multipart file
    activate SVR
    SVR->>SVR: 校验 pdf docx txt
    alt 职位JD解析
        SVR->>RQ: parse_document_task.delay
    else 简历解析
        SVR->>RQ: parse_resume_task.delay
    end
    SVR-->>FE: task_id 与 filename
    deactivate SVR
    FE->>FE: 保存 task_id 开始轮询

    loop 轮询直到 success 或 error
        FE->>SVR: GET parse status by task_id
        activate SVR
        SVR->>RB: AsyncResult
        RB-->>SVR: Celery state 与 meta
        alt Celery SUCCESS 且 result.status success
            Note right of FE: status success percent 100
        else Celery SUCCESS 含 error 或 FAILURE
            Note right of FE: status error
        else PENDING 或 PROGRESS
            Note right of FE: status processing percent N
        end
        SVR-->>FE: 返回 status 与 data 或 message
        deactivate SVR
    end

    RQ->>WK: 消费解析任务
    activate WK
    alt 职位文档
        WK->>DP: extract_text_from_bytes
        DP-->>WK: full_text
        WK->>LLM: get_parse_prompt 单条或批量
        LLM-->>WK: JSON 职位字段
        WK->>CLN: clean_job_data
        CLN-->>WK: 表单可用结构
    else 简历文档
        WK->>DP: extract_text_from_bytes
        DP-->>WK: full_text
        WK->>WK: extract_info_from_filename
        WK->>LLM: build_resume_parse_prompt
        LLM-->>WK: JSON 简历字段
        WK->>WK: normalize_resume_parse_result
    end
    WK->>RB: Celery SUCCESS 写入 result
    deactivate WK

    FE->>A: 预填表单或展示批量列表
```

---

## API 路径对照

| 类型 | 提交 | 状态查询 | Celery 任务 |
|------|------|----------|-------------|
| 职位（Admin） | `POST /api/v1/admin/jobs/parse/submit` | `GET .../jobs/parse/status/{task_id}` | `parse_document_task` |
| 职位（HR） | `POST /api/v1/mentor/jobs/parse/submit` | `GET .../jobs/parse/status/{task_id}` | 同上 |
| 简历（Admin） | `POST /api/v1/admin/resumes/parse/submit` | `GET .../resumes/parse/status/{task_id}` | `parse_resume_task` |

---

## Worker 内四步进度（职位解析）

| 进度 | Celery | API status | 动作 |
|------|--------|------------|------|
| 0% | `PENDING` | `processing` | 排队 |
| 25% | `PROGRESS` | `processing` | 提取文本 |
| 50% | `PROGRESS` | `processing` | LLM 解析 |
| 75% | `PROGRESS` | `processing` | 清洗 |
| 100% | `SUCCESS` | `success` 或 `error` | 写入 Redis Result |

简历解析为 3 步：约 30% / 60% / 90%。

---

## 与其它文档

| 文档 | 内容 |
|------|------|
| [function-structure.md](./function-structure.md) | 文档解析在平台能力层的位置 |
| [use-case.md](./use-case.md) | 管理员/HR 解析用例 |
| **本文件** | 上传 → Celery → LLM 时序 |

---

## 文档命名约定

- 文件名：`docs/parse-sequence.md`
- 一级标题：`# 文档解析序列图`
- 图表小节：`## 文档解析交互序列图`
