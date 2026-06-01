"""
验证 LangSmith 能否上报 trace。在 backend 目录执行:

  conda activate smart-customer-rag
  cd talentflow-ai-backend-bak
  python scripts/verify_langsmith.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.config import settings
from app.core.langsmith_tracing import setup_langsmith_tracing


def main() -> int:
    print("LANGSMITH_TRACING (env):", os.getenv("LANGSMITH_TRACING"))
    print("settings.LANGSMITH_TRACING_ENABLED:", settings.LANGSMITH_TRACING_ENABLED)
    print("API key configured:", bool((settings.LANGSMITH_API_KEY or "").strip()))
    print("project:", settings.LANGSMITH_PROJECT)

    if not setup_langsmith_tracing():
        print("\n[FAIL] LangSmith 未启用，请检查 .env")
        return 1

    try:
        from langsmith import Client

        client = Client()
        client.create_run(
            name="talentflow_verify_ping",
            run_type="chain",
            inputs={"ping": "talentflow"},
            outputs={"ok": True},
            project_name=settings.LANGSMITH_PROJECT,
        )
        print(f"\n[OK] 已向项目「{settings.LANGSMITH_PROJECT}」发送测试 trace。")
        print("请在 LangSmith → Traces 刷新页面（约 5–30 秒）。")
        return 0
    except Exception as e:
        print(f"\n[FAIL] 上报失败: {e}")
        print("常见原因：API Key 无效、网络无法访问 api.smith.langchain.com")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
