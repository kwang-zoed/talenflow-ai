# 功能结构图

> 预览：安装 **Markdown Preview Mermaid Support**，打开本文件 `Ctrl+Shift+V`；或复制 `mermaid` 到 [Mermaid Live Editor](https://mermaid.live)。

---

## 项目功能结构树图

> **答辩 / 说明书推荐用这一张。** 按 **平台 → 终端 → 功能模块 → 具体功能** 四级树状分解，版式接近常见项目结构图（根在上、叶子在下）。  
> 配色：**深色文字 + 浅色底**，白底预览可读；五端用不同色区分。

```mermaid
flowchart TB
    ROOT["TalentFlow-AI 智能招聘平台"]

    ROOT --> PUB["公共模块"]
    ROOT --> U["学生/求职者端"]
    ROOT --> HR["导师/HR端"]
    ROOT --> AD["管理员端"]
    ROOT --> CAP["平台能力层"]

    PUB --> P_M["认证与权限"]
    P_M --> P1["用户登录"] & P2["用户注册"] & P3["JWT鉴权"] & P4["角色分流"]

    U --> U_M1["蒲公英成长中心"]
    U --> U_M2["求职与投递"]
    U --> U_M3["门户展示页"]

    U_M1 --> U1["任务大厅"] & U2["任务详情"] & U3["接取任务"]
    U_M2 --> U4["简历管理"] & U5["浏览职位"] & U6["AI职位推荐"] & U7["智能投递"] & U8["审核确认"] & U9["我的投递"]
    U_M3 --> U10["广场"] & U11["充电站"] & U12["创业页"]

    HR --> H_M1["工作台看板"]
    HR --> H_M2["职位管理"]
    HR --> H_M3["培训任务"]
    HR --> H_M4["投递审核"]

    H_M1 --> H1["数据概览"] & H2["待办动态"]
    H_M2 --> H3["职位CRUD"] & H4["JD文档解析"]
    H_M3 --> H5["任务发布"] & H6["任务管理"]
    H_M4 --> H7["申请列表"] & H8["简历查看"] & H9["通过拒绝"] & H10["状态更新"]

    AD --> A_M1["数据看板"]
    AD --> A_M2["用户管理"]
    AD --> A_M3["职位管理"]
    AD --> A_M4["简历管理"]
    AD --> A_M5["项目管理"]

    A_M1 --> A1["运营统计"] & A2["多维分析"]
    A_M2 --> A3["用户CRUD"] & A4["封禁激活"]
    A_M3 --> A5["全站职位"] & A6["JD批量解析"]
    A_M4 --> A7["简历库维护"] & A8["简历解析"]
    A_M5 --> A9["项目CRUD"]

    CAP --> C_M1["职位推荐"]
    CAP --> C_M2["智能投递"]
    CAP --> C_M3["文档解析"]
    CAP --> C_M4["基础设施"]

    C_M1 --> C1["混合检索"] & C2["BM25"] & C3["FAISS"] & C4["BGE精排"]
    C_M2 --> C5["LangGraph"] & C6["人工中断"] & C7["MCP读写库"]
    C_M3 --> C8["职位JD解析"] & C9["简历解析"]
    C_M4 --> C10["MySQL"] & C11["Redis Celery"] & C12["向量索引"] & C13["Docker部署"]

    classDef root fill:#2563eb,color:#ffffff,stroke:#1d4ed8,stroke-width:2px
    classDef pubT fill:#ede9fe,color:#5b21b6,stroke:#7c3aed,stroke-width:2px
    classDef userT fill:#dbeafe,color:#1e40af,stroke:#2563eb,stroke-width:2px
    classDef hrT fill:#d1fae5,color:#065f46,stroke:#059669,stroke-width:2px
    classDef adminT fill:#ffedd5,color:#9a3412,stroke:#ea580c,stroke-width:2px
    classDef capT fill:#ccfbf1,color:#115e59,stroke:#0d9488,stroke-width:2px
    classDef module fill:#f3f4f6,color:#111827,stroke:#6b7280,stroke-width:1px
    classDef leaf fill:#fef3c7,color:#78350f,stroke:#d97706,stroke-width:1px

    class ROOT root
    class PUB pubT
    class U userT
    class HR hrT
    class AD adminT
    class CAP capT
    class P_M,U_M1,U_M2,U_M3,H_M1,H_M2,H_M3,H_M4,A_M1,A_M2,A_M3,A_M4,A_M5,C_M1,C_M2,C_M3,C_M4 module
    class P1,P2,P3,P4,U1,U2,U3,U4,U5,U6,U7,U8,U9,U10,U11,U12,H1,H2,H3,H4,H5,H6,H7,H8,H9,H10,A1,A2,A3,A4,A5,A6,A7,A8,A9,C1,C2,C3,C4,C5,C6,C7,C8,C9,C10,C11,C12,C13 leaf
```

---

## 系统功能结构图

> **说明：** 按 **业务子系统 → 功能模块 → 具体功能** 三级展开；最下方 **平台能力层** 为各业务共用的 AI / 任务 / 数据能力（不是单独菜单，但在结构中单独列出便于理解）。

```mermaid
mindmap
  root((TalentFlow AI\n智能招聘平台))
    公共模块
      用户登录
      用户注册
      角色分流
        求职者
        平台管理员
        HR导师
    求职者端
      蒲公英成长中心
        成长任务大厅
        任务详情
        接取任务
      求职与投递
        简历管理
        浏览职位列表
        AI职位推荐
        智能投递
        人工审核确认
        我的投递记录
      门户展示页
        广场
        充电站
        创业页
    平台管理端
      运营数据看板
      用户管理
      全站职位管理
      职位文档解析
      简历库管理
      简历文档解析
      项目管理
    HR导师端
      HR工作台
      本机构职位管理
      培训任务管理
      投递申请管理
      投递简历查看
      投递状态处理
    平台能力层
      职位混合检索
        BM25关键词
        FAISS向量
        BGE精排
      智能投递引擎
        LangGraph工作流
        断点续跑
        MCP读写库
      文档智能解析
        职位JD解析
        简历解析
      异步任务调度
      AI大模型服务
      可观测监控
    基础设施
      MySQL数据库
      Redis与Celery
      向量索引库
      Docker部署
```

---

## 分层功能结构图

> 从 **用户看到的** 到 **底层支撑的** 四层关系（与上一张 mindmap 互补）。

```mermaid
flowchart TB
    subgraph L1["表现层 Web 前端"]
        FE_A["管理端 admin"]
        FE_H["HR 端 hr"]
        FE_U["求职者端 dashboard"]
        FE_P["登录注册"]
    end

    subgraph L2["业务服务层 FastAPI"]
        API_AUTH["认证 auth"]
        API_ADMIN["admin 用户职位简历项目统计"]
        API_HR["mentor hr 职位任务投递"]
        API_USER["user 简历任务推荐投递智能投递"]
    end

    subgraph L3["平台能力层"]
        CAP_REC["职位推荐服务\n混合检索加精排"]
        CAP_APPLY["智能投递服务\nLangGraph加Celery"]
        CAP_PARSE["文档解析服务\nCelery加LLM"]
        CAP_MCP["MCP 工具服务"]
    end

    subgraph L4["数据与基础设施"]
        DB[("MySQL")]
        RD[("Redis Celery")]
        VS[("FAISS 向量库")]
        AI["DeepSeek 等 AI"]
    end

    FE_P --> API_AUTH
    FE_U --> API_USER
    FE_A --> API_ADMIN
    FE_H --> API_HR

    API_USER --> CAP_REC
    API_USER --> CAP_APPLY
    API_ADMIN --> CAP_PARSE
    API_HR --> CAP_PARSE
    CAP_APPLY --> CAP_MCP
    CAP_REC --> VS
    CAP_REC --> AI
    CAP_APPLY --> AI
    CAP_PARSE --> AI

    API_AUTH --> DB
    API_ADMIN --> DB
    API_HR --> DB
    API_USER --> DB
    CAP_REC --> DB
    CAP_APPLY --> RD
    CAP_PARSE --> RD
    CAP_MCP --> DB
```

---

## 三级功能分解表

### 1. 公共模块

| 二级 | 三级功能 | 前端 | 后端 |
|------|----------|------|------|
| 认证 | 登录 | `LoginView` | `api/v1/auth/login` |
| 认证 | 注册 | `LoginView` | `api/v1/auth/register` |
| 认证 | 按角色跳转 | `router` 守卫 | JWT `role` 0/1/2 |

### 2. 求职者端

| 二级 | 三级功能 | 前端 | 后端 |
|------|----------|------|------|
| 简历 | 列表/增删改/默认 | `ResumeManager` | `api/v1/resume/*` |
| 职位 | 职位列表 | `JobList` | `user/job-list` |
| 推荐 | AI 职位推荐 | `JobCockpit` | `user/recommend/submit` |
| 投递 | 智能投递 | `JobCockpit` `JobList` | `user/smart-apply/*` |
| 投递 | 人工审核 | `SmartApplyReviewDialog` | `thread/resume` |
| 投递 | 我的投递 | `Applications` | `user/applications` |
| 任务 | 大厅/详情/接单 | `TaskBoard` `TaskDetail` | `user/tasks/*` |
| 门户 | 广场等展示页 | `Square` 等 | — |

### 3. 平台管理端

| 二级 | 三级功能 | 前端 | 后端 |
|------|----------|------|------|
| 统计 | 运营看板 | `admin/Dashboard` | `admin/stats/*` |
| 用户 | 用户管理 | `admin/Users` | `admin/users/*` |
| 职位 | 全站 CRUD | `admin/Jobs` | `admin/jobs/*` |
| 职位 | 文档解析 | `admin/Jobs` | `admin/jobs/parse/submit` |
| 简历 | 简历库 CRUD | `admin/Resumes` | `admin/resumes/*` |
| 简历 | 文档解析 | `admin/Resumes` | `admin/resumes/parse/submit` |
| 项目 | 项目管理 | `admin/Projects` | `admin/projects/*` |

### 4. HR/导师端

| 二级 | 三级功能 | 前端 | 后端 |
|------|----------|------|------|
| 工作台 | 统计与动态 | `hr/Dashboard` | `mentor/dashboard/*` |
| 职位 | 本机构职位 | `hr/HrJobs` | `mentor/jobs/*` |
| 职位 | 文档解析 | `hr/HrJobs` | 同 admin 解析任务 |
| 任务 | 培训任务 | `hr/Task` | `mentor/tasks/*` |
| 投递 | 申请列表 | `hr/Applications` | `mentor/applications` |
| 投递 | 简历预览 | 同上 | `applications/{id}/resume` |
| 投递 | 状态处理 | 同上 | `PATCH process` |

### 5. 平台能力层（无独立菜单，支撑上层）

| 能力模块 | 包含功能 | 主要代码 |
|----------|----------|----------|
| 职位推荐 | 读简历、混合检索、精排、异步任务 | `recommendation_service` `rag/retriever` |
| 智能投递 | LangGraph 七节点、人工中断、Celery、MCP | `agents/` `smart_apply_service` |
| 文档解析 | PDF/Word 抽取、LLM 结构化 | `recommendation_service.parse_*` |
| MCP 工具 | 读简历、存简历、建申请 | `mcp_server/server.py` |
| 向量库 | 职位 embedding、FAISS 索引 | `rag/vector_store` |
| 监控 | LangSmith trace | `langsmith_tracing.py` |

---

## 与其它文档的关系

| 文档 | 内容 |
|------|------|
| **本文件** | 系统 **有哪些功能模块**、怎么分层 |
| [use-case.md](./use-case.md) | **谁** 使用这些功能（用例图） |
| [recommend-flow.md](./recommend-flow.md) | 职位推荐 **怎么跑**（活动图） |
| [recommend-sequence.md](./recommend-sequence.md) | 职位推荐 **谁调谁**（序列图） |
| [recommend-state.md](./recommend-state.md) | 职位推荐 **在什么状态**（状态图） |
| [smart-apply-flow.md](./smart-apply-flow.md) | 智能投递 **怎么跑**（活动图） |
| [smart-apply-sequence.md](./smart-apply-sequence.md) | 智能投递 **谁调谁**（序列图） |
| [smart-apply-state.md](./smart-apply-state.md) | 智能投递 **状态转换**（状态图） |
| [parse-sequence.md](./parse-sequence.md) | 文档解析时序 |
| [auth-sequence.md](./auth-sequence.md) | 登录注册与角色分流时序 |
| [database-er.md](./database-er.md) | MySQL 实体关系图（ER） |

---

## 读图提示

1. **项目功能结构树图（第一张）**：答辩/说明书用的 **四级树状分解**（终端 → 模块 → 功能），与代码功能一致。  
2. **mindmap（第二张）**：同一内容的 **放射状** 总览，适合快速浏览。  
3. **flowchart 分层图（第三张）**：**前端 / API / 能力 / 存储** 四层依赖。  
4. **表格**：与代码目录对照，查功能在哪个 Vue 页面、哪个 API 路由。

---

## 文档命名约定

- 文件名：`docs/function-structure.md`
- 一级标题：`# 功能结构图`
- 树图小节：`## 项目功能结构树图`
- Mindmap 小节：`## 系统功能结构图`
