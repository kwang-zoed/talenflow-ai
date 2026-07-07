"""路径注入、LangSmith Client、环境变量。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
BACKEND_ROOT = EVAL_DIR.parents[1]


def setup_paths() -> None:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    if str(EVAL_DIR) not in sys.path:
        sys.path.insert(0, str(EVAL_DIR))


def ensure_langsmith_env() -> None:
    setup_paths()
    import config

    if config.LANGSMITH_API_KEY.strip():
        os.environ.setdefault("LANGSMITH_API_KEY", config.LANGSMITH_API_KEY)
        os.environ.setdefault("LANGCHAIN_API_KEY", config.LANGSMITH_API_KEY)


def get_client():
    setup_paths()
    ensure_langsmith_env()
    import config
    from langsmith import Client

    return Client(**config.langsmith_client_kwargs())


def require_api_key() -> bool:
    setup_paths()
    import config

    return bool(config.LANGSMITH_API_KEY.strip())
