# 职位推荐功能实现方案

## 1. 仓库研究结论

### 现有资源检查

| 模块/文件 | 状态 | 位置 |
|----------|------|------|
| **Embedding模型** | ✅ 已实现 | [`app/rag/embeddings.py`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/rag/embeddings.py) |
| **向量库(FAISS)** | ✅ 已实现 | [`app/rag/vector_store.py`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/rag/vector_store.py) |
| **Resume Model** | ✅ 已实现 | [`app/models/resume.py`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/models/resume.py) |
| **Job Model** | ✅ 已实现 | [`app/models/job_position.py`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/models/job_position.py) |
| **Retriever文件** | ❌ 需新建 | `app/rag/retriever.py` |
| **Reranker文件** | ❌ 需新建 | `app/rag/reranker.py` |
| **RecommendationService** | ❌ 需新建 | `app/services/recommendation_service.py` |
| **用户端API** | ❌ 需新增 | `app/api/v1/user/job_recommend.py` |

---

## 2. 需要创建/修改的文件

### 新建文件清单

```
app/
├── rag/
│   ├── retriever.py          # BM25+FAISS向量混合检索 get_hybrid_retriever
│   └── reranker.py           # bge-reranker-v2-m3 精排模型
└── services/
    └── recommendation_service.py  # RecommendationService类 + recommend_jobs方法
```

### 修改文件清单

| 文件 | 修改点 |
|------|--------|
| [`app/main.py`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/main.py) | 1. lifespan事件注册预加载模型<br>2. 注册用户端推荐API路由 |
| [`app/schemas/`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/schemas/) 目录下新增Schema文件 | **推荐接口的数据校验模型放在这里** |
| [`app/api/v1/user/resume_manage.py`](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/user/resume_manage.py) 或 新路由文件 | 新增 GET `/api/v1/user/recommend/{user_id}` |

---

## 3. 主要实现步骤

### 步骤1: 实现 `rag/retriever.py` 混合检索

```python
def get_hybrid_retriever():
    """
    初始化BM25检索器 + FAISS向量检索器
    返回: 混合检索对象
    """
    pass
```

**检索逻辑：**
- BM25检索（基于关键词匹配职位文本）
- FAISS向量检索（基于语义相似度）
- rag_score = BM25_score * 0.3 + vector_score * 0.7

---

### 步骤2: 实现 `rag/reranker.py` 精排模型

```python
from modelscope import AutoModelForSequenceClassification, AutoTokenizer

class BgeReranker:
    """本地加载 app/bge-reranker-v2-m3"""
    def __init__(self, model_path=None):
        pass
    
    def compute_score(self, query: str, passages: List[str]):
        """计算query-passage相关性分数"""
        pass
```

---

### 步骤3: 实现 RecommendationService 核心类

**文件：** `app/services/recommendation_service.py`

```python
class RecommendationService:
    """职位推荐服务"""
    
    def recommend_jobs(self, user_id: int, top_k: int = 5) -> List[Dict]:
        """
        主入口：返回给用户推荐的职位列表
        
        完整流程：
        1. 根据 user_id 查询 Resume（取 is_default=1 的默认简历，无默认则取最新）
        2. 从Resume表提取关键信息 → 构造检索查询文本 + 技能匹配集合
        3. BM25检索 + FAISS向量检索 → 合并去重召回一批候选职位
        4. 对候选统一粗排：粗排分 = (BM25*0.3 + 向量分*0.7)*0.7 + skill_scores*0.3
        5. 取粗排 Top N = top_k × 5 进入精排
        6. 用 bge-reranker-v2-m3 做精排重排序
        7. 返回 top_k 结果
        """
        pass
```

---

### 步骤3补充：Resume表用于检索的字段明细

