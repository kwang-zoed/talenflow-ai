#!/usr/bin/env python3
"""
下载 BGE embedding / reranker 到 app/ 下（不提交 Git，构建镜像或本地开发时执行）。

- 本地 / 国内 Docker build: HF_ENDPOINT=https://hf-mirror.com
- GitHub Actions: 自动优先 https://huggingface.co
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

MODELS = {
    "BAAI/bge-small-zh-v1.5": "bge-small-zh-v1.5-embedding",
    "BAAI/bge-reranker-v2-m3": "bge-reranker-v2-m3",
}

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_ROOT / "app"

# 只拉推理必需文件，避免把整个 repo 杂项都下下来
ALLOW_PATTERNS = [
    "*.json",
    "*.safetensors",
    "*.bin",
    "*.model",
    "*.txt",
    "tokenizer*",
    "1_Pooling/**",
    "README.md",
]


def _has_weights(target: Path) -> bool:
    if not target.is_dir():
        return False
    for name in ("model.safetensors", "pytorch_model.bin"):
        if (target / name).exists():
            return True
    return False


def _normalize_endpoint(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _endpoint_candidates() -> list[str]:
    explicit = _normalize_endpoint(os.getenv("HF_ENDPOINT") or "")
    if explicit:
        return [explicit]

    if os.getenv("GITHUB_ACTIONS") == "true":
        return ["https://huggingface.co", "https://hf-mirror.com"]

    return ["https://hf-mirror.com", "https://huggingface.co"]


def _download_one(repo_id: str, target: Path, force: bool) -> None:
    from huggingface_hub import snapshot_download

    if _has_weights(target) and not force:
        print(f"[skip] {target.name} 已有权重", flush=True)
        return

    target.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None

    for endpoint in _endpoint_candidates():
        os.environ["HF_ENDPOINT"] = endpoint
        print(f"[download] {repo_id} -> {target} via {endpoint}", flush=True)

        for attempt in range(1, 4):
            try:
                snapshot_download(
                    repo_id=repo_id,
                    local_dir=str(target),
                    allow_patterns=ALLOW_PATTERNS,
                    endpoint=endpoint,
                )
                if not _has_weights(target):
                    raise RuntimeError(f"下载结束但未发现权重文件: {target}")
                print(f"[ok] {target.name}", flush=True)
                return
            except Exception as exc:
                last_err = exc
                wait = 5 * attempt
                print(
                    f"[retry] {target.name} attempt {attempt}/3 @ {endpoint}: {exc}",
                    flush=True,
                )
                time.sleep(wait)

    raise RuntimeError(f"下载失败 {repo_id}: {last_err}") from last_err


def download_all(force: bool = False) -> None:
    try:
        import huggingface_hub  # noqa: F401
    except ImportError as exc:
        raise SystemExit("缺少 huggingface_hub，请 pip install huggingface_hub") from exc

    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "600")
    print(f"HF_HUB_DOWNLOAD_TIMEOUT={os.getenv('HF_HUB_DOWNLOAD_TIMEOUT')}", flush=True)
    print(f"endpoints={_endpoint_candidates()}", flush=True)

    for repo_id, folder in MODELS.items():
        _download_one(repo_id, APP_DIR / folder, force)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download BGE models for TalentFlow")
    parser.add_argument("--force", action="store_true", help="已有权重也重新下载")
    args = parser.parse_args()
    try:
        download_all(force=args.force)
    except Exception as exc:
        print(f"[fatal] {exc}", flush=True)
        sys.exit(1)
    print("模型下载完成。", flush=True)


if __name__ == "__main__":
    main()
