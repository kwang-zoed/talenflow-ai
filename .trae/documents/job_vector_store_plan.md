# 职位向量库功能实现计划

## 需求分析

用户需要在admin端创建新职位时，将职位关键检索信息存入FAISS向量库：
- 使用 `bge-small-zh-v1.5-embedding` 模型计算向量
- 使用FAISS实现向量存储，**使用IndexFlatIP支持余弦相似度**
- **向量维度：512维**
- metadata存入 `.pkl` 文件，向量索引存入 `index.faiss` 文件
- **增加调试代码，确保全流程顺畅**

## 现有资源

| 文件 | 状态 | 说明 |
|------|------|------|
| `app/rag/embeddings.py` | 空文件 | 需要实现向量计算功能 |
| `app/rag/vector_store.py` | 空文件 | 需要实现FAISS向量存储功能 |
| `app/api/v1/admin/job_manage.py` | 已有create_job接口 | 需要添加向量库写入逻辑 |
| `app/bge-small-zh-v1.5-embedding/` | 模型文件存在 | 用于计算向量 |

## 实现步骤

### 1. 创建 embeddings.py

实现使用sentence-transformers加载bge-small-zh-v1.5模型，提供向量化方法：
- 加载本地模型（路径：`app/bge-small-zh-v1.5-embedding/`）
- 实现 `embed_documents` 方法用于批量向量化
- 实现 `embed_query` 方法用于单条查询向量化
- **向量维度：512维**
- **添加调试日志：模型加载状态、向量计算耗时、输出维度检查**

### 2. 创建 vector_store.py

实现FAISS向量存储功能：
- 定义向量库目录路径（`talentflow-ai-backend-bak/vector_store/`）
- 实现 `get_vectorstore()` 函数获取/初始化FAISS索引
  - **使用 IndexFlatIP（Inner Product）支持余弦相似度**
  - **向量维度设置为512**
- 实现 `add_texts_to_vectorstore()` 函数添加文本和metadata
- metadata存储到 `metadata.pkl`
- 向量索引存储到 `index.faiss`
- **添加调试日志：索引加载状态、向量数量、文件写入状态**

### 3. 修改 job_manage.py

在 `create_job` 函数中添加向量库写入逻辑：
- 导入向量存储相关模块
- 创建职位关键信息文本（title + description + skills等）
- 构造metadata（包含职位id等信息）
- 调用 `add_texts_to_vectorstore` 写入向量库
- **添加调试日志：向量库写入开始/完成状态、异常捕获与日志记录**

## 文件修改清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `app/rag/embeddings.py` | 新建 | 实现向量计算（含调试日志） |
| `app/rag/vector_store.py` | 新建 | 实现FAISS向量存储（IndexFlatIP，512维，含调试日志） |
| `app/api/v1/admin/job_manage.py` | 修改 | 添加向量库写入逻辑（含调试日志） |

## 依赖要求

需要确保以下Python包已安装：
- sentence-transformers (用于加载bge模型)
- faiss-cpu (用于向量存储)
- numpy (用于向量处理)
- pickle (用于metadata序列化)

## 向量存储格式

**metadata.pkl** 存储格式：
```python
[
    {"id": 1, "title": "软件工程师", "type": "job"},
    {"id": 2, "title": "产品经理", "type": "job"}
]
```

**index.faiss**：FAISS向量索引文件（使用IndexFlatIP，512维）

## 调试代码设计

### embeddings.py 调试点
1. 模型加载时打印加载状态和耗时
2. 向量计算前后打印输入文本数量和输出向量维度
3. 异常捕获并打印错误信息

### vector_store.py 调试点
1. 索引初始化/加载时打印状态信息
2. 添加向量时打印向量数量和维度
3. 文件读写操作前后打印状态
4. 异常捕获并打印错误信息

### job_manage.py 调试点
1. 创建职位后打印开始写入向量库
2. 向量库写入完成后打印成功信息
3. 捕获向量库写入异常，记录日志但不影响职位创建
4. 打印向量库目录路径确认

## 风险评估

1. **模型加载失败**：确保bge-small-zh-v1.5-embedding目录存在且完整
2. **FAISS索引文件损坏**：添加异常处理和日志记录
3. **向量维度不匹配**：确保embedding输出维度与FAISS索引维度一致（512维）

## 测试验证

1. 创建职位时检查vector_store目录是否生成index.faiss和metadata.pkl文件
2. 查看控制台输出确认调试日志正常打印
3. 验证metadata包含正确的职位信息
4. 确保后续创建的职位能正确追加到向量库