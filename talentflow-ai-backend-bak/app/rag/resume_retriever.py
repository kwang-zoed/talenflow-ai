import json
import os
from typing import Dict, List, Set, Tuple

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.rag.embeddings import embed_query
from app.rag.retriever import normalize_scores, search_bm25
from app.rag.vector_store import RESUME_INDEX_FILE


def parse_resume_skills(resume: Resume) -> Set[str]:
    skills_set: Set[str] = set()
    if not resume.skills:
        return skills_set
    if isinstance(resume.skills, list):
        for s in resume.skills:
            if s:
                skills_set.add(str(s).strip().lower())
        return skills_set
    try:
        skills_list = json.loads(resume.skills)
        if isinstance(skills_list, list):
            for s in skills_list:
                if s:
                    skills_set.add(str(s).strip().lower())
    except (json.JSONDecodeError, TypeError):
        pass
    return skills_set


def resume_to_text(resume: Resume) -> str:
    skills_text = ""
    if resume.skills:
        if isinstance(resume.skills, list):
            skills_text = " ".join(str(s) for s in resume.skills if s)
        else:
            skills_text = str(resume.skills)
    parts = [
        resume.title or "",
        resume.name or "",
        resume.summary or "",
        resume.education or "",
        resume.work_experience or "",
        resume.project_experience or "",
        skills_text,
    ]
    return " ".join(p for p in parts if p).strip()


def load_all_resumes(db: Session) -> List[Resume]:
    stmt = select(Resume).where(Resume.status != "Archived")
    return list(db.execute(stmt).scalars().all())


def build_bm25_corpus(resumes: List[Resume]) -> Tuple[BM25Okapi, List[str], List[int]]:
    corpus = []
    resume_ids_list = []
    for resume in resumes:
        text = resume_to_text(resume).lower()
        corpus.append(text)
        resume_ids_list.append(resume.id)
    tokenized_corpus = [doc.split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else BM25Okapi([[]])
    return bm25, corpus, resume_ids_list


def search_faiss_resumes(query_text: str, top_k: int = 50) -> List[Tuple[int, float]]:
    if not os.path.exists(RESUME_INDEX_FILE):
        return []
    index = faiss.read_index(RESUME_INDEX_FILE)
    if index.ntotal == 0:
        return []
    query_vec = embed_query(query_text)
    query_np = np.array([query_vec]).astype("float32")
    k = min(top_k, index.ntotal)
    D, I = index.search(query_np, k)
    results = []
    for idx in range(len(I[0])):
        faiss_id = int(I[0][idx])
        score = float(D[0][idx])
        if faiss_id != -1:
            results.append((faiss_id, score))
    return results


def get_hybrid_resume_retriever(db: Session):
    resumes = load_all_resumes(db)
    bm25, _corpus, resume_ids_list = build_bm25_corpus(resumes)
    resumes_map = {r.id: r for r in resumes}

    def search(query_text: str, top_k: int = 50) -> List[Dict]:
        faiss_results = search_faiss_resumes(query_text, top_k)
        bm25_results = search_bm25(bm25, query_text, resume_ids_list, top_k)

        faiss_norm = normalize_scores(faiss_results)
        bm25_norm = normalize_scores(bm25_results)
        all_resume_ids = set(faiss_norm.keys()) | set(bm25_norm.keys())

        merged = []
        for resume_id in all_resume_ids:
            resume = resumes_map.get(resume_id)
            if not resume:
                continue
            f_score = faiss_norm.get(resume_id, 0)
            b_score = bm25_norm.get(resume_id, 0)
            rag_score = b_score * 0.3 + f_score * 0.7
            merged.append(
                {
                    "resume_id": resume_id,
                    "resume_obj": resume,
                    "bm25_score": b_score,
                    "faiss_score": f_score,
                    "rag_score": rag_score,
                    "passage": resume_to_text(resume),
                    "skills": list(parse_resume_skills(resume)),
                }
            )
        merged.sort(key=lambda x: x["rag_score"], reverse=True)
        return merged[:top_k]

    return search
