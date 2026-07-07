# 职位推荐流程图

> 预览：在 Cursor / VS Code 中安装 **Markdown Preview Mermaid Support**，打开本文件后使用 Markdown 预览（`Ctrl+Shift+V`）。  
> 也可复制下方 `mermaid` 代码块到 [Mermaid Live Editor](https://mermaid.live) 导出 PNG/SVG。  
> 状态转换见 [recommend-state.md](./recommend-state.md)。

**Mermaid 写法注意：** 节点文字里避免未加引号的 `[` `]`、`/`、`:`、`|×` 等，否则会被当成语法解析。公式细节见下方「评分公式」表，图内用简写标签。

---

## 职位推荐功能流程图

```mermaid
flowchart TB
    START(["用户打开 JobCockpit 职位驾驶舱"]) --> LOGIN{"已登录?<br/>userStore.userInfo.id"}
    LOGIN -->|否| TO_LOGIN["跳转登录页"]
    LOGIN -->|是| CACHE_CHECK

    CACHE_CHECK{"sessionStorage 缓存<br/>result + time<br/>10 分钟内有效?"}
    CACHE_CHECK -->|是且非强制刷新| SHOW_CACHE["直接渲染 recommendedJobs"]
    CACHE_CHECK -->|否| TASK_CHECK

    TASK_CHECK{"sessionStorage 有 task_id?"}
    TASK_CHECK -->|有| STATUS_ONCE["GET recommend status"]
    STATUS_ONCE -->|success| USE_OLD["写缓存并展示列表"]
    STATUS_ONCE -->|processing| POLL
    STATUS_ONCE -->|error| SUBMIT
    TASK_CHECK -->|无| SUBMIT

    REFRESH(["用户点击刷新"]) --> CLEAR["clearCache 取消轮询"]
    CLEAR --> SUBMIT

    SUBMIT["POST recommend submit<br/>user_id top_k=5 JWT"] --> DELAY["generate_recommendation_task.delay"]
    DELAY --> REDIS_Q[("Redis db0 Celery 队列")]
    DELAY --> RET_TID["返回 task_id"]
    RET_TID --> SAVE_TID["sessionStorage 保存 task_id"]

    SAVE_TID --> POLL["pollRecommendResult 轮询<br/>最长 120 秒"]
    POLL --> PROGRESS["GlobalTaskProgress 进度条"]
    POLL -->|processing| POLL
    POLL -->|error| ERR["ElMessage 报错"]
    POLL -->|success| SAVE_RES["sessionStorage 保存 result"]
    SAVE_RES --> RENDER["渲染推荐卡片列表"]

    subgraph STATUS_API["FastAPI 状态查询"]
        direction TB
        AR["AsyncResult task_id"] --> REDIS_R[("Redis db1 Result")]
        AR -->|PENDING| ST_PROC["status processing"]
        AR -->|SUCCESS| ST_OK["status success"]
        AR -->|FAILURE| ST_ERR["status error"]
    end
    POLL -.-> AR

    REDIS_Q --> WORKER["Celery Worker 消费任务"]
    WORKER --> DB_OPEN["SessionLocal MySQL"]
    DB_OPEN --> REC["RecommendationService.recommend_jobs"]

    REC --> GET_RESUME["get_user_resume"]
    GET_RESUME --> DEF{"默认简历 is_default=1?"}
    DEF -->|有| EXTRACT
    DEF -->|无| ANY["取任意一份简历"]
    ANY --> NO_RESUME{"有简历?"}
    NO_RESUME -->|否| EMPTY["返回空数组"]
    NO_RESUME -->|是| EXTRACT

    EXTRACT["extract_user_resume_info"] --> SEARCH_TEXT["search_text 拼接简历字段"]
    EXTRACT --> USER_SKILLS["user_skills 技能集合"]

    SEARCH_TEXT --> COARSE["coarse_count = top_k x 5"]
    USER_SKILLS --> COARSE

    COARSE --> HYBRID

    subgraph HYBRID["混合召回 get_hybrid_retriever"]
        direction TB
        LOAD_JOBS["MySQL 加载 job_positions"] --> BM25_BUILD["构建 BM25 语料"]
        LOAD_JOBS --> JOBS_MAP["job_id 映射表"]

        SEARCH_TEXT --> FAISS_Q
        SEARCH_TEXT --> BM25_Q

        FAISS_Q["bge-small-zh embed_query"] --> FAISS_READ[("index.faiss")]
        FAISS_READ --> FAISS_TOP["FAISS Top-K"]

        BM25_BUILD --> BM25_Q["BM25 Top-K"]
        BM25_Q --> BM25_TOP["BM25 分数"]

        FAISS_TOP --> NORM["Min-Max 归一化"]
        BM25_TOP --> NORM
        NORM --> MERGE["job_id 并集"]
        MERGE --> RAG_SCORE["rag = BM25x0.3 + FAISSx0.7"]
        RAG_SCORE --> TOP_COARSE["Top coarse_count"]
        JOBS_MAP --> TOP_COARSE
    end

    TOP_COARSE --> COARSE_RANK

    subgraph COARSE_RANK["粗排融合"]
        direction TB
        FOR_EACH["遍历候选"] --> JOB_SKILLS["解析 required_skills"]
        JOB_SKILLS --> SKILL_SCORE["skill_score 技能交集比"]
        SKILL_SCORE --> FINAL_COARSE["final = ragx0.7 + skillx0.3"]
        FINAL_COARSE --> SORT1["按 final_score 降序"]
    end

    SORT1 --> RERANK_CHECK{"Reranker 已加载?"}

    RERANK_CHECK -->|是| PASSAGES["拼接职位文本 截断1000字"]
    PASSAGES --> RERANK_SCORE["BGE Reranker compute_score"]
    RERANK_SCORE --> SORT2["按 rerank_score 降序"]
    RERANK_CHECK -->|否| SKIP_RERANK["跳过精排"]

    SORT2 --> TOPK
    SKIP_RERANK --> TOPK

    TOPK["取 Top top_k"] --> BUILD_RES["组装 job score matched_skills"]
    BUILD_RES --> CELERY_RET["Celery SUCCESS 写回 Redis"]
    CELERY_RET --> REDIS_R

    EMPTY --> CELERY_RET

    subgraph OFFLINE["离线建库 HR 发布职位"]
        direction LR
        HR_CREATE["创建导入职位"] --> MYSQL_JOBS[("MySQL job_positions")]
        HR_CREATE --> VS_ADD["add_job_to_vectorstore"]
        VS_ADD --> VS_TEXT["拼接职位全文"]
        VS_TEXT --> VS_EMB["bge-small-zh embed"]
        VS_EMB --> VS_WRITE["写入 index.faiss"]
    end

    VS_WRITE -.-> FAISS_READ
    MYSQL_JOBS -.-> LOAD_JOBS

    RENDER --> USER_ACT{"用户操作"}
    USER_ACT -->|一键投递| SMART_APPLY["智能投递 submit"]
    USER_ACT -->|刷新| REFRESH
    USER_ACT -->|浏览| DONE(["结束"])
```

---

## 评分公式

| 阶段 | 公式 |
|------|------|
| 混合召回 | `rag_score = BM25_norm×0.3 + FAISS_norm×0.7` |
| 粗排融合 | `final_score = rag_score×0.7 + skill_score×0.3` |
| 技能匹配 | `skill_score = 技能交集数 / 职位技能数` |
| 展示分 | `score = int(final_score × 100)` |

## 主要代码入口

| 环节 | 文件 |
|------|------|
| 前端 | `talentflow-ai-frontend/src/views/user/dashboard/JobCockpit.vue` |
| API | `talentflow-ai-backend-bak/app/api/v1/user/job_recommend.py` |
| Celery 任务 | `talentflow-ai-backend-bak/app/services/recommendation_service.py` |
| 混合检索 | `talentflow-ai-backend-bak/app/rag/retriever.py` |
| 向量 / 精排 | `embeddings.py` / `reranker.py` / `vector_store.py` |

---

## 文档命名约定

后续流程图 Markdown 建议统一命名：

- 文件名：`docs/{模块}-flow.md`（如 `smart-apply-flow.md`）
- 一级标题：`# {功能名}流程图`
- Mermaid 小节标题：`## {功能名}功能流程图`（格式：**xx功能xx图**）
