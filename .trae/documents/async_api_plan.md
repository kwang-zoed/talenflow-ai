# 查询类接口异步化实现计划（Async SQLAlchemy 方案）

> ✅ 已确认采用方案：**完整迁移 Async SQLAlchemy + asyncmy 驱动**\
> 技术路径：同步 SQLAlchemy ORM → Async SQLAlchemy 1.4+/2.0 异步语法\
> 前端适配：**零改动**，HTTP 响应完全兼容

***

## 方案总览

### 改造前技术栈

| 层级      | 实现                                 |
| ------- | ---------------------------------- |
| Driver  | `mysql+pymysql://`（同步）             |
| Engine  | `create_engine(...)`               |
| Session | `sessionmaker(...)`                |
| 查询语法    | `db.query(User).filter(...).all()` |
| 接口      | `def` 同步函数                         |

### 改造后技术栈

| 层级      | 实现                                                           |
| ------- | ------------------------------------------------------------ |
| Driver  | `mysql+asyncmy://`（异步）                                       |
| Engine  | `create_async_engine(...)`                                   |
| Session | `async_sessionmaker(..., class_=AsyncSession)`               |
| 查询语法    | `await db.execute(select(User).filter(...)).scalars().all()` |
| 接口      | `async def` 异步函数                                             |

***

## Phase 1: 核心基础设施改造（第一步）

### 1. database.py 异步引擎改造

**文件**: [database.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/core/database.py)

```python
# ========== 新增：完整异步实现 ==========
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker
)

# 同步 URL 转异步 URL: pymysql -> asyncmy
ASYNC_DATABASE_URL = DATABASE_URL.replace("pymysql", "asyncmy")

# 异步引擎（和同步引擎双轨，逐步迁移）
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# FastAPI 异步依赖注入（替代原 def get_db）
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 2. deps.py 依赖改造

**文件**: [deps.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/core/deps.py)

```python
# get_current_user 支持 AsyncSession 兼容
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db = Depends(get_async_db)  # or Depends(get_db) 双兼容
):
    ...
```

***

## Phase 2: CRUD 查询语法迁移对照表

**文件**: [crud.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/crud/crud.py)

### 同步 vs 异步查询语法差异

| 操作        | 同步                                           | 异步                                                                                       |
| --------- | -------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **列表查询**  | `db.query(User).offset(n).all()`             | `(await db.execute(select(User).offset(n))).scalars().all()`                             |
| **单条查询**  | `db.query(User).filter(User.id==id).first()` | `(await db.execute(select(User).filter(User.id==id))).scalar_one_or_none()`              |
| **Count** | `db.query(User).count()`                     | `(await db.execute(select(func.count()).select_from(select(User).subquery()))).scalar()` |
| **提交事务**  | `db.commit()`                                | `await db.commit()`                                                                      |

***

## Phase 3: 接口层 def → async def 迁移清单

### Admin 模块（优先级高）

| 文件                                                                                                                          | 接口                      | 当前状态                       | 依赖                                          |
| --------------------------------------------------------------------------------------------------------------------------- | ----------------------- | -------------------------- | ------------------------------------------- |
| [user\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/user_manage.py)     | `GET /admin/users`      | `def get_users(...)`       | Depends(get\_async\_db) + await crud\_async |
| [user\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/user_manage.py)     | `GET /admin/users/{id}` | `def get_user_detail(...)` | 同上                                          |
| [task\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/task_manage.py)     | `GET /admin/tasks`      | `def get_tasks(...)`       | 同上                                          |
| [task\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/task_manage.py)     | `GET /admin/tasks/{id}` | `def get_task(...)`        | 同上                                          |
| [job\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/job_manage.py)       | `GET /admin/jobs`       | `def read_jobs(...)`       | 同上                                          |
| [job\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/job_manage.py)       | `GET /admin/jobs/{id}`  | `def get_job(...)`         | 同上                                          |
| [resume\_manage.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/resume_manage.py) | `GET /admin/resumes`    | `def`                      | 同上                                          |
| [get\_dashboard.py](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/admin/get_dashboard.py) | `GET /admin/dashboard`  | `def`                      | 同上                                          |

### User & Mentor 模块

| 文件                                                                                                                                | 主要接口                    | 当前状态  |
| --------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----- |
| [task\_manage.py (user)](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/user/task_manage.py)     | `GET /user/tasks`       | `def` |
| [resume\_manage.py (user)](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/user/resume_manage.py) | `GET /user/resumes`     | `def` |
| [task\_manage.py (mentor)](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/mentor/task_manage.py) | `GET /mentor/tasks`     | `def` |
| [dashboard.py (mentor)](file:///c:/Users/kzd/Desktop/talentflow-ai/talentflow-ai-backend-bak/app/api/v1/mentor/dashboard.py)      | `GET /mentor/dashboard` | `def` |

***

## 迁移前后对比（代码片段）

### 迁移前

```python
@router.get("/users")
def get_users(
    skip: int = Query(0),
    limit: int = Query(10),
    db: Session = Depends(get_db)
):
    users, total = crud.read_users(db, skip, limit)
    result = [user_to_dict(user) for user in users]
    return result
```

### 迁移后

```python
@router.get("/users")
async def get_users(
    skip: int = Query(0),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_async_db)
):
    users, total = await crud.read_users_async(db, skip, limit)
    result = [user_to_dict(user) for user in users]
    return result
```

***

## 验证与回滚

### 验证标准（每改造完一个模块）

1. `/docs` Swagger UI 可正常执行 `Try it out`，响应 200
2. 前端页面列表、详情页功能无异常
3. `response.json()` 结构与改造前完全一致

### 回滚方案（遇阻时）

| 层级          | 回滚点                                          |
| ----------- | -------------------------------------------- |
| database.py | 同步 engine + `get_db()` 保留未删，可随时切回            |
| crud.py     | 同步函数保留，新增 `*_async` 后缀区分                     |
| 接口          | `Depends(get_async_db)` 切回 `Depends(get_db)` |

***

## 前端影响结论

✅ **无影响：前端一行都不用改！**

* HTTP 方法、URL、请求参数不变

* 响应 JSON schema 不变

* 仅变化：Server 端处理并发的内部实现机制

