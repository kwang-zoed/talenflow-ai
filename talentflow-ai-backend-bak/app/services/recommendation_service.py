from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import time
import logging

from app.models import base
from app.models.resume import Resume
from app.rag.retriever import get_hybrid_retriever
from app.rag.reranker import get_reranker
from app.core.celery_app import celery_app
from app.core.database import SessionLocal


logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_resume(self, user_id: int) -> Optional[Resume]:
        stmt_default = select(Resume).where(
            Resume.user_id == user_id,
            Resume.is_default == True
        )
        resume = self.db.execute(stmt_default).scalar_one_or_none()
        
        if not resume:
            stmt_any = select(Resume).where(Resume.user_id == user_id)
            resume = self.db.execute(stmt_any).scalars().first()
        
        return resume

    def extract_user_resume_info(self, resume: Resume) -> Dict[str, Any]:
        text_parts = []
        
        if resume.title:
            text_parts.append(f"{resume.title}")
        if resume.name:
            text_parts.append(f"{resume.name}")
        if resume.summary:
            text_parts.append(f"{resume.summary}")
        if resume.education:
            text_parts.append(f"{resume.education}")
        if resume.work_experience:
            text_parts.append(f"{resume.work_experience}")
        if resume.project_experience:
            text_parts.append(f"{resume.project_experience}")
        
        search_text = " ".join(text_parts)
        
        skills_set = set()
        if resume.skills and isinstance(resume.skills, list):
            for s in resume.skills:
                if s:
                    skills_set.add(str(s).strip().lower())
        elif resume.skills:
            try:
                skills_list = json.loads(resume.skills)
                if isinstance(skills_list, list):
                    for s in skills_list:
                        if s:
                            skills_set.add(str(s).strip().lower())
            except:
                pass
        
        return {
            "search_text": search_text,
            "skills": skills_set
        }

    def recommend_jobs(self, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        print("=" * 60)
        print(f" [RECOMMEND SERVICE] 开始职位推荐: user_id={user_id}, top_k={top_k}")
        
        resume = self.get_user_resume(user_id)
        if not resume:
            print(f" [RECOMMEND SERVICE] 没有找到用户简历，返回空")
            print("=" * 60)
            return []
        
        print(f" [RECOMMEND SERVICE] 找到简历: name={resume.name}, title={resume.title}")
        
        resume_info = self.extract_user_resume_info(resume)
        search_text = resume_info["search_text"]
        user_skills = resume_info["skills"]
        
        print(f" [RECOMMEND SERVICE] 查询文本长度: {len(search_text)}")
        print(f" [RECOMMEND SERVICE] 用户技能集合: {user_skills}")
        
        coarse_count = top_k * 5
        print(f" [RECOMMEND SERVICE] 粗排召回候选数: {coarse_count}")
        
        search_func = get_hybrid_retriever(self.db)
        merged_candidates = search_func(search_text, coarse_count)
        
        print(f" [RECOMMEND SERVICE] BM25+FAISS实际召回数: {len(merged_candidates)}")
        
        candidate_list = []
        for item in merged_candidates:
            job_obj = item['job_obj']
            job_skills = set()
            
            if hasattr(job_obj, 'skills') and job_obj.skills:
                if isinstance(job_obj.skills, list):
                    job_skills = {str(s).strip().lower() for s in job_obj.skills if s}
                else:
                    try:
                        skills_list = json.loads(job_obj.skills)
                        if isinstance(skills_list, list):
                            job_skills = {str(s).strip().lower() for s in skills_list if s}
                    except:
                        pass
            
            if job_skills and user_skills:
                matched = len(user_skills & job_skills)
                skill_score = matched / len(job_skills)
            else:
                skill_score = 0
            
            rag_score = item.get('rag_score', 0)
            final_score = rag_score * 0.7 + skill_score * 0.3
            
            candidate_list.append({
                'job_id': item['job_id'],
                'job_obj': item['job_obj'],
                'bm25_score': item.get('bm25_score', 0),
                'faiss_score': item.get('faiss_score', 0),
                'rag_score': rag_score,
                'skill_score': skill_score,
                'final_score': final_score
            })
        
        candidate_list.sort(key=lambda x: x['final_score'], reverse=True)
        
        top_for_rerank = candidate_list[:coarse_count]
        
        print(f" [RECOMMEND SERVICE] 粗排完毕，Final前三名分数: ")
        for i, cand in enumerate(top_for_rerank[:3]):
            print(f"   {i+1}. rag={cand['rag_score']:.3f}, skill={cand['skill_score']:.3f}, final={cand['final_score']:.3f}")
        
        reranker = get_reranker()
        if reranker:
            passages = []
            for cand in top_for_rerank:
                job_obj = cand['job_obj']
                job_text = ""
                if hasattr(job_obj, 'title') and job_obj.title:
                    job_text += f"{job_obj.title} "
                if hasattr(job_obj, 'company') and job_obj.company:
                    job_text += f"{job_obj.company} "
                if hasattr(job_obj, 'description') and job_obj.description:
                    job_text += f"{job_obj.description} "
                if hasattr(job_obj, 'skills') and job_obj.skills:
                    job_text += f"{job_obj.skills} "
                passages.append(job_text[:1000])
            
            if passages:
                rerank_scores = reranker.compute_score(search_text[:1000], passages)
                for i, score in enumerate(rerank_scores):
                    if i < len(top_for_rerank):
                        top_for_rerank[i]['rerank_score'] = float(score)
                
                top_for_rerank.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
                print(f" [RECOMMEND SERVICE] Reranker精排完成 ")
                for i, cand in enumerate(top_for_rerank[:3]):
                    print(f"   {i+1}. rerank_score={cand.get('rerank_score', 0):.3f}")
        else:
            print(f" [RECOMMEND SERVICE] Reranker未加载，使用粗排结果 ")
        
        results = []
        for item in top_for_rerank[:top_k]:
            if not isinstance(item, dict):
                print(f"[RECOMMEND WARNING] 跳过非字典类型的项: {type(item)}")
                continue
            
            job = item.get('job_obj')
            if not job:
                print(f"[RECOMMEND WARNING] 项中没有job_obj，跳过: {item.keys()}")
                continue
            
            job_data = {}
            if hasattr(job, '__dict__'):
                job_data = {k: v for k, v in job.__dict__.items() if not k.startswith('_')}
            elif isinstance(job, dict):
                job_data = dict(job)
            elif hasattr(job, 'id'):
                job_data = {'id': job.id}
            
            final_score = float(item.get('final_score', item.get('rag_score', 0)) or 0)
            
            results.append({
                'job': job_data,
                'score': int(final_score * 100),
                'matched_skills': []
            })
        
        print(f" [RECOMMEND SERVICE] 返回推荐数: {len(results)} ")
        print("=" * 60)
        
        return results


# ========== 异步推荐任务 ==========
@celery_app.task(bind=True, name="app.recommendation_service.generate_recommendation_task")
def generate_recommendation_task(self, user_id: int, top_k: int = 5):
    """后台异步执行的职位推荐任务"""
    start_time = time.time()
    
    try:
        logger.info(f"[Celery Worker] 开始为用户 {user_id} 异步生成推荐...")
        
        # 为新任务创建独立的数据库会话
        db = SessionLocal()
        
        try:
            # 1. 使用推荐服务
            service = RecommendationService(db)
            results = service.recommend_jobs(user_id, top_k)
            
            elapsed_time = time.time() - start_time
            logger.info(f"[Celery Worker] 用户 {user_id} 推荐完成，耗时 {elapsed_time:.2f}s")
            
            return {
                "status": "success",
                "result": results,
                "user_id": user_id,
                "elapsed_time": elapsed_time
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"[Celery Worker] 推荐任务失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


# ========== ========== 文档解析异步长任务（新增） ========== ==========
@celery_app.task(bind=True, name="app.services.recommendation_service.parse_document_task")
def parse_document_task(self, file_content: bytes, filename: str, is_batch: bool = False):
    """Celery后台任务：文档解析，支持进度上报 update_state
    
    Args:
        file_content: 文件二进制内容（bytes可被Celery序列化）
        filename: 文件名
        is_batch: True=批量解析 / False=单个解析
    """
    from app.utils.document_parser import extract_text_from_bytes
    from app.utils.llm_utils import parse_llm_json_result, get_parse_prompt, ParseMode
    from app.utils.data_cleaner import clean_job_data_for_response, clean_batch_job_results
    from app.rag.chain import get_llm
    
    task_start = time.time()
    print(f"\n{'='*60}")
    print(f"[Celery Parse Task] 开始: filename={filename}, is_batch={is_batch}")
    print(f"{'='*60}")
    
    try:
        mode = ParseMode.BATCH if is_batch else ParseMode.SINGLE
        
        # ========== STEP 1: 文本提取（25%） ==========
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1, 'total': 4,
                'message': '正在提取文档文本...',
                'percent': 25
            }
        )
        
        full_text = extract_text_from_bytes(file_content, filename)
        if not full_text or not full_text.strip():
            return {
                "status": "error",
                "message": "无法提取文档文本内容"
            }
        
        print(f"[Celery Parse Task] STEP 1 完成，文本长度: {len(full_text)}")
        
        # ========== STEP 2: 调用LLM解析（50%） ==========
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 2, 'total': 4,
                'message': '正在调用AI分析文档...',
                'percent': 50
            }
        )
        
        prompt = get_parse_prompt(full_text, mode)
        llm = get_llm()
        llm_output = llm.invoke(prompt)
        llm_text = llm_output.content if hasattr(llm_output, 'content') else str(llm_output)
        
        try:
            result = parse_llm_json_result(llm_text)
        except:
            return {
                "status": "error",
                "message": "AI返回的JSON格式解析失败，请重试"
            }
        
        print(f"[Celery Parse Task] STEP 2 完成，LLM输出长度: {len(llm_text)}")
        
        # ========== STEP 3: 清洗结果（75%） ==========
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 3, 'total': 4,
                'message': '正在整理解析结果...',
                'percent': 75
            }
        )
        
        if is_batch:
            jobs = clean_batch_job_results(result)
            final_output = {
                "is_batch": True,
                "total": len(jobs),
                "jobs": jobs
            }
        else:
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            cleaned_data = clean_job_data_for_response(result, filename)
            final_output = {"is_batch": False, **cleaned_data}
        
        print(f"[Celery Parse Task] STEP 3 完成")
        
        # ========== STEP 4: 完成（100%） ==========
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 4, 'total': 4,
                'message': '解析完成',
                'percent': 100
            }
        )
        
        elapsed = time.time() - task_start
        print(f"[Celery Parse Task] 全部完成，耗时: {elapsed:.2f}s")
        print(f"{'='*60}\n")
        
        return {
            "status": "success",
            "filename": filename,
            "is_batch": is_batch,
            "result": final_output,
            "elapsed_time": round(elapsed, 2)
        }
        
    except Exception as e:
        print(f"[Celery Parse Task] 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return {
            "status": "error",
            "message": f"解析失败: {str(e)}"
        }


