import os
import faiss
import pickle
import numpy as np
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from sqlmodel import Session, select

from app.models.job_position import JobPosition
from app.rag.embeddings import embed_query
from app.rag.vector_store import INDEX_FILE, METADATA_FILE, VECTOR_STORE_DIR


def load_all_jobs(db: Session) -> List[JobPosition]:
    jobs = db.execute(select(JobPosition)).scalars().all()
    return list(jobs)


def build_bm25_corpus(jobs: List[JobPosition]) -> Tuple[BM25Okapi, List[str], Dict[int, int]]:
    corpus = []
    job_id_to_idx = {}
    job_ids_list = []
    
    for idx, job in enumerate(jobs):
        skills_text = ' '.join(job.required_skills) if job.required_skills else ''
        text = f"{job.title or ''} {job.company or ''} {job.description or ''} {skills_text} {job.location or ''} {job.education_requirement or ''}"
        
        corpus.append(text.lower())
        job_id_to_idx[job.id] = idx
        job_ids_list.append(job.id)
    
    tokenized_corpus = [doc.split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    
    return bm25, corpus, job_ids_list


def search_faiss(query_text: str, top_k: int = 50) -> List[Tuple[int, float]]:
    if not os.path.exists(INDEX_FILE):
        return []
    
    index = faiss.read_index(INDEX_FILE)
    
    query_vec = embed_query(query_text)
    query_np = np.array([query_vec]).astype('float32')
    
    D, I = index.search(query_np, top_k)
    
    results = []
    for idx in range(len(I[0])):
        faiss_id = int(I[0][idx])
        score = float(D[0][idx])
        if faiss_id != -1:
            results.append((faiss_id, score))
    
    return results


def search_bm25(bm25: BM25Okapi, query_text: str, job_ids_list: List[int], top_k: int = 50) -> List[Tuple[int, float]]:
    tokenized_query = query_text.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    top_indices = np.argsort(scores)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            job_id = job_ids_list[idx]
            results.append((job_id, float(scores[idx])))
    
    return results


def normalize_scores(items: List[Tuple[int, float]]) -> Dict[int, float]:
    if not items:
        return {}
    
    scores = [s for _, s in items]
    min_s, max_s = min(scores), max(scores)
    
    normalized = {}
    for job_id, score in items:
        if max_s - min_s > 1e-8:
            normalized[job_id] = (score - min_s) / (max_s - min_s)
        else:
            normalized[job_id] = 1.0
    
    return normalized


def get_hybrid_retriever(db: Session):
    jobs = load_all_jobs(db)
    bm25, corpus, job_ids_list = build_bm25_corpus(jobs)
    
    jobs_map = {j.id: j for j in jobs}
    
    def search(query_text: str, top_k: int = 50) -> List[Dict]:
        faiss_results = search_faiss(query_text, top_k)
        bm25_results = search_bm25(bm25, query_text, job_ids_list, top_k)
        
        faiss_norm = normalize_scores(faiss_results)
        bm25_norm = normalize_scores(bm25_results)
        
        all_job_ids = set(list(faiss_norm.keys()) + list(bm25_norm.keys()))
        
        merged = []
        for job_id in all_job_ids:
            job = jobs_map.get(job_id)
            if job:
                f_score = faiss_norm.get(job_id, 0)
                b_score = bm25_norm.get(job_id, 0)
                rag_score = b_score * 0.3 + f_score * 0.7
                
                skills_text = ' '.join(job.required_skills) if job.required_skills else ''
                passage = f"{job.title or ''} {job.company or ''} {job.description or ''} {skills_text}"
                
                merged.append({
                    'job_id': job_id,
                    'job_obj': job,
                    'bm25_score': b_score,
                    'faiss_score': f_score,
                    'rag_score': rag_score,
                    'passage': passage,
                    'required_skills': job.required_skills or []
                })
        
        merged.sort(key=lambda x: x['rag_score'], reverse=True)
        
        return merged[:top_k]
    
    return search
