# 智能投递序列图

> 预览：安装 **Markdown Preview Mermaid Support**，打开本文件 `Ctrl+Shift+V`；或复制 `mermaid` 到 [Mermaid Live Editor](https://mermaid.live)。  
> 配套：[smart-apply-flow.md](./smart-apply-flow.md) · [smart-apply-state.md](./smart-apply-state.md)

---

## 30 秒读懂

一次智能投递分 **3 个 Turn**，共用 `thread_id`。竖线 **激活条** 用 `activate` / `deactivate` 标注；后端 ID 为 `SVR`（显示名 FastAPI）。

| Turn | 进程 | 触发 | status 走向 |
|------|------|------|-------------|
| 1 | Celery | `POST .../submit` | `processing` → `interrupted` |
| 2 | FastAPI | `POST .../resume` | `interrupted` → `processing` → `interrupted` |
| 3 | FastAPI | 再次 `.../resume` | `processing` → `success` |

---

## 智能投递交互序列图

```mermaid
sequenceDiagram
    autonumber
    actor U as 求职者
    participant FE as Vue 前端
    participant SVR as FastAPI
    participant DB as MySQL
    participant RQ as Redis 队列
    participant WK as Celery Worker
    participant LG as LangGraph
    participant CP as SQLite Checkpointer
    participant MCP as MCP Server
    participant LLM as DeepSeek

    Note over U,LLM: Turn 1 — 提交与 Celery 执行

    U->>FE: 选择简历+职位，点击智能投递
    FE->>SVR: POST smart-apply/submit
    activate SVR
    SVR->>SVR: build_initial_state 校验简历
    SVR->>SVR: assert_smart_apply_ready
    SVR->>DB: create_apply_task status running
    DB-->>SVR: row id
    SVR->>RQ: smart_apply_task.delay
    SVR-->>FE: task_id + thread_id
    deactivate SVR
    FE->>FE: localStorage 保存任务

    loop 轮询直到 interrupted
        FE->>SVR: GET smart-apply/status/task_id
        activate SVR
        SVR->>RQ: AsyncResult 读 Celery
        RQ-->>SVR: state PROGRESS meta
        SVR-->>FE: status processing percent stage
        deactivate SVR
    end

    RQ->>WK: 消费 smart_apply_task
    activate WK
    WK->>LG: graph.astream initial_state thread_id
    activate LG
    LG->>MCP: get_resume_content user_id
    MCP->>DB: 查询默认简历
    DB-->>MCP: 简历记录
    MCP-->>LG: 简历正文与字段
    LG->>LLM: optimize_resume_node
    LLM-->>LG: optimized_resume JSON
    LG->>CP: 写入 checkpoint
    CP-->>LG: ok
    LG->>LG: interrupt 等待审核简历
    WK->>RQ: update_state PROGRESS interrupted
    deactivate LG
    deactivate WK

    FE->>SVR: GET status
    activate SVR
    SVR->>DB: update_apply_task interrupted
    DB-->>SVR: ok
    SVR-->>FE: status interrupted review_type optimized_resume
    deactivate SVR
    FE->>FE: SmartApplyReviewDialog 弹窗

    Note over U,LLM: Turn 2 — 确认简历后 FastAPI 续跑

    U->>FE: 确认优化简历
    FE->>SVR: POST thread/thread_id/resume
    activate SVR
    SVR->>LG: ainvoke Command resume updates
    activate LG
    LG->>CP: 读取 checkpoint 断点
    CP-->>LG: state
    LG->>MCP: save_optimized_resume
    MCP->>DB: INSERT 优化版简历
    DB-->>MCP: new_resume_id
    MCP-->>LG: new_resume_id
    LG->>LLM: generate_letter_node
    LLM-->>LG: cover_letter
    LG->>CP: 更新 checkpoint
    CP-->>LG: ok
    LG->>LG: interrupt 等待审核求职信
    deactivate LG
    SVR->>DB: update_apply_task interrupted
    DB-->>SVR: ok
    SVR-->>FE: status interrupted review_type cover_letter
    deactivate SVR

    Note over U,LLM: Turn 3 — 确认求职信后完成投递

    U->>FE: 确认求职信
    FE->>SVR: POST thread/thread_id/resume
    activate SVR
    SVR->>LG: ainvoke 续跑
    activate LG
    LG->>MCP: create_application_record
    MCP->>DB: INSERT applications
    DB-->>MCP: application_id
    MCP-->>LG: application_id
    LG->>CP: 最终 checkpoint done
    CP-->>LG: ok
    deactivate LG
    SVR->>DB: update_apply_task success stage done
    DB-->>SVR: ok
    SVR->>DB: update UserResumeCache 可选
    SVR-->>FE: status success application_id
    deactivate SVR
    FE->>FE: 移除 localStorage 任务，提示成功
```

---

## 关键 API 与消息

| 步骤 | HTTP | 说明 |
|------|------|------|
| 提交 | `POST /api/v1/user/smart-apply/submit` | 返回 `task_id`、`thread_id` |
| 轮询 | `GET /api/v1/user/smart-apply/status/{task_id}` | `processing` / `interrupted` / `success` / `error` |
| 续跑 | `POST /api/v1/user/smart-apply/thread/{thread_id}/resume` | Body `{ updates: {...} }` |
| 就绪检查 | `GET /api/v1/user/smart-apply/readiness` | Redis / Worker / MCP 是否可用 |

---

## MCP 工具调用一览

| LangGraph 节点 | MCP 工具 | 作用 |
|----------------|----------|------|
| fetch_resume | `get_resume_content` / `get_resume_by_id` | 读用户简历 |
| save_optimized_resume | `save_optimized_resume` | 持久化 AI 优化版 |
| save_record | `create_application_record` | 创建投递记录 |

---

## 与其它文档

| 文档 | 区别 |
|------|------|
| [smart-apply-flow.md](./smart-apply-flow.md) | 活动图：分支与失败场景 |
| [smart-apply-state.md](./smart-apply-state.md) | 状态图：status / stage 字段对照 |
| **本文件** | 序列图：时序 + 激活条生命周期 |

---

## 文档命名约定

- 文件名：`docs/smart-apply-sequence.md`
- 一级标题：`# 智能投递序列图`
- 图表小节：`## 智能投递交互序列图`
