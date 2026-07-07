"""
LangSmith 评测配置与分阶段执行说明
==================================

统一入口：python scripts/eval/cli.py <子命令>

  setup          阶段 0：LangSmith 连通性
  import-jobs    阶段 1：导入 eval 职位种子
  seed           阶段 1：上传 golden set（--pipeline rag|smart_apply）
  smoke          阶段 1：单链路冒烟（--pipeline rag|smart_apply）
  run            阶段 2–4：批量评估（--pipeline rag|smart_apply）
  trace          阶段 5：Trace → Dataset
  analyze/compare 阶段 5：BadCase 与实验对比

完整说明见：scripts/eval/docs/langsmith-eval-guide.md  
生产方案见：scripts/eval/docs/langsmith-eval-production-plan.md

必需环境变量（阶段 0 起）：
  LANGSMITH_API_KEY
  LANGSMITH_EVAL_PROJECT（默认 talentflow-eval）

阶段 2 起额外需要 MySQL + FAISS 职位数据。
阶段 3/4 起需要 EVAL_JUDGE_* 或 API_KEY（DeepSeek）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_EVAL_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _EVAL_DIR.parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent

if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env", override=True)

DATASETS_DIR = _EVAL_DIR / "datasets"
EVALUATORS_DIR = _EVAL_DIR / "evaluators"
SCHEMAS_DIR = _EVAL_DIR / "schemas"

# LangSmith 评测专用 project（与 trace project 分离）
LANGSMITH_EVAL_PROJECT: str = os.getenv("LANGSMITH_EVAL_PROJECT", "talentflow-eval")
LANGSMITH_API_KEY: str = os.getenv(
    "LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY", "")
)
LANGSMITH_ENDPOINT: str = os.getenv(
    "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
)

# LLM Judge（阶段 3/4 启用）
EVAL_JUDGE_PROVIDER: str = os.getenv("EVAL_JUDGE_PROVIDER", "deepseek").lower()
EVAL_JUDGE_MODEL: str = os.getenv("EVAL_JUDGE_MODEL", "")
EVAL_JUDGE_API_KEY: str = os.getenv(
    "EVAL_JUDGE_API_KEY",
    os.getenv("OPENAI_API_KEY", os.getenv("API_KEY", "")),
)
EVAL_JUDGE_TEMPERATURE: float = float(os.getenv("EVAL_JUDGE_TEMPERATURE", "0"))
EVAL_JUDGE_TOP_N: int = int(os.getenv("EVAL_JUDGE_TOP_N", "3"))
EVAL_RELEVANCE_PASS_THRESHOLD: int = int(os.getenv("EVAL_RELEVANCE_PASS_THRESHOLD", "4"))

# 检索指标（阶段 2 启用）
EVAL_RECALL_K: int = int(os.getenv("EVAL_RECALL_K", "5"))
EVAL_PRECISION_K: int = int(os.getenv("EVAL_PRECISION_K", "5"))
EVAL_SEMANTIC_THRESHOLD: float = float(os.getenv("EVAL_SEMANTIC_THRESHOLD", "0.65"))

# 数据集名称
RAG_DATASET_NAME = "talentflow_golden_set_v1"
RAG_DATASET_V2_NAME = "talentflow_golden_set_v2"
SMART_APPLY_DATASET_NAME = "smart_apply_golden_set_v1"
SETUP_TEST_DATASET_NAME = "talentflow_eval_setup_test"

_JUDGE_DEFAULTS = {
    "deepseek": ("deepseek-chat", "https://api.deepseek.com/v1"),
    "openai": ("gpt-4o", None),
}


def get_judge_model() -> str:
    if EVAL_JUDGE_MODEL.strip():
        return EVAL_JUDGE_MODEL.strip()
    return _JUDGE_DEFAULTS.get(EVAL_JUDGE_PROVIDER, _JUDGE_DEFAULTS["deepseek"])[0]


def get_judge_base_url() -> str | None:
    explicit = os.getenv("EVAL_JUDGE_BASE_URL", "").strip()
    if explicit:
        return explicit
    return _JUDGE_DEFAULTS.get(EVAL_JUDGE_PROVIDER, _JUDGE_DEFAULTS["deepseek"])[1]


def langsmith_client_kwargs() -> dict:
    kwargs: dict = {"api_key": LANGSMITH_API_KEY.strip()}
    if LANGSMITH_ENDPOINT.strip():
        kwargs["api_url"] = LANGSMITH_ENDPOINT.strip()
    return kwargs
