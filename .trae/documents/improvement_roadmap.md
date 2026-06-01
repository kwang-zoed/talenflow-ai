# TalentFlow AI 改进任务清单（分阶段）

> 基于架构梳理会话整理，按 **P0 → P1 → P2** 三阶段拆分。  
> 每阶段含：目标、任务、涉及文件、验收标准、依赖关系。

---

## 阶段一（P0）：稳定性与核心体验

**目标**：长耗时流程不拖垮 HTTP；依赖服务可一键启动；代码结构不再误导。

**预计周期**：1～2 周

---

### 1.1 智能投递异步化（对齐 Celery 模式）

| 项 | 内容 |
|----|------|
| **问题** | `/smart-apply` 同步 `ainvoke`，多轮 LLM 易超时 |
| **方案** | 参考 `job_recommend.py`：`submit` + `status/{task_id}` |

**任务清单**

- [x] **T1.1.1** 新增 Celery 任务 `smart_apply_task`（`app/services/smart_apply_service.py`）
  - 入参：`user_id`, `job_id`, `job_description`, `mode`, `resume_id`
  - 内部：`graph.astream` + `update_state` 按节点上报进度
  - 返回：`{ status, result: ApplyResponse 字段 }`

- [x] **T1.1.2** 新增 API（`app/api/v1/user/smart_apply.py`）
  - `POST /smart-apply/submit` → 返回 `task_id`
  - `GET /smart-apply/status/{task_id}` → `processing | success | error` + `data`
  - 原 `POST /smart-apply` 标记 `deprecated`

- [x] **T1.1.3** 成功后写 `user_resume_cache` 逻辑迁入 Worker

- [x] **T1.1.4** 前端 `JobList.vue` submit + 轮询，复用 `GlobalTaskProgress` 置顶进度条

**涉及文件**

- `app/services/recommendation_service.py` 或新建 `smart_apply_service.py`
- `app/core/celery_app.py`（`include` 新模块）
- `app/api/v1/user/smart_apply.py`
- 前端 API + 投递页组件

**验收标准**

- 提交后 1s 内返回 `task_id`
- 关闭页面后任务仍完成
- 成功响应字段与现 `ApplyResponse` 一致
- 失败时不留脏数据（回滚逻辑仍生效）

**依赖**：Celery Worker、Redis、MCP Server 已启动

---

### 1.2 统一部署与启动编排

| 项 | 内容 |
|----|------|
| **问题** | API / Celery / MCP 需分别手动起，易漏 |
| **方案** | Docker Compose + 环境变量统一配置 |

**任务清单**

- [x] **T1.2.1** 编写 `docker-compose.yml`（或扩展现有）
  - 服务：`backend`、`celery-worker`、`mcp-server`、`redis`、`mysql`、`frontend`
  - 根目录 `docker-compose.yml` + 后端 `Dockerfile`

- [x] **T1.2.2** 配置外置（`celery_app.py`、`config.py`）
  - Redis URL、MCP URL 从 `.env` 读取，去掉硬编码密码

- [x] **T1.2.3** 增加健康检查（部分）
  - MySQL / Redis / backend `GET /` healthcheck
  - 待补：`GET /health` 聚合 DB + Redis + MCP

- [x] **T1.2.4** 编写 `docs/DEPLOY.md`：本地 / Docker 启动顺序与常见问题

**验收标准**

- `docker compose up` 后推荐、解析、智能投递均可跑通
- 新成员按文档 15 分钟内起全栈

---

### 1.3 清理双套 Agent 代码 ✅

| 项 | 内容 |
|----|------|
| **问题** | `app/agent/` 与 `app/agents/` 并存，旧版含未接入的人工审核 |
| **方案** | 删除旧目录，单一入口 `app/agents/` |

**任务清单**

- [x] **T1.3.1** 确认 `app/agent/` 无 import 引用（`grep app.agent`）
- [x] **T1.3.2** 人工审核设计保留在 `smart_apply_plan.md`（P1 阶段用 Checkpointer + interrupt 实现）
- [x] **T1.3.3** 删除 `app/agent/` 下全部文件（graph / nodes / state / __init__）
- [x] **T1.3.4** 正式实现统一在 `app/agents/`（graph / nodes / state / edges）

**验收标准**

- 全项目仅 `app/agents/` 为智能投递实现
- `main.py`、API、Celery Worker 无旧路径引用

---

### 阶段一里程碑

| 交付物 | 说明 |
|--------|------|
| 智能投递 Celery 化 | submit + status，HTTP 不再长时间阻塞 |
| Docker Compose | API + Worker + MCP + Redis + MySQL 一键启动 |
| 旧 agent 清理 | 消除 `app/agent/` 与 `app/agents/` 混淆 |

**建议执行顺序（阶段内）**

1. T1.2 部署编排（先保证环境）
2. T1.3 清理旧代码
3. T1.1 智能投递 Celery + 前端轮询

---

