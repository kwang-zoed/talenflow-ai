# 智能投递序列图

> 预览：安装 **Markdown Preview Mermaid Support**，打开本文件 `Ctrl+Shift+V`；或复制 `mermaid` 到 [Mermaid Live Editor](https://mermaid.live)。  
> 配套活动流程图：[smart-apply-flow.md](./smart-apply-flow.md)

---

## 30 秒读懂

一次智能投递在时间上分为 **3 段**（LangSmith 里常显示为 2～3 个 Turn）：

| 段 | 执行进程 | 触发方式 | 跑到哪一步 |
|----|----------|----------|------------|
| **Turn 1** | Celery Worker | `POST /smart-apply/submit` | 取简历 → AI 优化 → **暂停等确认简历** |
| **Turn 2** | FastAPI | `POST /thread/{id}/resume` | 保存简历 → 写求职信 → **暂停等确认求职信** |
| **Turn 3** | FastAPI | 再次 `POST .../resume` | 写入投递记录 → 完成 |

同一次投递共用 **`thread_id`**（Checkpointer 续跑）；**`task_id`** 主要用于 Turn 1 轮询 Celery 进度。

---

## 智能投递交互序列图

```mermaid
sequenceDiagram
    autonumber
    actor U as 求职者
    participant FE as Vue 前端
    participant API as FastAPI
    participant DB as MySQL
    participant RQ as Redis 队列
    participant WK as Celery Worker
    participant LG as LangGraph
    participant CP as SQLite Checkpointer
    participant MCP as MCP Server
    participant LLM as DeepSeek

    Note over U,LLM: Turn 1 — 提交与 Celery 执行（astream）

    U->>FE: 选择简历+职位，点击智能投递
    FE->>API: POST /api/v1/user/smart-apply/submit
    API->>API: build_initial_state 校验简历
    API->>API: assert_smart_apply_ready
    API->>DB: create_apply_task(thread_id)
    API->>RQ: smart_apply_task.delay(payload)
    API-->>FE: task_id + thread_id
    FE->>FE: localStorage 保存任务

    loop 轮询进度 pollSmartApplyResult
        FE->>API: GET /smart-apply/status/{task_id}
        API->>RQ: AsyncResult 读 Celery 状态
        API-->>FE: processing / percent / stage
    end

    RQ->>WK: 消费 smart_apply_task
    WK->>LG: graph.astream(initial_state, thread_id)
    LG->>MCP: get_resume_content(user_id)
    MCP->>DB: 查询默认简历
    MCP-->>LG: 简历正文与字段
    LG->>LLM: optimize_resume_node AI 优化
    LLM-->>LG: optimized_resume JSON
    LG->>CP: 写入 checkpoint
    LG->>LG: interrupt 等待审核简历
    WK->>RQ: update_state PROGRESS interrupted
    FE->>API: GET status
    API-->>FE: status=interrupted review_type=optimized_resume
    FE->>FE: SmartApplyReviewDialog 弹窗

    Note over U,LLM: Turn 2 — 用户确认简历后 FastAPI 续跑（ainvoke）

    U->>FE: 确认优化简历
    FE->>API: POST /smart-apply/thread/{thread_id}/resume
    API->>LG: ainvoke(Command(resume=updates))
    LG->>CP: 读取 checkpoint 断点
    LG->>MCP: save_optimized_resume
    MCP->>DB: INSERT 优化版简历
    MCP-->>LG: new_resume_id
    LG->>LLM: generate_letter_node 写求职信
    LLM-->>LG: cover_letter
    LG->>CP: 更新 checkpoint
    LG->>LG: interrupt 等待审核求职信
    API->>DB: update_apply_task interrupted
    API-->>FE: status=interrupted review_type=cover_letter

    Note over U,LLM: Turn 3 — 用户确认求职信后完成投递

    U->>FE: 确认求职信
    FE->>API: POST /thread/{thread_id}/resume
    API->>LG: ainvoke 续跑
    LG->>MCP: create_application_record
    MCP->>DB: INSERT applications
    MCP-->>LG: application_id
    LG->>CP: 最终状态 done
    API->>DB: update_apply_task success
    API->>DB: update UserResumeCache 可选
    API-->>FE: status=success application_id
    FE->>FE: 移除 localStorage 任务，提示成功
```

---

## 关键 API 与消息

| 步骤 | HTTP | 说明 |
|------|------|------|
| 提交 | `POST /api/v1/user/smart-apply/submit` | 返回 `task_id`、`thread_id` |
| 轮询 | `GET /api/v1/user/smart-apply/status/{task_id}` | `processing` / `interrupted` / `success` / `error` |
| 续跑 | `POST /api/v1/user/smart-apply/thread/{thread_id}/resume` | Body: `{ updates: {...} }`，人工确认后调用 |
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
| [smart-apply-flow.md](./smart-apply-flow.md) | **活动图**：分支、状态、失败场景 |
| [smart-apply-state.md](./smart-apply-state.md) | **状态图**：API / DB / LangGraph 状态转换 |
| **本文件** | **序列图**：参与者之间按时间的调用顺序 |

---

## 文档命名约定

- 文件名：`docs/smart-apply-sequence.md`
- 一级标题：`# 智能投递序列图`
- 图表小节：`## 智能投递交互序列图`
