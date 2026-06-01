#!/usr/bin/env python3
"""
下载 BGE embedding / reranker 到 app/ 下（不提交 Git，构建镜像或本地开发时执行）。

国内可设: HF_ENDPOINT=https://hf-mirror.com
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

# HuggingFace 仓库 id -> 本地目录名（与 embeddings.py / reranker.py 一致）
MODELS = {
    "BAAI/bge-small-zh-v1.5": "bge-small-zh-v1.5-embedding",
    "BAAI/bge-reranker-v2-m3": "bge-reranker-v2-m3",
}

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_ROOT / "app"


def _has_weights(target: Path) -> bool:
    if not target.is_dir():
        return False
    for name in ("model.safetensors", "pytorch_model.bin"):
        if (target / name).exists():
            return True
    return False


def download_all(force: bool = False) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit(
            "请先安装: pip install huggingface_hub\n"
            "或已在 requirements.txt / Docker 构建中安装"
        ) from exc

    endpoint = os.getenv("HF_ENDPOINT", "")
    if endpoint:
        print(f"HF_ENDPOINT={endpoint}")

    for repo_id, folder in MODELS.items():
        target = APP_DIR / folder
        target.mkdir(parents=True, exist_ok=True)

        if _has_weights(target) and not force:
            print(f"[skip] {folder} 已有权重")
            continue

        print(f"[download] {repo_id} -> {target}")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target),
            local_dir_use_symlinks=False,
        )
        print(f"[ok] {folder}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download BGE models for TalentFlow")
    parser.add_argument("--force", action="store_true", help="已有权重也重新下载")
    args = parser.parse_args()
    download_all(force=args.force)
    print("模型下载完成。")


if __name__ == "__main__":
    main()
