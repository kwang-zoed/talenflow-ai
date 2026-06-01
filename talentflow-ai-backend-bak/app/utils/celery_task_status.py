"""Celery 任务状态轮询响应（文档解析 / 简历解析等共用）"""
from celery.result import AsyncResult

from app.core.celery_app import celery_app


def build_celery_task_status(task_id: str) -> dict:
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {
            "status": "processing",
            "message": "任务排队中...",
            "percent": 0,
        }
    if result.state == "PROGRESS":
        meta = result.info
        if isinstance(meta, dict):
            return {
                "status": "processing",
                "message": meta.get("message", "正在处理..."),
                "percent": meta.get("percent", 0),
                "current": meta.get("current", 0),
                "total": meta.get("total", 1),
            }
        return {
            "status": "processing",
            "message": "正在处理...",
            "percent": 0,
        }
    if result.state == "SUCCESS":
        task_output = result.result
        if isinstance(task_output, dict) and task_output.get("status") == "success":
            return {
                "status": "success",
                "message": "处理完成",
                "percent": 100,
                "data": task_output.get("result"),
            }
        if isinstance(task_output, dict) and task_output.get("status") == "error":
            return {
                "status": "error",
                "message": task_output.get("message", "处理失败"),
            }
        return {
            "status": "success",
            "message": "处理完成",
            "percent": 100,
            "data": task_output,
        }
    if result.state == "FAILURE":
        return {
            "status": "error",
            "message": f"处理失败: {str(result.info)[:120]}",
        }

    return {
        "status": "processing",
        "message": f"状态: {result.state}",
        "percent": 0,
    }
