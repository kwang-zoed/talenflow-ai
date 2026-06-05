# 智能投递流程图

> 预览：在 Cursor / VS Code 中安装 **Markdown Preview Mermaid Support**，打开本文件后使用 Markdown 预览（`Ctrl+Shift+V`）。  
> 也可复制下方 `mermaid` 代码块到 [Mermaid Live Editor](https://mermaid.live) 导出 PNG/SVG。

---

## 30 秒读懂：智能投递在干什么

用户选中 **一份简历 + 一个职位** 后点「一键投递」，系统会在后台：

1. **读简历**（从数据库经 MCP 取出）
2. **按职位描述 AI 优化简历**（可选；有缓存可跳过）
3. **让你确认**优化后的简历（默认开启）
4. **保存优化版简历** 并 **AI 写求职信**
5. **让你确认**求职信（默认开启）
6. **写入投递记录**（applications 表），完成投递

因为第 3、5 步要等人点确认，**一次投递在后台会分 2～3 段执行**（不是重复跑，是「暂停 → 你确认 → 接着跑」）。

---

## 读图指南：图里几大块分别是什么

| 图上区域 | 中文含义 | 谁在跑 |
|----------|----------|--------|
| 最上方（submit → 轮询） | **前端 + 提交 API**：点投递、拿 task_id、定时查进度 | 浏览器 + FastAPI |
| 中间 `STATUS` 子图 | **查任务状态**：排队中 / 进行中 / 待审核 / 成功 / 失败 | FastAPI 读 Redis |
| `REVIEW_UI` 子图 | **人工审核弹窗**：展示 AI 产物，点「确认并继续」 | 浏览器 + FastAPI |
| `TURN1` 子图 | **第一段 AI 流程**：取简历 → 优化 → 第一次暂停 | **Celery Worker** |
| `TURN2` / `TURN3` | **第二、三段**：保存简历、写信、最终入库 | **FastAPI**（你点确认后） |
| `MCP_SRV` | **工具服务**：替 LangGraph 节点去查库、写库 | 独立进程 `:8002` |
| `DEPS` | **必须一起启动的依赖** | Redis、Worker、MCP 等 |

**实线箭头**：正常下一步。**虚线箭头**：辅助关系或「在别的时间点触发」。

---

## 术语对照（图里英文是什么）

| 术语 | 通俗解释 |
|------|----------|
| **task_id** | Celery 任务编号；前端轮询进度用这个 id |
| **thread_id** | LangGraph 会话编号；**同一次投递**各段共用，checkpoint 靠它续跑 |
| **Celery Worker** | 后台干活的进程；不启动则 submit 会 503，任务一直排队 |
| **MCP Server** | 「数据库助手」服务；图里的节点不直接写 SQL，而是调 MCP 工具 |
| **LangGraph** | 把「取简历→优化→保存→…」编排成 **状态机/工作流** 的框架 |
| **Checkpointer** | 把图执行到一半的状态存进 SQLite；**中断后能接着跑** |
| **interrupt** | 工作流 **故意暂停**，等人确认（不是报错） |
| **astream** | 流式跑图（Celery 里用，边跑边更新进度） |
| **ainvoke** | 一次性跑图（你点「确认继续」后在 FastAPI 里用） |
| **Turn 1/2/3** | LangSmith 监控里的 **三段执行**；对应 1 次 astream + 最多 2 次 ainvoke |
| **localStorage** | 浏览器本地记录未完成任务；刷新页面后会 **接着轮询** 同一个 task_id |
| **UserResumeCache** | 表：某用户某职位 **已优化过的简历 id**；有则 mode=auto 可跳过 AI 优化 |

---

## 用户视角：完整时间线

```text
① 在职位页选简历 → 点「智能投递」
② 前端 POST submit → 立刻拿到 task_id、thread_id（此时 AI 还没跑完）
③ 顶部进度条轮询 status：
      - processing：Worker 正在跑（取简历、优化中…）
      - interrupted：等你审核 → 弹窗出现
④ 弹窗①：看 AI 优化后的简历 → 可改 JSON →「确认并继续」
⑤ 后台 Turn2：保存简历 → AI 写求职信 → 再次 interrupted
⑥ 弹窗②：看求职信 → 可改文字 →「确认并继续」
⑦ 后台 Turn3：写入投递记录 → status 变 success
⑧ 提示「投递成功」，任务从 localStorage 清除
```

若 `.env` 里 `SMART_APPLY_HUMAN_REVIEW=false`，则没有 ④⑤ 弹窗，① 提交后 Worker **一条道跑到底**。

---

## 智能投递功能流程图

```mermaid
flowchart TB
    START(["用户点击一键智能投递"]) --> PICK["弹窗选择一份简历"]
    PICK --> SUBMIT_FE["前端提交后台任务<br/>不阻塞页面"]

    SUBMIT_FE --> API_SUB["后端 API 接收投递请求"]
    API_SUB --> PRE1{"检查 Redis 和 Celery Worker 是否在线"}
    PRE1 -->|失败 503| ERR503["无法提交 提示先启动 Worker"]
    PRE1 -->|通过| PRE2{"检查 MCP 服务是否可用"}
    PRE2 -->|不可用| ERR503
    PRE2 -->|通过| BUILD_CHK["校验简历和缓存是否合法"]
    BUILD_CHK -->|404| ERR404["无可用简历或无可复用缓存"]
    BUILD_CHK -->|通过| CREATE_ROW["数据库记录本次投递任务"]
    CREATE_ROW --> DELAY["任务放入 Redis 队列"]
    DELAY --> REDIS_Q[("Redis 消息队列")]
    DELAY --> RET["返回 task_id 和 thread_id"]
    RET --> LS["浏览器保存任务 id 便于刷新恢复"]
    LS --> POLL["前端每隔几秒查一次进度"]

    subgraph STATUS["查询任务状态 API"]
        direction TB
        AR["读取 Celery 任务结果"] --> REDIS_R[("Redis 结果存储")]
        AR -->|PENDING 排队| ST_P["进行中 实际在等 Worker"]
        AR -->|PROGRESS 执行中| ST_R["进行中 显示百分比和阶段"]
        AR -->|SUCCESS 中断| ST_I["待审核 请打开弹窗确认"]
        AR -->|SUCCESS 完成| ST_OK["投递成功"]
        AR -->|FAILURE 失败| ST_E["投递失败"]
    end
    POLL --> STATUS
    POLL -->|待审核| REVIEW_UI

    subgraph REVIEW_UI["人工审核弹窗"]
        direction TB
        D1["读取工作流快照 含 AI 生成内容"]
        D1 --> D2{"当前要审什么?"}
        D2 -->|优化简历| D3["展示可编辑的简历 JSON"]
        D2 -->|求职信| D4["展示可编辑的求职信"]
        D3 --> CONF["用户点击确认并继续"]
        D4 --> CONF
        CONF --> RESUME_API["调用续跑 API 把修改一并提交"]
    end

    RESUME_API --> GRAPH_RESUME["FastAPI 从 checkpoint 接着跑图"]
    GRAPH_RESUME --> CHECK_INT{"是否 again 需要人工确认?"}
    CHECK_INT -->|是 还要审求职信| REVIEW_UI
    CHECK_INT -->|否 已全部完成| DONE_UI["提示成功 清除本地任务记录"]
    POLL -->|success| DONE_UI

    REDIS_Q --> WORKER["Celery Worker 取出任务执行"]
    WORKER --> LS_TRACE["开启 LangSmith 监控 可选"]
    WORKER --> BUILD_ST["构造图入口参数 initial_state"]
    BUILD_ST --> MODE{"投递模式与是否有缓存?"}

    MODE -->|复用已优化简历| ST_REUSE["标记跳过 AI 优化<br/>直接用缓存 resume_id"]
    MODE -->|需要重新生成| ST_NEW["标记走完整 AI 优化<br/>用用户选的 resume_id"]
    MODE -->|强制复用但无缓存| ST_ERR["任务失败 返回错误"]

    ST_REUSE --> TURN1
    ST_NEW --> TURN1

    subgraph TURN1["第一段 Celery 流式执行图"]
        direction TB
        CP1["状态写入 SQLite checkpoint 文件"] --> G1["加载 talentflow_smart_apply 工作流"]
        G1 --> N1["节点1 获取简历"]
        N1 --> MCP1["MCP 从数据库读简历内容"]
        MCP1 --> R1{"是否跳过 AI 优化?"}
        R1 -->|跳过 有缓存| N7B["直达节点7 保存投递"]
        R1 -->|需要优化| N2["节点2 AI 优化简历"]
        N2 --> LLM1["调用 DeepSeek 大模型"]
        LLM1 --> N3["节点3 人工审核简历"]
        N3 --> H1{"是否开启人工审核?"}
        H1 -->|是 默认| INT1["工作流暂停 等用户确认"]
        H1 -->|否| N4B["继续 不暂停"]
    end

    INT1 --> POLL
    TURN1 --> PROG["更新 Celery 进度条和数据库 stage"]

    subgraph TURN2["第二段 用户确认简历后继续"]
        direction TB
        N3R["带入用户修改的简历"] --> N4["节点4 保存优化简历到库"]
        N4 --> MCP2["MCP 写入新简历记录"]
        MCP2 --> N5["节点5 AI 生成求职信"]
        N5 --> LLM2["调用 DeepSeek 大模型"]
        LLM2 --> N6["节点6 人工审核求职信"]
        N6 --> H2{"是否开启人工审核?"}
        H2 -->|是| INT2["再次暂停 等确认求职信"]
        H2 -->|否| N7
    end

    RESUME_API -.->|第一次点确认| TURN2
    INT2 --> REVIEW_UI

    subgraph TURN3["第三段 用户确认求职信后"]
        direction TB
        N6R["带入用户确认的求职信"] --> N7["节点7 创建投递记录"]
        N7 --> MCP3["MCP 写入 applications 表"]
        MCP3 --> ENDG["完成 得到 application_id"]
    end

    RESUME_API -.->|第二次点确认| TURN3
    R1 -->|跳过优化路径| N7
    ENDG --> CACHE_UPD["更新 UserResumeCache 便于下次复用"]
    CACHE_UPD --> CELERY_OK["任务标记 SUCCESS"]
    CELERY_OK --> REDIS_R

    subgraph MCP_SRV["MCP 工具服务 端口 8002"]
        direction LR
        T1["读用户默认简历内容"]
        T2["按 id 读指定简历"]
        T3["保存 AI 优化后的简历"]
        T4["创建投递申请记录"]
    end
    MCP1 -.-> MCP_SRV
    MCP2 -.-> MCP_SRV
    MCP3 -.-> MCP_SRV

    subgraph DEPS["本地开发需同时启动"]
        direction LR
        D_M["MySQL 存简历和投递"]
        D_R["Redis 队列和结果"]
        D_C["Celery Worker 建议 pool solo"]
        D_P["MCP Server"]
        D_S["SQLite 存 LangGraph 断点"]
        D_L["LangSmith 可选 监控 AI"]
    end

    WORKER -.-> DEPS
    GRAPH_RESUME -.-> DEPS
```

> **说明：** 图中 `N7B` 为「跳过优化时」从节点 1 直接到节点 7 的捷径；正常完整路径经 Turn2、Turn3 到达 `N7`。

---

## 图上关键节点中文说明

### 提交前检查（不过就 503 / 404）

| 步骤 | 含义 | 常见失败原因 |
|------|------|--------------|
| Redis + Worker | 后台能不能接任务 | 没开 Celery 窗口 |
| MCP 预检 | 工具服务能不能查简历 | 没开 `python -m mcp_server.server` |
| build_initial_state | 简历 id、缓存是否合法 | 没选简历、force_reuse 却无缓存 |

### LangGraph 七个节点（按顺序）

| 节点 | 中文 | 输入 → 输出 |
|------|------|-------------|
| 1 fetch_resume | 取简历 | 用户 id → 简历正文、原始字段 |
| 2 optimize_resume | AI 改简历 | 简历 + 职位描述 → optimized_resume |
| 3 review_optimized_resume | 审简历 | **暂停**；用户确认后继续 |
| 4 save_optimized_resume | 存优化简历 | optimized_resume → 新 resume_id |
| 5 generate_letter | AI 写求职信 | 简历 + JD → cover_letter |
| 6 review_cover_letter | 审求职信 | **暂停**；用户确认后继续 |
| 7 save_record | 写投递单 | 求职信 + resume_id → application_id |

**捷径：** 若 `skip_generation=true`（复用缓存），节点 1 之后 **跳过 2～6**，直接到节点 7 只创建投递记录（仍会用已有 resume_id）。

### 状态轮询 status 返回值

| status | 用户看到什么 | 该做什么 |
|--------|--------------|----------|
| processing | 进度条在走 | 等待 |
| interrupted | 待审核 / 弹窗 | 打开审核，点确认 |
| success | 投递完成 | 无需操作 |
| error | 失败提示 | 看 message，检查 Worker/MCP 日志 |

---

## 三段执行（LangSmith Turn）详解

| 段 | 何时发生 | 谁执行 | 监控名称 | 跑到哪停 |
|----|----------|--------|----------|----------|
| Turn 1 | 点「投递」后 | Celery | smart_apply_astream | 默认停在「审简历」 |
| Turn 2 | 第一次点确认 | FastAPI | smart_apply_resume | 默认停在「审求职信」 |
| Turn 3 | 第二次点确认 | FastAPI | smart_apply_resume | 跑完，写入 applications |

关闭人工审核后，通常 **只有 Turn 1 一段**，Turn 2/3 不发生。

---

## 投递模式 mode（前端默认 auto）

| mode | 中文 | 行为 |
|------|------|------|
| `auto` | 自动 | 该职位 **有过优化缓存** → 跳过 AI 优化；否则完整生成 |
| `force_generate` | 强制生成 | 无视缓存，一定走 AI 优化 + 写信 |
| `force_reuse` | 强制复用 | 必须用缓存；没有则 **直接失败** |

---

## 为什么要 MCP，不直接在节点里写 SQL？

LangGraph 节点通过 **MCP 工具** 访问数据库，好处是：

- 工具接口固定（读简历、存简历、建申请），节点逻辑更清晰
- MCP 可单独启动、单独测；与 FastAPI、Celery 解耦
- 和智能体 / 外部调用方式统一

本地需单独开：`python -m mcp_server.server`（端口 8002）。

---

## 主要 API（路径前缀 `/api/v1/user`）

| 方法 | 路径 | 中文说明 |
|------|------|----------|
| GET | `smart-apply/readiness` | 自检 Redis、Worker、MCP 是否就绪 |
| POST | `smart-apply/submit` | 提交投递，返回 task_id、thread_id |
| GET | `smart-apply/status/{task_id}` | 查进度；interrupted 时含 review_type |
| GET | `smart-apply/thread/{thread_id}` | 读断点快照（弹窗加载 AI 内容） |
| POST | `smart-apply/thread/{thread_id}/resume` | 确认后续跑；body 可带用户修改 |

---

## 本地开发：最少要开几个窗口

```text
窗口1  Redis
窗口2  MCP Server      python -m mcp_server.server
窗口3  Celery Worker   celery -A app.core.celery_app worker --loglevel=info --pool=solo
窗口4  FastAPI         uvicorn app.main:app --reload --port 8000
```

缺 Worker → submit **503**；缺 MCP → submit **503** 或取简历失败；只有 FastAPI 时 **status 可能一直 200 但任务 PENDING**。

---

## 主要代码入口

| 环节 | 文件 |
|------|------|
| 前端任务与轮询 | `talentflow-ai-frontend/src/utils/smartApplyTaskRunner.js` |
| 审核弹窗 | `talentflow-ai-frontend/src/components/SmartApplyReviewDialog.vue` |
| API | `talentflow-ai-backend-bak/app/api/v1/user/smart_apply.py` |
| Celery 任务 | `talentflow-ai-backend-bak/app/services/smart_apply_service.py` |
| 工作流图定义 | `talentflow-ai-backend-bak/app/agents/graph.py` |
| 各节点实现 | `talentflow-ai-backend-bak/app/agents/nodes.py` |
| 断点续跑 | `talentflow-ai-backend-bak/app/agents/checkpoint_service.py` |
| MCP 工具 | `talentflow-ai-backend-bak/mcp_server/server.py` |

---

## 文档命名约定

- 文件名：`docs/{模块}-flow.md`
- 一级标题：`# {功能名}流程图`
- Mermaid 小节：`## {功能名}功能流程图`
