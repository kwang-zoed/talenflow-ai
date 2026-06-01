import os
import time
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'bge-small-zh-v1.5-embedding')

_embedding_model = None
_vector_dimension = 512

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print(f"\n{'='*60}")
        print("[EMBEDDING DEBUG] 开始加载BGE模型...")
        start_time = time.time()
        try:
            _embedding_model = SentenceTransformer(MODEL_PATH)
            elapsed_time = time.time() - start_time
            print(f"[EMBEDDING DEBUG] BGE模型加载成功，耗时: {elapsed_time:.2f}s")
            print(f"[EMBEDDING DEBUG] 模型路径: {MODEL_PATH}")
            print(f"{'='*60}")
        except Exception as e:
            print(f"[EMBEDDING ERROR] 模型加载失败: {str(e)}")
            raise
    return _embedding_model

def embed_documents(texts: list) -> list:
    print(f"\n{'='*60}")
    print(f"[EMBEDDING DEBUG] 开始向量化 {len(texts)} 条文本...")
    start_time = time.time()
    
    if not texts:
        print("[EMBEDDING DEBUG] 输入文本为空")
        print(f"{'='*60}")
        return []
    
    try:
        model = get_embedding_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()
        
        elapsed_time = time.time() - start_time
        print(f"[EMBEDDING DEBUG] 向量化完成，耗时: {elapsed_time:.2f}s")
        print(f"[EMBEDDING DEBUG] 输出向量数量: {len(embeddings)}")
        print(f"[EMBEDDING DEBUG] 向量维度: {len(embeddings[0]) if embeddings else 0}")
        print(f"{'='*60}")
        
        return embeddings
    except Exception as e:
        print(f"[EMBEDDING ERROR] 向量化失败: {str(e)}")
        raise

def embed_query(text: str) -> list:
    print(f"\n{'='*60}")
    print(f"[EMBEDDING DEBUG] 开始向量化查询文本...")
    print(f"[EMBEDDING DEBUG] 输入文本: {text[:50]}...")
    start_time = time.time()
    
    try:
        model = get_embedding_model()
        embedding = model.encode(text, normalize_embeddings=True)
        
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        
        elapsed_time = time.time() - start_time
        print(f"[EMBEDDING DEBUG] 查询向量化完成，耗时: {elapsed_time:.2f}s")
        print(f"[EMBEDDING DEBUG] 向量维度: {len(embedding)}")
        print(f"{'='*60}")
        
        return embedding
    except Exception as e:
        print(f"[EMBEDDING ERROR]查询向量化失败: {str(e)}")
        raise

def get_vector_dimension() -> int:
    return _vector_dimension