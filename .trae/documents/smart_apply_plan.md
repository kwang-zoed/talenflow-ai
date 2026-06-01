# 智能投递功能实现计划

## 1. 概述

使用 `langgraph` 和 `fastmcp` 实现智能投递工作流，包括：
- 简历获取
- 简历优化（含人工审核/回填）
- 优化后简历保存
- 求职信生成（含人工审核/回填）
- 投递记录保存

## 2. 技术架构

### 核心组件
- **state.py**: 定义状态机（黑板协作），使用 `Annotated` + 覆盖机制
- **nodes.py**: 实现各工作流节点
- **graph.py**: 构建 LangGraph 工作流图
- **smart_apply.py**: 用户端 API 接口
- **mcp_server/server.py**: 提供工具服务

### 工作流节点

```
获取简历 -> 优化简历 -> [人工审核/回填] -> 保存优化简历 -> 生成求职信 -> [人工审核/回填] -> 保存投递记录
```

## 3. 文件修改清单

### 3.1 新增/修改核心文件

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `requirements.txt` | 修改 | 添加 langgraph, langchain, fastmcp, openai |
| `app/agents/state.py` | 定义智能投递状态机（AgentState + Annotated reducer） |
| `app/agents/nodes.py` | 实现各工作流节点（MCP + LLM） |
| `app/agents/graph.py` | 构建工作流图 |
| `app/api/v1/user/smart_apply.py` | 新建 | 智能投递 API |
| `app/schemas/smart_apply_schema.py` | 新建 | 智能投递相关 Schema |
| `mcp_server/server.py` | 修改 | 完善 MCP 工具 |
| `app/main.py` | 修改 | 注册新路由 |
| `app/models/application.py` | 可选修改 | 扩展投递记录字段 |

### 3.2 状态机设计 (state.py) - 使用 Annotated 覆盖机制

```python
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph

# 覆盖机制：后写入的值覆盖先前的值
def override(a, b):
    return b if b is not None else a

class SmartApplyState(TypedDict):
    # 基础信息（不可覆盖）
    user_id: int
    job_id: int
    
    # 简历相关（使用覆盖机制）
    resume_id: Annotated[Optional[int], override]
    original_resume: Annotated[Optional[Dict], override]
    job_info: Annotated[Optional[Dict], override]
    optimized_resume: Annotated[Optional[Dict], override]
    
    # 求职信相关（使用覆盖机制）
    cover_letter: Annotated[Optional[str], override]
    
    # 审核状态
    resume_approved: Annotated[Optional[bool], override]
    cover_letter_approved: Annotated[Optional[bool], override]
    
    # 审核反馈（人工回填，可覆盖）
    resume_feedback: Annotated[Optional[str], override]
    cover_letter_feedback: Annotated[Optional[str], override]
    
    # 输出结果
    optimized_resume_id: Annotated[Optional[int], override]
    application_id: Annotated[Optional[int], override]
    
    # 流程控制
    current_step: Annotated[Optional[str], override]
    error: Annotated[Optional[str], override]
```

### 3.3 节点设计 (nodes.py)

1. **get_resume_node**: 获取原始简历和职位信息
2. **optimize_resume_node**: AI 优化简历
3. **save_optimized_resume_node**: 保存优化后简历
4. **generate_cover_letter_node**: AI 生成求职信
5. **save_application_node**: 保存投递记录

### 3.4 工作流图设计 (graph.py)

使用 LangGraph 的条件边实现人工审核点：
- 优化简历后等待审核（暂停，等待用户输入）
- 生成求职信后等待审核（暂停，等待用户输入）

### 3.5 API 设计 (smart_apply.py)

```
POST /api/v1/user/smart-apply/start          # 开始智能投递
POST /api/v1/user/smart-apply/{id}/resume-review  # 简历审核
POST /api/v1/user/smart-apply/{id}/cover-letter-review  # 求职信审核
GET  /api/v1/user/smart-apply/{id}/status    # 查询状态
```

## 4. 实现步骤

### 步骤 1: 更新依赖
在 `requirements.txt` 中添加：
```
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
fastmcp>=0.5.0
openai>=1.50.0
```

### 步骤 2: 实现状态机 (state.py)
定义 `SmartApplyState` 类型字典，使用 `Annotated` + 覆盖机制

### 步骤 3: 实现节点 (nodes.py)
- 获取简历和职位信息
- AI 优化简历（调用 LLM）
- 保存优化简历
- AI 生成求职信（调用 LLM）
- 保存投递记录

### 步骤 4: 构建工作流图 (graph.py)
- 使用 LangGraph 构建图
- 添加条件边实现人工审核暂停点

### 步骤 5: 实现 API 接口 (smart_apply.py)
- 启动智能投递
- 审核接口
- 状态查询接口

### 步骤 6: 完善 MCP Server (mcp_server/server.py)
- 获取简历工具
- 保存简历工具
- 获取职位信息工具
- 保存投递记录工具

### 步骤 7: 注册路由 (main.py)
- 导入并注册 smart_apply 路由

### 步骤 8: （可选）更新数据模型
- 扩展 Application 模型，添加优化简历 ID 等字段
- 添加 Schema 定义

## 5. 注意事项

1. **状态持久化**: 需要使用内存或数据库存储工作流状态
2. **LLM 调用**: 确保配置了 OpenAI API Key
3. **错误处理**: 各节点添加异常处理
4. **权限验证**: 使用现有的 `get_current_user` 依赖
5. **日志记录**: 添加关键步骤的日志

## 6. 依赖项确认

- 项目已有 FastAPI, SQLAlchemy, MySQL
- 需要新增: langgraph, langchain, fastmcp, openai
