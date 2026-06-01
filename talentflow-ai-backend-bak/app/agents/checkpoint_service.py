"""LangGraph Checkpointer 查询与续跑（FastAPI 进程内使用）。"""



import logging

from pathlib import Path

from typing import Any, Dict, Optional, Tuple



from langgraph.types import Command



from app.agents.graph import build_graph, get_smart_apply_graph

from app.core.config import settings
from app.core.langsmith_tracing import build_langgraph_run_config



logger = logging.getLogger(__name__)



NODE_TO_STAGE = {

    "fetch_resume": "fetch_resume",

    "optimize_resume": "optimize",

    "review_optimized_resume": "optimize",

    "save_optimized_resume": "save_resume",

    "generate_letter": "generate_letter",

    "review_cover_letter": "generate_letter",

    "save_record": "save_record",

}



STAGE_PERCENT = {

    "pending": 0,

    "fetch_resume": 20,

    "optimize": 40,

    "save_resume": 60,

    "generate_letter": 80,

    "save_record": 95,

    "done": 100,

}



REVIEW_MESSAGES = {

    "optimized_resume": "请确认 AI 优化后的简历",

    "cover_letter": "请确认求职信",

}





def make_thread_id(user_id: int, job_id: str, run_id: str) -> str:

    """thread_id 规范：apply_{user_id}_{job_id}_{run_id}，run_id 通常为 Celery task id。"""

    return f"apply_{user_id}_{job_id}_{run_id}"





def stage_from_node(node_name: str) -> str:

    return NODE_TO_STAGE.get(node_name, node_name)





def extract_interrupt_info(snapshot) -> Dict[str, Any]:

    """从 LangGraph StateSnapshot 解析 interrupt 载荷。"""

    if snapshot is None or not getattr(snapshot, "interrupts", None):

        return {}

    first = snapshot.interrupts[0]

    payload = getattr(first, "value", first)

    if isinstance(payload, dict):

        return payload

    return {"message": str(payload)}





def infer_stage_from_snapshot(next_nodes: Tuple[str, ...], values: Dict[str, Any]) -> str:

    if values.get("application_id"):

        return "done"

    if next_nodes:

        return stage_from_node(next_nodes[0])

    return _last_completed_stage(values)





def _last_completed_stage(values: Dict[str, Any]) -> str:

    if values.get("cover_letter"):

        return "save_record"

    if values.get("resume_saved_in_run") or (

        values.get("optimized_resume") and values.get("resume_id")

    ):

        return "generate_letter"

    if values.get("optimized_resume"):

        return "save_resume"

    if values.get("resume_content"):

        return "optimize"

    return "fetch_resume"





def sanitize_state_for_api(values: Optional[Dict[str, Any]], include_details: bool = False) -> Dict[str, Any]:

    """返回可对外暴露的黑板字段，默认不含大段文本。"""

    if not values:

        return {}



    safe = {

        "user_id": values.get("user_id"),

        "job_id": values.get("job_id"),

        "resume_id": values.get("resume_id"),

        "application_id": values.get("application_id"),

        "skip_generation": values.get("skip_generation"),

        "resume_saved_in_run": values.get("resume_saved_in_run"),

        "applicant_name": values.get("applicant_name"),

        "error_message": values.get("error_message"),

        "has_optimized_resume": bool(values.get("optimized_resume")),

        "has_cover_letter": bool(values.get("cover_letter")),

    }



    if include_details:

        safe["optimized_resume"] = values.get("optimized_resume")

        safe["cover_letter"] = values.get("cover_letter")

        if values.get("resume_content"):

            content = str(values["resume_content"])

            safe["resume_content_preview"] = content[:300] + ("..." if len(content) > 300 else "")



    return safe





def build_snapshot_response(

    thread_id: str,

    snapshot,

    include_details: bool = False,

) -> Dict[str, Any]:

    if snapshot is None or snapshot.values is None:

        return {

            "thread_id": thread_id,

            "found": False,

            "stage": "pending",

            "status": "pending",

            "percent": 0,

            "next_nodes": [],

            "interrupts": False,

            "review_type": None,

            "review_message": None,

            "state": {},

        }



    values = dict(snapshot.values)

    next_nodes = tuple(snapshot.next or ())

    stage = infer_stage_from_snapshot(next_nodes, values)

    interrupt_info = extract_interrupt_info(snapshot)

    review_type = interrupt_info.get("review_type")



    if values.get("application_id"):

        status = "success"

    elif values.get("error_message") and not next_nodes:

        status = "error"

    elif snapshot.interrupts:

        status = "interrupted"

    elif next_nodes:

        status = "running"

    else:

        status = "success" if values.get("application_id") else "running"



    return {

        "thread_id": thread_id,

        "found": True,

        "stage": stage,

        "status": status,

        "percent": STAGE_PERCENT.get(stage, 0),

        "next_nodes": list(next_nodes),

        "interrupts": bool(snapshot.interrupts),

        "review_type": review_type,

        "review_message": interrupt_info.get("message") or REVIEW_MESSAGES.get(review_type),

        "state": sanitize_state_for_api(values, include_details=include_details),

    }





async def get_thread_checkpoint_state(

    thread_id: str,

    include_details: bool = False,

) -> Dict[str, Any]:

    """通过 Checkpointer 读取指定 thread 的快照。"""

    graph = await get_smart_apply_graph()

    config = build_langgraph_run_config(thread_id, run_name="smart_apply_get_state")

    snapshot = await graph.aget_state(config)

    return build_snapshot_response(thread_id, snapshot, include_details=include_details)





async def resume_thread_workflow(

    thread_id: str,

    updates: Optional[Dict[str, Any]] = None,

) -> Dict[str, Any]:

    """

    从 Checkpointer 断点续跑。

    updates 非空时作为 Command(resume=updates) 传入（人工回填场景）。

    返回 graph 结果 + 续跑后的快照（可能再次 interrupted）。

    """

    graph = await get_smart_apply_graph()

    config = build_langgraph_run_config(thread_id, run_name="smart_apply_resume")
    snapshot = await graph.aget_state(config)

    if snapshot is None or not snapshot.values:

        raise ValueError("未找到该 thread 的检查点，无法续跑")

    values = dict(snapshot.values)
    config = build_langgraph_run_config(
        thread_id,
        user_id=int(values["user_id"]) if values.get("user_id") is not None else None,
        job_id=str(values["job_id"]) if values.get("job_id") else None,
        run_name="smart_apply_resume",
    )

    if updates:

        graph_result = await graph.ainvoke(Command(resume=updates), config)

    else:

        graph_result = await graph.ainvoke(None, config)



    after = await graph.aget_state(config)

    snapshot_data = build_snapshot_response(thread_id, after, include_details=True)



    result_dict: Dict[str, Any] = {}

    if isinstance(graph_result, dict):

        result_dict = dict(graph_result)



    return {

        "result": result_dict,

        **snapshot_data,

    }





async def create_ephemeral_checkpointer():

    """Celery 任务内：每次 asyncio.run 创建独立连接，写入共享 SQLite 文件。"""

    import aiosqlite

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver



    db_path = Path(settings.SQLITE_CHECKPOINT_PATH)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(str(db_path))

    return AsyncSqliteSaver(conn), conn

