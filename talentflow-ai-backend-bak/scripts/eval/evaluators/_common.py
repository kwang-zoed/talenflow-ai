"""评估器公共工具：从 run / example 读取 inputs / outputs。"""

from __future__ import annotations


def get_inputs(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.get("inputs") or obj
    return getattr(obj, "inputs", None) or {}


def get_outputs(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.get("outputs") or obj
    return getattr(obj, "outputs", None) or {}