## 阶段二（P1）：可恢复、可观测、数据一致

**目标**：工作流可查中间态；向量库可靠；前端异步体验统一。

**预计周期**：2～3 周（建议在 P0 稳定后进行）

---

### 2.1 LangGraph 任务状态与中断恢复

| 项 | 内容 |
|----|------|
| **问题** | 有 Checkpointer 但无查询/续跑 API |
| **方案** | 任务表 + Checkpointer +（可选）interrupt |

**任务清单**

- [x] **T2.1.1** 新建表 `apply_tasks`（或扩展现有 task 模型）
  - 字段：`id`, `user_id`, `job_id`, `thread_id`, `celery_task_id`, `stage`, `status`, `error`, `created_at`, `updated_at`
  - `stage` 枚举：`fetch_resume | optimize | save_resume | generate_letter | save_record | done`

- [x] **T2.1.2** 各节点入口/出口更新 `stage`（Worker 内或节点 wrapper）

- [x] **T2.1.3** 新增 API
  - `GET /smart-apply/tasks` 任务列表
  - `GET /smart-apply/thread/{thread_id}` 读 Checkpointer 快照（含 `stage`, `percent`）
  - `POST /smart-apply/thread/{thread_id}/resume` 断点续跑
  - `GET /smart-apply/status/{task_id}` 扩展返回 `thread_id` / `stage`
  - submit 响应增加 `thread_id`

- [x] **T2.1.4**（可选）人工审核
  - 在 `optimize_resume` / `generate_letter` 后加 `review_*` 节点 + `interrupt()`
  - `POST /smart-apply/thread/{thread_id}/resume` 带 `Command(resume=...)` 继续
  - 前端 `SmartApplyReviewDialog` 弹窗确认简历与求职信
  - 环境变量 `SMART_APPLY_HUMAN_REVIEW=true`（默认开启）可关闭人工审核

**涉及文件**

- `app/models/apply_task.py`（新建）
- `app/services/apply_task_service.py`（新建）
- `app/agents/checkpoint_service.py`（新建）
- `app/agents/graph.py`、`app/services/smart_apply_service.py`
- `app/api/v1/user/smart_apply.py`

**验收标准**

- 中断后可查：当前阶段、黑板关键字段（不含敏感信息）
- 续跑后从断点继续，不重复写库
- `thread_id = apply_{user_id}_{job_id}_{run_id}`（run_id 通常为 uuid 或 Celery task id）

---

### 2.2 向量库读写统一与重建工具

| 项 | 内容 |
|----|------|
| **问题** | 写入用内存单例，检索每次读盘；无 DB 同步 |
| **方案** | 统一 VectorStore 服务 + 管理接口 |

**任务清单**

- [ ] **T2.2.1** 重构 `vector_store.py`
  - 检索也走 `get_vectorstore()`，避免双路径
  - 写操作加文件锁或单 Writer 进程约定

- [ ] **T2.2.2** 新增 Admin API
  - `POST /admin/vector-store/rebuild`：从 `job_positions` 全量重建
  - `GET /admin/vector-store/stats`：`ntotal`、metadata 条数、与 DB count 对比

- [ ] **T2.2.3** 职位 CRUD 失败时告警（向量写入失败已有 log，可加 metrics/通知）

- [ ] **T2.2.4** 删除/更新职位时确保 `remove_job_from_vectorstore` 被调用（核对 admin/mentor 路由）

**验收标准**

- rebuild 后 FAISS 条数 = 有效职位数
- 并发创建 10 个职位无 index 损坏
- 检索与写入共用同一套加载逻辑

---

### 2.3 前端统一异步任务组件

| 项 | 内容 |
|----|------|
| **问题** | 解析/推荐/投递轮询逻辑分散或未接入 |
| **方案** | 通用 `pollTaskResult` + 全局进度条 |

**任务清单**

- [x] **T2.3.1** 封装 `src/utils/taskPoller.js`
  - 入参：`getStatus(taskId)`、指数退避、超时、`onProgress` 回调
  - 供 recommend / parse / smart-apply 共用

- [x] **T2.3.2** 组件 `GlobalTaskProgress.vue`（参考 `celery_parse_plan.md`）

- [x] **T2.3.3** 接入 Admin 职位解析、用户推荐、智能投递三处

- [x] **T2.3.4** 完成态：解析→填表单；推荐→刷新列表；投递→跳转申请记录

**验收标准**

- 三场景共用同一 poller，无重复 copy-paste
- 用户切页后顶部进度条仍可见（或任务中心可回看）

---

### 2.4 MCP 连接优化

**任务清单**

- [ ] **T2.4.1** `nodes.py` 中 MCP Client 改为模块级连接池或单例（注意 async 生命周期）
- [ ] **T2.4.2** 统一 `_parse_mcp_result` + 重试（3 次，指数退避）
- [ ] **T2.4.3** MCP 不可用时节点返回明确 `error_message`

**验收标准**

