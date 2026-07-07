import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.core.config import settings

RERANKER_PATH = os.path.join(os.path.dirname(__file__), '..', 'bge-reranker-v2-m3')

logger = logging.getLogger(__name__)

_reranker_instance: Optional["BgeReranker"] = None
_reranker_unavailable = False


def reranker_load_allowed() -> bool:
    """Reranker 仅在 Celery Worker 中加载，API 进程一律跳过。"""
    explicit = os.getenv("RERANKER_ENABLED")
    if explicit is not None:
        return explicit.lower() in ("1", "true", "yes")

    role = (settings.APP_PROCESS_ROLE or os.getenv("APP_PROCESS_ROLE", "")).lower()
    if role == "worker":
        return True
    if role in ("api", "mcp"):
        return False

    argv = " ".join(sys.argv).lower()
    return "celery" in argv and "worker" in argv


class BgeReranker:
    def __init__(self, model_path: str = None):
        model_path = model_path or RERANKER_PATH
        abs_path = os.path.abspath(model_path)

        print(f"\n{'='*60}")
        print(f"[RERANKER DEBUG] 开始加载 BGE Reranker 模型...")
        start_time = time.time()

        self.tokenizer = AutoTokenizer.from_pretrained(abs_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            abs_path,
            low_cpu_mem_usage=True,
        )
        self.model.eval()

        elapsed = time.time() - start_time
        print(f"[RERANKER DEBUG] 模型加载成功，耗时: {elapsed:.2f}s")
        print(f"[RERANKER DEBUG] 模型路径: {abs_path}")
        print(f"{'='*60}\n")

    def compute_score(self, query: str, passages: List[str]) -> List[float]:
        if not passages:
            return []

        pairs = [[query, p] for p in passages]

        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            )

            logits = self.model(**inputs).logits
            scores = logits.view(-1).float().tolist()

        return scores

    def rerank(self, query: str, candidates: List[dict],
               passage_key: str = 'passage', id_key: str = 'job_id') -> List[dict]:
        if not candidates:
            return []

        passages = [c.get(passage_key, '') or '' for c in candidates]
        scores = self.compute_score(query, passages)

        ranked = []
        for idx, score in enumerate(scores):
            item = candidates[idx].copy()
            item['rerank_score'] = float(score)
            ranked.append(item)

        ranked.sort(key=lambda x: x['rerank_score'], reverse=True)
        return ranked


def get_reranker() -> Optional[BgeReranker]:
    """加载 reranker；非 Worker 进程、加载失败或超时均返回 None。"""
    global _reranker_instance, _reranker_unavailable

    if not reranker_load_allowed():
        return None
    if _reranker_unavailable:
        return None
    if _reranker_instance is not None:
        return _reranker_instance

    timeout = settings.RERANKER_LOAD_TIMEOUT
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(BgeReranker)
            _reranker_instance = future.result(timeout=timeout)
            return _reranker_instance
    except FuturesTimeoutError:
        _reranker_unavailable = True
        logger.warning("Reranker 加载超时(%ss)，将使用粗排结果", timeout)
        return None
    except Exception as e:
        _reranker_unavailable = True
        logger.warning("Reranker 加载失败，将使用粗排结果: %s", e)
        return None