@celery_app.task(bind=True, name="app.services.recommendation_service.parse_resume_task")
def parse_resume_task(self, file_content: bytes, filename: str):
    """Celery 后台任务：简历文档解析"""
    from app.utils.document_parser import extract_text_from_bytes
    from app.utils.llm_utils import parse_llm_json_result
    from app.utils.resume_parse_utils import (
        build_resume_parse_prompt,
        extract_info_from_filename,
        normalize_resume_parse_result,
    )
    from app.rag.chain import get_llm

    task_start = time.time()
    print(f"\n{'='*60}")
    print(f"[Celery Resume Parse] 开始: filename={filename}")
    print(f"{'='*60}")

    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 1,
                "total": 3,
                "message": "正在提取简历文本...",
                "percent": 30,
            },
        )

        full_text = extract_text_from_bytes(file_content, filename)
        if not full_text or not full_text.strip():
            return {"status": "error", "message": "无法提取文本文档内容"}

        filename_info = extract_info_from_filename(filename)

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 2,
                "total": 3,
                "message": "正在调用 AI 解析简历...",
                "percent": 60,
            },
        )

        prompt = build_resume_parse_prompt(full_text, filename_info)
        llm = get_llm()
        llm_output = llm.invoke(prompt)
        llm_text = llm_output.content if hasattr(llm_output, "content") else str(llm_output)

        try:
            raw_result = parse_llm_json_result(llm_text)
        except Exception:
            return {"status": "error", "message": "AI 返回的 JSON 格式解析失败，请重试"}

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 3,
                "total": 3,
                "message": "正在整理解析结果...",
                "percent": 90,
            },
        )

        parsed = normalize_resume_parse_result(raw_result, filename_info)
        elapsed = time.time() - task_start
        print(f"[Celery Resume Parse] 完成，耗时: {elapsed:.2f}s")
        print(f"{'='*60}\n")

        return {
            "status": "success",
            "filename": filename,
            "result": parsed,
            "elapsed_time": round(elapsed, 2),
        }

    except Exception as e:
        print(f"[Celery Resume Parse] 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return {"status": "error", "message": f"解析失败: {str(e)}"}