| Resume字段 | 进BM25/向量检索文本 | 进skill_scores技能匹配 | 说明 |
|------------|---------------------|------------------------|------|
| `skills` (JSON数组) | ✅ 空格拼接进文本 | ✅ 主要来源 | 如: ["Python", "Flask", "MySQL"] |
| `title` | ✅ | ❌ | 求职意向/岗位名称 |
| `summary` | ✅ | ❌ | 个人简介大文本 |
| `project_experience` | ✅ | ❌ | 项目经验大文本 |
| `work_experience` | ✅ | ❌ | 工作经验大文本 |
| `education` | ✅ | ❌ | 学历 |
| `experience_years` | ✅ (数值转文本) | ❌ | 工作年限 |

**skill_scores匹配：**
- 取简历 `skills` 数组做成小写集合：`{"python", "flask", "mysql"}`
- 遍历每个职位的 `required_skills`，算交集数量除以总数量
- `skill_scores = 简历技能∩职位技能 / len(职位技能列表)`

---

### 步骤4: 关键得分算法

#### skill_scores 计算逻辑：
```
skill_scores = 简历上匹配到的岗位技能数量 / 该岗位要求的总技能数量
```

#### 两阶段排序（明确数量关系）：
| 阶段 | 数量关系 | 公式/说明 |
|------|---------|-----------|
| **粗排** | `粗排候选数 = 精排数 × 5` <br> top_k=5 → 粗排取25个 → 精排取5个 | `粗排分 = (BM25*0.3 + 向量分*0.7)*0.7 + skill_scores*0.3` <br> BM25/向量/技能三者合为一轮计算 |
| **精排** | 输入粗排Top 25，输出最终Top 5 | reranker模型对(query, 职位描述)相关性重新打分排序 |

---

### 步骤5: 模型预加载（服务启动时）

**文件：** `app/main.py` 的 `lifespan` 上下文管理器

```python
# main.py 内直接写，不新建models_loader.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动前预加载模型"""
    
    # 1. 预加载 embedding (app/bge-small-zh-v1.5-embedding)
    from app.rag.embeddings import embed_documents
    embed_documents(["warmup"])  # 触发初始化
    
    # 2. 预加载 reranker (app/bge-reranker-v2-m3)
    from app.rag.reranker import get_reranker
    _ = get_reranker()
    
    yield
```

**注意：** 不新建 `models_loader.py`，加载逻辑直接写在 `main.py` 里。

---

### 步骤6: 推荐接口Schema定义（schemas模块）

**文件：** `app/schemas/recommend_schema.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Any

# 请求/响应模型放在schemas模块，不写在路由里
class JobRecommendRequest(BaseModel):
    user_id: int
    top_k: int = Field(5, ge=1, le=20)

class JobRecommendItem(BaseModel):
    job_id: int
    title: str
    company: str
    final_score: Optional[float]
    rerank_score: Optional[float]
    # 其他职位字段...

class JobRecommendResponse(BaseModel):
    data: List[Any]
    count: int
```

---

### 步骤7: API接口实现

```python
# GET /api/v1/user/recommend/{user_id}?top_k=5

@router.get("/recommend/{user_id}", response_model=JobRecommendResponse)
def get_job_recommendations(
    user_id: int,
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(database.get_db),
    current_user = Depends(deps.get_current_user)
):
    service = RecommendationService(db)
    results = service.recommend_jobs(user_id, top_k)
    return {"data": results, "count": len(results)}
```

---

## 4. 依赖项与注意事项

| 依赖包 | 说明 |
|--------|------|
| `rank_bm25` | BM25关键词检索库 |
| `modelscope` 或 `transformers` | bge-reranker-v2-m3 模型加载 |
| `numpy` | 得分计算 |

---

## 5. 风险处理

| 风险 | 缓解方案 |
|------|---------|
| **模型加载超时/失败** | 加try-except，记录错误日志，不阻塞web服务启动 |
| **用户没有简历** | 返回空结果列表 + 友好提示 |
| **没有匹配职位** | 返回空结果 |
| **skill_scores 除零错误** | 当岗位技能列表为空时，skill_scores直接返回0 |
| **reranker模型报错** | 降级策略：跳过精排，直接返回粗排结果 |
