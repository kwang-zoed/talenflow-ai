# 职位推荐序列图

> 预览：安装 **Markdown Preview Mermaid Support**，打开本文件 `Ctrl+Shift+V`；或复制 `mermaid` 到 [Mermaid Live Editor](https://mermaid.live)。  
> 配套活动流程图：[recommend-flow.md](./recommend-flow.md)

---

## 30 秒读懂

用户在 **JobCockpit** 打开推荐页 → 前端 `POST recommend/submit` 拿到 `task_id` → **Celery Worker** 读默认简历、混合检索、精排 → 前端轮询 `GET recommend/status/{task_id}` 直到 `success` → 结果写入 `sessionStorage` 并渲染卡片。

---

## 职位推荐交互序列图

```mermaid
sequenceDiagram
    autonumber
    actor U as 求职者
    participant FE as JobCockpit
    participant API as FastAPI
    participant RQ as Redis 队列
    participant RB as Redis Result
    participant WK as Celery Worker
    participant SVC as RecommendationService
    participant DB as MySQL
    participant RET as HybridRetriever
    participant VS as FAISS 索引
    participant RR as BGE Reranker

    U->>FE: 打开职位驾驶舱
    FE->>FE: 检查 sessionStorage 缓存

    alt 10 分钟内有效缓存
        FE->>FE: 直接渲染 recommendedJobs
    else 无缓存或强制刷新
        FE->>API: POST /api/v1/user/recommend/submit
        Note right of FE: body user_id top_k=5 JWT
        API->>RQ: generate_recommendation_task.delay
        API-->>FE: task_id
        FE->>FE: sessionStorage 保存 task_id

        loop pollRecommendResult 最长 120s
            FE->>API: GET /user/recommend/status/{task_id}
            API->>RB: AsyncResult 读任务状态
            alt PENDING 或 PROGRESS
                API-->>FE: status=processing
            else SUCCESS
                API-->>FE: status=success data=职位列表
            else FAILURE
                API-->>FE: status=error message
            end
        end

        RQ->>WK: 消费推荐任务
        WK->>SVC: recommend_jobs(user_id, top_k)
        SVC->>DB: 查询用户默认简历
        DB-->>SVC: Resume 记录
        SVC->>SVC: extract_user_resume_info 拼 search_text

        SVC->>RET: hybrid_search(search_text, coarse_count)
        RET->>DB: 加载职位元数据
        RET->>VS: FAISS 向量近邻
        RET->>RET: BM25 关键词打分
        RET-->>SVC: 合并候选 rag_score

        SVC->>SVC: 技能匹配加权 final_score 粗排
        SVC->>RR: compute_score 精排 top 候选
        RR-->>SVC: rerank_score
        SVC-->>WK: top_k 职位列表
        WK->>RB: 写入 SUCCESS 结果

        FE->>FE: sessionStorage 保存 result
        FE->>U: 渲染推荐卡片
    end
```

---

## Worker 内检索步骤（对照序列图 25～32 步）

| 顺序 | 组件 | 动作 |
|------|------|------|
| 1 | MySQL | 取用户默认简历 |
| 2 | HybridRetriever | BM25 + FAISS 混合召回 `top_k × 5` 条 |
| 3 | RecommendationService | 技能交集算 `skill_score`，与 `rag_score` 融合 |
| 4 | BGE Reranker | 对粗排结果精排 |
| 5 | Celery | 返回 `{ status: success, result: [...] }` |

---

## 关键 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/user/recommend/submit` | 提交异步推荐，返回 `task_id` |
| GET | `/api/v1/user/recommend/status/{task_id}` | 轮询：`processing` / `success` / `error` |

---

## 与其它文档

| 文档 | 区别 |
|------|------|
| [recommend-flow.md](./recommend-flow.md) | 活动图：缓存分支、进度条、评分公式 |
| **本文件** | 序列图：前端 ↔ API ↔ Worker ↔ 检索组件时序 |

---

## 文档命名约定

- 文件名：`docs/recommend-sequence.md`
- 一级标题：`# 职位推荐序列图`
- 图表小节：`## 职位推荐交互序列图`
