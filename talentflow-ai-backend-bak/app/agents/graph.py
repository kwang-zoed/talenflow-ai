import logging
from pathlib import Path
from typing import Optional

from langgraph.graph import END, START, StateGraph

from app.agents.edges import route_after_fetch
from app.agents.nodes import (
    fetch_resume_node,
    generate_letter_node,
    optimize_resume_node,
    review_cover_letter_node,
    review_optimized_resume_node,
    save_optimized_resume_node,
    save_record_node,
)
from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

_REDIS_SEARCH_HINT = (
    "当前 Redis 未启用 RediSearch/RedisJSON（普通 redis-server 不支持 FT._LIST）。"
    "已自动改用 SQLite 检查点；若需 Redis 持久化请安装 Redis Stack / Redis 8+。"
)

smart_apply_graph = None
_checkpointer: Optional[object] = None
_graph_initialized = False


def _is_redis_module_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "ft._list" in msg or "unknown command" in msg or "redisjson" in msg or "redisearch" in msg


async def _create_async_redis_checkpointer():
    """需 Redis Stack / Redis 8+（含 RediSearch、RedisJSON）。"""
    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
    except ImportError as e:
        logger.warning(
            "未安装 langgraph-checkpoint-redis: %s。pip install langgraph-checkpoint-redis",
            e,
        )
        return None

    try:
        checkpointer = AsyncRedisSaver(redis_url=settings.REDIS_URL)
        await checkpointer.setup()
        logger.info("LangGraph 检查点: Redis Stack (%s)", settings.REDIS_URL.split("@")[-1])
        return checkpointer
    except Exception as e:
        if _is_redis_module_error(e):
            logger.warning("%s 详情: %s", _REDIS_SEARCH_HINT, e)
        else:
            logger.warning("Redis 检查点连接失败: %s", e)
        return None


async def _create_async_sqlite_checkpointer():
    """与 ainvoke 兼容的 SQLite 检查点（需 aiosqlite）。"""
    try:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError as e:
        logger.warning(
            "未安装 langgraph-checkpoint-sqlite / aiosqlite: %s。"
            "pip install langgraph-checkpoint-sqlite aiosqlite",
            e,
        )
        return None

    try:
        db_path = Path(settings.SQLITE_CHECKPOINT_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(db_path))
        checkpointer = AsyncSqliteSaver(conn)
        logger.info("LangGraph 检查点: AsyncSQLite (%s)", db_path.resolve())
        return checkpointer
    except Exception as e:
        logger.warning("AsyncSQLite 检查点初始化失败: %s", e)
        return None


def _create_memory_checkpointer():
    from langgraph.checkpoint.memory import InMemorySaver

    logger.info("LangGraph 检查点: 内存（进程重启后会话状态不保留）")
    return InMemorySaver()


async def create_checkpointer():
    backend = (settings.CHECKPOINTER_BACKEND or "auto").strip().lower()

    if backend == "memory":
        return _create_memory_checkpointer()

    if backend == "sqlite":
        return await _create_async_sqlite_checkpointer() or _create_memory_checkpointer()

    if backend == "redis":
        cp = await _create_async_redis_checkpointer()
        if cp is None:
            logger.warning("CHECKPOINTER_BACKEND=redis 失败，回退 AsyncSQLite")
            return await _create_async_sqlite_checkpointer() or _create_memory_checkpointer()
        return cp

    # 开发环境多为普通 Redis，先 SQLite 避免 FT._LIST 阻塞启动
    cp = await _create_async_sqlite_checkpointer()
    if cp is not None:
        return cp

    cp = await _create_async_redis_checkpointer()
    if cp is not None:
        return cp

    return _create_memory_checkpointer()


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("fetch_resume", fetch_resume_node)
    builder.add_node("optimize_resume", optimize_resume_node)
    builder.add_node("review_optimized_resume", review_optimized_resume_node)
    builder.add_node("save_optimized_resume", save_optimized_resume_node)
    builder.add_node("generate_letter", generate_letter_node)
    builder.add_node("review_cover_letter", review_cover_letter_node)
    builder.add_node("save_record", save_record_node)

    builder.add_edge(START, "fetch_resume")
    builder.add_conditional_edges(
        "fetch_resume",
        route_after_fetch,
        {
            "optimize_resume": "optimize_resume",
            "save_record": "save_record",
        },
    )
    builder.add_edge("optimize_resume", "review_optimized_resume")
    builder.add_edge("review_optimized_resume", "save_optimized_resume")
    builder.add_edge("save_optimized_resume", "generate_letter")
    builder.add_edge("generate_letter", "review_cover_letter")
    builder.add_edge("review_cover_letter", "save_record")
    builder.add_edge("save_record", END)

    return builder.compile(checkpointer=checkpointer, name="talentflow_smart_apply")


async def init_smart_apply_graph() -> None:
    """在 FastAPI 启动时调用（需已有运行中的事件循环）。"""
    global smart_apply_graph, _checkpointer, _graph_initialized

    _checkpointer = await create_checkpointer()
    smart_apply_graph = build_graph(checkpointer=_checkpointer)
    _graph_initialized = True


async def get_smart_apply_graph():
    """获取已编译图；若尚未初始化则在此事件循环中初始化。"""
    global smart_apply_graph, _graph_initialized

    if smart_apply_graph is None or not _graph_initialized:
        await init_smart_apply_graph()
    return smart_apply_graph


async def shutdown_smart_apply_graph() -> None:
    """释放检查点连接，避免进程退出时卡住（尤其 Windows + Ctrl+C）。"""
    global smart_apply_graph, _checkpointer, _graph_initialized

    if _checkpointer is None:
        return

    try:
        conn = getattr(_checkpointer, "conn", None)
        if conn is not None:
            close_fn = getattr(conn, "close", None)
            if callable(close_fn):
                result = close_fn()
                if hasattr(result, "__await__"):
                    await result

        redis_client = getattr(_checkpointer, "_redis", None)
        if redis_client is not None:
            for method_name in ("aclose", "close"):
                method = getattr(redis_client, method_name, None)
                if callable(method):
                    result = method()
                    if hasattr(result, "__await__"):
                        await result
                    break
    except Exception as e:
        logger.warning("关闭 LangGraph 检查点连接失败: %s", e)
    finally:
        smart_apply_graph = None
        _checkpointer = None
        _graph_initialized = False
        logger.info("LangGraph 检查点已释放")