- 瞬时 MCP 失败可自动重试
- 错误信息对用户/日志可追踪

---

### 阶段二里程碑

| 交付物 | 说明 |
|--------|------|
| 任务状态 API | 可查智能投递进度与中间态 |
| 向量库 rebuild | Admin 一键修复不一致 |
| 前端 TaskPoller | 三业务场景统一异步 UX |
| MCP 重试 | 降低瞬时网络失败率 |

---

## 阶段三（P2）：规模、性能与工程化

**目标**：支撑更大数据量；调用链真正非阻塞；仓库与配置规范化。

**预计周期**：3～4 周（按业务量触发）

---

### 3.1 向量检索升级

**任务清单**

- [ ] **T3.1.1** 评估：职位 > 1 万时 `IndexFlatIP` 延迟基准测试
- [ ] **T3.1.2** 选型：FAISS `IndexIVFFlat` / Milvus / Qdrant / pgvector
- [ ] **T3.1.3** 抽象 `VectorStoreBackend` 接口，FAISS 作默认实现
- [ ] **T3.1.4** 迁移脚本：`index.faiss` → 新后端

**验收标准**：10 万职位下 P99 检索 < 200ms（或达到业务 SLA）

---

### 3.2 全链路异步化补全

**任务清单**

- [x] **T3.2.1** 简历解析 `/resumes/parse` → Celery submit/status
- [x] **T3.2.2** 废弃同步接口：`/jobs/parse`、`/recommend/{user_id}`（返回 410 或文档警告）
- [x] **T3.2.3** LLM 调用统一 `await llm.ainvoke()` 或全部放 Worker
- [x] **T3.2.4** Admin 查询接口完成 Async SQLAlchemy 迁移（按 `async_api_plan.md` 剩余项）

**验收标准**

- 无 `async def` 内同步 `llm.invoke` 的长耗时路径
- Celery `result_expires` 可配置（如 24h）

---

### 3.3 推荐链路优化

**任务清单**

- [ ] **T3.3.1** BM25 corpus 缓存（Redis/内存，职位变更时失效）
- [ ] **T3.3.2** Celery 返回结果用 Pydantic schema 序列化 job，去掉 `__dict__` 直出
- [ ] **T3.3.3** 生产环境 `PRELOAD_MODELS_ON_STARTUP=true` + 就绪探针等待预热

---

### 3.4 工程与仓库整理

**任务清单**

- [ ] **T3.4.1** `talentflow-ai-backend-bak` 重命名或合并为正式 `backend`
- [ ] **T3.4.2** `.gitignore`：`.env`、`*.sqlite`、`vector_store/` 大文件策略
- [ ] **T3.4.3** 补 `models/skills.py` 或删除空文件
- [ ] **T3.4.4** 核心路径集成测试：推荐 submit、解析 submit、智能投递 submit

---

### 阶段三里程碑

| 指标 | 目标 |
|------|------|
| 向量检索 | 支持 10 万级职位 |
| 同步长接口 | 全部迁移或废弃 |
| 仓库 | 单一 backend 目录 + CI 冒烟 |

---

## 跨阶段依赖关系

```
P0: T1.2 Docker 编排
  └─> T1.1 投递 Celery 化
        └─> P1: T2.1 状态与恢复
              └─> P1: T2.3 前端 Poller

P0: T1.3 清理旧 agent ──> P1: T2.1 中断恢复设计

P1: T2.2 向量库统一 ──> P2: T3.1 向量升级

P1: T2.3 前端 Poller ──> P2: T3.2 全链路异步
```

---

## 已知不足速查（问题来源）

| 模块 | 主要不足 |
|------|----------|
| 向量库 | IndexFlatIP 暴力检索；读写双路径；多进程写冲突 |
| MCP | 独立进程需手动启；每次新建 Client；无重试 |
| LangGraph | HTTP 同步阻塞；无 interrupt/resume API；双套 agent 代码 |
| Checkpointer | 有快照无恢复 API；与 MySQL 副作用割裂 |
| Celery | 仅推荐/解析异步；智能投递/简历解析仍阻塞 |
| 前端 | 轮询组件未统一接入 |
| 工程 | 硬编码 Redis 密码；backend-bak 命名；空 models/skills.py |

---

## 每个任务的 Definition of Done（通用）

1. 代码合并 + 本地/Docker 验证通过
2. 对应 API 在 Swagger 可测
3. 失败场景有日志且用户可见错误信息
4. 若改接口，前端或文档同步更新
5. 不提交 `.env`、密钥、大二进制模型到 git

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `async_api_plan.md` | Async SQLAlchemy 迁移计划 |
| `celery_parse_plan.md` | 文档解析 Celery + 前端轮询参考 |
| `smart_apply_plan.md` | 智能投递 LangGraph 原始设计 |
| `job_vector_store_plan.md` | FAISS 向量库实现计划 |
| `job_recommendation_plan.md` | 推荐链路设计 |

---

*最后更新：2026-05-31*
