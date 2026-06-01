import os
import time
import numpy as np
from typing import List
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

RERANKER_PATH = os.path.join(os.path.dirname(__file__), '..', 'bge-reranker-v2-m3')

_reranker_instance = None


class BgeReranker:
    def __init__(self, model_path: str = None):
        model_path = model_path or RERANKER_PATH
        abs_path = os.path.abspath(model_path)
        
        print(f"\n{'='*60}")
        print(f"[RERANKER DEBUG] 开始加载 BGE Reranker 模型...")
        start_time = time.time()
        
        self.tokenizer = AutoTokenizer.from_pretrained(abs_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(abs_path)
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


def get_reranker() -> BgeReranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BgeReranker()
    return _reranker_instance
