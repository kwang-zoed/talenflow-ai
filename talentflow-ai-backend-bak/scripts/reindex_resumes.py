#!/usr/bin/env python
"""全量重建简历 FAISS 索引（运维脚本，长期保留）"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.rag.resume_retriever import load_all_resumes, resume_to_text
from app.rag.vector_store import (
    RESUME_INDEX_FILE,
    RESUME_METADATA_FILE,
    ensure_dir,
    get_resume_index_count,
    _add_texts_to_resume_vectorstore,
)
import faiss
import pickle
import os
from app.rag.embeddings import get_vector_dimension


def reindex_all():
    ensure_dir()
    dimension = get_vector_dimension()
    base_index = faiss.IndexFlatIP(dimension)
    index = faiss.IndexIDMap2(base_index)
    if os.path.exists(RESUME_INDEX_FILE):
        os.remove(RESUME_INDEX_FILE)
    if os.path.exists(RESUME_METADATA_FILE):
        os.remove(RESUME_METADATA_FILE)

    global _resume_vectorstore
    from app.rag import vector_store as vs
    vs._resume_vectorstore = None

    db = SessionLocal()
    try:
        resumes = load_all_resumes(db)
        if not resumes:
            print("[reindex_resumes] 无 Active 简历，跳过")
            faiss.write_index(index, RESUME_INDEX_FILE)
            with open(RESUME_METADATA_FILE, 'wb') as f:
                pickle.dump([], f)
            return 0
        texts = [resume_to_text(r) for r in resumes]
        metadatas = [{
            "id": r.id,
            "name": r.name,
            "title": r.title,
            "type": "resume",
        } for r in resumes]
        _add_texts_to_resume_vectorstore(texts, metadatas)
        count = get_resume_index_count()
        print(f"[reindex_resumes] 完成，索引向量数: {count}")
        return count
    finally:
        db.close()


if __name__ == "__main__":
    reindex_all()
