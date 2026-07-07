from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import time
import logging

from app.models import base
from app.models.resume import Resume
from app.models.job_position import JobPosition
from app.models.user_profile import UserProfile
from app.rag.retriever import get_hybrid_retriever
from app.rag.resume_retriever import get_hybrid_resume_retriever, parse_resume_skills, resume_to_text
from app.rag.reranker import get_reranker
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.recommend_session_store import (
    load_recommend_session,
    patch_recommend_session,
    save_recommend_session,
)
from app.services.recommend_session_tasks import rerank_recommend_session_task
from app.services.location_service import (
    build_distance_fields,
    get_user_profile,
    resolve_job_coords,
    resolve_resume_coords,
)

import uuid

COARSE_POOL_SIZE = 100
RERANK_POOL_SIZE = 50


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

    def _job_coords(self, job: Optional[JobPosition]):
        if not job:
            return None
        return resolve_job_coords(job)

    def _load_profiles_for_users(self, user_ids: set) -> Dict[int, UserProfile]:
        if not user_ids:
            return {}
        rows = self.db.query(UserProfile).filter(UserProfile.user_id.in_(user_ids)).all()
        return {row.user_id: row for row in rows}

    def _user_location_context(self, user_id: int, resume: Optional[Resume] = None):
        if resume is None:
            resume = self.get_user_resume(user_id)
        profile = get_user_profile(self.db, user_id)
        coords = resolve_resume_coords(resume, profile) if resume else None
        city = None
        if resume and not getattr(resume, "use_profile_location", 1) and resume.residence_city:
            city = resume.residence_city
        elif profile and profile.residence_city:
            city = profile.residence_city
        elif resume and resume.residence_city:
            city = resume.residence_city
        return coords, city

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

    @staticmethod
    def _parse_skills_list(raw) -> set:
        skills_set = set()
        if not raw:
            return skills_set
        if isinstance(raw, list):
            for s in raw:
                if s:
                    skills_set.add(str(s).strip().lower())
            return skills_set
        try:
            skills_list = json.loads(raw)
            if isinstance(skills_list, list):
                for s in skills_list:
                    if s:
                        skills_set.add(str(s).strip().lower())
        except (json.JSONDecodeError, TypeError):
            pass
        return skills_set

    def extract_job_info(self, job: JobPosition) -> Dict[str, Any]:
        text_parts = []
        if job.title:
            text_parts.append(job.title)
        if job.company:
            text_parts.append(job.company)
        if job.description:
            text_parts.append(job.description)
        if job.location:
            text_parts.append(job.location)
        if job.experience_requirement:
            text_parts.append(job.experience_requirement)
        if job.education_requirement:
            text_parts.append(job.education_requirement)
        if job.required_skills:
            text_parts.append(" ".join(job.required_skills))
        search_text = " ".join(text_parts)
        job_skills = self._parse_skills_list(job.required_skills)
        return {"search_text": search_text, "skills": job_skills}

    def _resume_to_dict(self, resume: Resume, mask_contact: bool = False) -> Dict[str, Any]:
        data = {}
        if hasattr(resume, "__dict__"):
            data = {k: v for k, v in resume.__dict__.items() if not k.startswith("_")}
        if mask_contact:
            if data.get("phone"):
                phone = str(data["phone"])
                data["phone"] = phone[:3] + "****" + phone[-2:] if len(phone) > 5 else "****"
            if data.get("email") and "@" in str(data["email"]):
                local, domain = str(data["email"]).split("@", 1)
                data["email"] = (local[:2] + "***@" + domain) if local else "***@" + domain
        return data

    def recommend_resumes(self, job_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        print("=" * 60)
        print(f" [RECOMMEND SERVICE] 开始简历推荐: job_id={job_id}, top_k={top_k}")

        job = self.db.get(JobPosition, job_id)
        if not job:
            print(f" [RECOMMEND SERVICE] 职位不存在，返回空")
            print("=" * 60)
            return []

        job_info = self.extract_job_info(job)
        search_text = job_info["search_text"]
        job_skills = job_info["skills"]

        coarse_count = top_k * 5
        search_func = get_hybrid_resume_retriever(self.db)
        merged_candidates = search_func(search_text, coarse_count)

        candidate_list = []
        for item in merged_candidates:
            resume_obj = item["resume_obj"]
            resume_skills = parse_resume_skills(resume_obj)
            if job_skills and resume_skills:
                matched_lower = job_skills & resume_skills
                skill_score = len(matched_lower) / len(job_skills)
            else:
                matched_lower = set()
                skill_score = 0

            rag_score = item.get("rag_score", 0)
            final_score = rag_score * 0.7 + skill_score * 0.3
            candidate_list.append({
                "resume_id": item["resume_id"],
                "resume_obj": resume_obj,
                "rag_score": rag_score,
                "skill_score": skill_score,
                "final_score": final_score,
                "matched_lower": matched_lower,
            })

        candidate_list.sort(key=lambda x: x["final_score"], reverse=True)
        top_for_rerank = candidate_list[:coarse_count]

        reranker = get_reranker()
        if reranker and top_for_rerank:
            try:
                passages = [resume_to_text(c["resume_obj"])[:1000] for c in top_for_rerank]
                rerank_scores = reranker.compute_score(search_text[:1000], passages)
                for i, score in enumerate(rerank_scores):
                    if i < len(top_for_rerank):
                        top_for_rerank[i]["rerank_score"] = float(score)
                top_for_rerank.sort(key=lambda x: x.get("rerank_score", x["final_score"]), reverse=True)
                print(" [RECOMMEND SERVICE] Reranker 精排完成")
            except Exception as e:
                logger.warning("[RECOMMEND SERVICE] Reranker 精排失败，使用粗排结果: %s", e)
        else:
            print(" [RECOMMEND SERVICE] Reranker 未加载，使用粗排结果")

        job_skill_display = {}
        if job.required_skills:
            for s in job.required_skills:
                if s:
                    job_skill_display[str(s).strip().lower()] = str(s).strip()

        results = []
        for item in top_for_rerank[:top_k]:
            resume = item.get("resume_obj")
            if not resume:
                continue
            matched_lower = item.get("matched_lower") or set()
            matched_skills = [
                job_skill_display.get(k, k) for k in matched_lower if k in job_skill_display
            ] or sorted(matched_lower)
            final_score = float(item.get("final_score", item.get("rag_score", 0)) or 0)
            results.append({
                "resume": self._resume_to_dict(resume, mask_contact=True),
                "score": int(final_score * 100),
                "matched_skills": matched_skills,
            })

        print(f" [RECOMMEND SERVICE] 返回简历推荐数: {len(results)}")
        print("=" * 60)
        return results

    # ---------- 会话式推荐：首屏粗排 + 后台精排 + exclude_ids 翻页 ----------

    def _build_job_skill_display(self, job: JobPosition) -> Dict[str, str]:
        job_skill_display = {}
        if job.required_skills:
            for s in job.required_skills:
                if s:
                    job_skill_display[str(s).strip().lower()] = str(s).strip()
        return job_skill_display

    def _build_coarse_candidate_pool(self, job_id: int, pool_size: int = COARSE_POOL_SIZE) -> tuple:
        job = self.db.get(JobPosition, job_id)
        if not job:
            return None, [], {}

        job_info = self.extract_job_info(job)
        search_text = job_info["search_text"]
        job_skills = job_info["skills"]

        search_func = get_hybrid_resume_retriever(self.db)
        merged_candidates = search_func(search_text, pool_size)

        candidate_list = []
        for item in merged_candidates:
            resume_obj = item["resume_obj"]
            resume_skills = parse_resume_skills(resume_obj)
            if job_skills and resume_skills:
                matched_lower = job_skills & resume_skills
                skill_score = len(matched_lower) / len(job_skills)
            else:
                matched_lower = set()
                skill_score = 0

            rag_score = item.get("rag_score", 0)
            final_score = rag_score * 0.7 + skill_score * 0.3
            candidate_list.append({
                "resume_id": item["resume_id"],
                "resume_obj": resume_obj,
                "rag_score": rag_score,
                "skill_score": skill_score,
                "final_score": final_score,
                "matched_lower": matched_lower,
            })

        candidate_list.sort(key=lambda x: x["final_score"], reverse=True)
        return job, candidate_list[:pool_size], self._build_job_skill_display(job)

    @staticmethod
    def _serialize_pool_item(item: Dict[str, Any]) -> Dict[str, Any]:
        matched = item.get("matched_lower") or set()
        if isinstance(matched, set):
            matched = sorted(matched)
        return {
            "resume_id": item["resume_id"],
            "final_score": float(item.get("final_score", 0) or 0),
            "skill_score": float(item.get("skill_score", 0) or 0),
            "rag_score": float(item.get("rag_score", 0) or 0),
            "matched_lower": list(matched),
            "rerank_score": item.get("rerank_score"),
            "display_score": item.get("display_score"),
        }

    @staticmethod
    def _take_from_pool(
        pool: List[Dict[str, Any]],
        exclude_ids: set,
        limit: int,
        id_key: str = "resume_id",
    ) -> List[Dict[str, Any]]:
        picked = []
        for item in pool:
            rid = item[id_key]
            if rid in exclude_ids:
                continue
            picked.append(item)
            if len(picked) >= limit:
                break
        return picked

    @staticmethod
    def _pool_has_more(pool: List[Dict[str, Any]], exclude_ids: set, id_key: str = "resume_id") -> bool:
        for item in pool:
            if item[id_key] not in exclude_ids:
                return True
        return False

    @staticmethod
    def _apply_rerank_display_scores(items: List[Dict[str, Any]]) -> None:
        """精排只改变排序；展示分在粗排基础上按顺位微调，避免 min-max 映射到 65~100 导致虚高。"""
        n = len(items)
        for rank, item in enumerate(items):
            coarse_pct = int(float(item.get("final_score", item.get("rag_score", 0)) or 0) * 100)
            if item.get("rerank_score") is None:
                item["display_score"] = coarse_pct
                continue
            if n <= 1:
                boost = 0
            else:
                # 精排第 1 名 +10，末位 -8，中间线性插值
                boost = int(round(10 - (rank / (n - 1)) * 18))
            item["display_score"] = max(1, min(99, coarse_pct + boost))

    def _pool_items_to_results(
        self,
        pool_items: List[Dict[str, Any]],
        job_skill_display: Dict[str, str],
        use_rerank: bool = False,
        job: Optional[JobPosition] = None,
    ) -> List[Dict[str, Any]]:
        if not pool_items:
            return []

        resume_ids = [x["resume_id"] for x in pool_items]
        stmt = select(Resume).where(Resume.id.in_(resume_ids))
        resumes = {r.id: r for r in self.db.execute(stmt).scalars().all()}
        profiles = self._load_profiles_for_users({r.user_id for r in resumes.values()})
        job_coords = self._job_coords(job)

        results = []
        for item in pool_items:
            resume = resumes.get(item["resume_id"])
            if not resume:
                continue
            matched_lower = set(item.get("matched_lower") or [])
            matched_skills = [
                job_skill_display.get(k, k) for k in matched_lower if k in job_skill_display
            ] or sorted(matched_lower)
            if use_rerank and item.get("display_score") is not None:
                score = int(item["display_score"])
            else:
                score = int(float(item.get("final_score", item.get("rag_score", 0)) or 0) * 100)
            profile = profiles.get(resume.user_id)
            resume_coords = resolve_resume_coords(resume, profile)
            if getattr(resume, "use_profile_location", 1) and profile and profile.residence_city:
                origin_city = profile.residence_city
            else:
                origin_city = resume.residence_city or (profile.residence_city if profile else None)
            distance = build_distance_fields(
                origin_coords=resume_coords,
                target_coords=job_coords,
                origin_city=origin_city,
                target_city=job.location if job else None,
                target_location_text=job.location if job else None,
            )
            results.append({
                "resume": self._resume_to_dict(resume, mask_contact=True),
                "score": score,
                "matched_skills": matched_skills,
                "ranking": "rerank" if use_rerank and item.get("rerank_score") is not None else "coarse",
                **distance,
            })
        return results

    def _active_pool(self, session: Dict[str, Any]) -> tuple:
        if (
            session.get("rerank_applied")
            and session.get("status") == "rerank_ready"
            and session.get("rerank_items")
        ):
            return session["rerank_items"], True
        return session.get("coarse_items") or [], False

    def create_recommend_session(self, job_id: int, page_size: int = 10) -> Dict[str, Any]:
        job, coarse_pool, job_skill_display = self._build_coarse_candidate_pool(job_id, COARSE_POOL_SIZE)
        if not job:
            return {"status": "error", "message": "职位不存在"}

        coarse_items = [self._serialize_pool_item(x) for x in coarse_pool]
        session_id = str(uuid.uuid4())
        first_batch = self._take_from_pool(coarse_items, set(), page_size)
        results = self._pool_items_to_results(first_batch, job_skill_display, use_rerank=False, job=job)
        shown_ids = {x["resume_id"] for x in first_batch}

        session = {
            "session_id": session_id,
            "kind": "resume",
            "job_id": job_id,
            "job_title": job.title or f"职位 #{job_id}",
            "status": "coarse_ready",
            "coarse_items": coarse_items,
            "rerank_items": [],
            "rerank_applied": False,
            "job_skill_display": job_skill_display,
        }
        save_recommend_session(session_id, session)

        return {
            "status": "success",
            "session_id": session_id,
            "job_id": job_id,
            "data": results,
            "has_more": self._pool_has_more(coarse_items, shown_ids),
            "ranking": "coarse",
            "session_status": "coarse_ready",
            "coarse_total": len(coarse_items),
        }

    def get_recommend_session_more(
        self,
        session_id: str,
        exclude_ids: Optional[List[int]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        session = load_recommend_session(session_id)
        if not session:
            return {"status": "error", "message": "推荐会话不存在或已过期"}

        kind = session.get("kind", "resume")
        exclude = set(exclude_ids or [])
        pool, use_rerank = self._active_pool(session)
        id_key = "job_id" if kind == "job" else "resume_id"
        batch = self._take_from_pool(pool, exclude, limit, id_key=id_key)

        if kind == "job":
            origin_coords, origin_city = self._user_location_context(session.get("user_id"))
            results = self._pool_job_items_to_results(
                batch,
                session.get("user_skill_display") or {},
                use_rerank=use_rerank,
                origin_coords=origin_coords,
                origin_city=origin_city,
            )
        else:
            job = self.db.get(JobPosition, session.get("job_id"))
            results = self._pool_items_to_results(
                batch,
                session.get("job_skill_display") or {},
                use_rerank=use_rerank,
                job=job,
            )

        next_exclude = exclude | {x[id_key] for x in batch}
        pool_total = len(pool)
        return {
            "status": "success",
            "session_id": session_id,
            "job_id": session.get("job_id"),
            "user_id": session.get("user_id"),
            "data": results,
            "has_more": self._pool_has_more(pool, next_exclude, id_key=id_key),
            "ranking": "rerank" if use_rerank else "coarse",
            "session_status": session.get("status", "coarse_ready"),
            "coarse_total": len(session.get("coarse_items") or []),
            "rerank_total": len(session.get("rerank_items") or []),
            "pool_total": pool_total,
            "rerank_applied": bool(session.get("rerank_applied")),
        }

    def get_recommend_session_status(self, session_id: str) -> Dict[str, Any]:
        session = load_recommend_session(session_id)
        if not session:
            return {"status": "error", "message": "推荐会话不存在或已过期"}
        rerank_available = (
            session.get("status") == "rerank_ready" and bool(session.get("rerank_items"))
        )
        rerank_applied = bool(session.get("rerank_applied"))
        return {
            "status": "success",
            "session_id": session_id,
            "kind": session.get("kind", "resume"),
            "job_id": session.get("job_id"),
            "user_id": session.get("user_id"),
            "session_status": session.get("status", "coarse_ready"),
            "rerank_available": rerank_available,
            "rerank_applied": rerank_applied,
            "ranking": "rerank" if rerank_applied and rerank_available else "coarse",
            "coarse_total": len(session.get("coarse_items") or []),
            "rerank_total": len(session.get("rerank_items") or []),
        }

    def apply_session_rerank_view(self, session_id: str, limit: int = 10) -> Dict[str, Any]:
        """用户点击「应用精排」：未启动则触发 Celery 精排，完成后按精排池重排列表。"""
        session = load_recommend_session(session_id)
        if not session:
            return {"status": "error", "message": "推荐会话不存在或已过期"}

        current_status = session.get("status", "coarse_ready")
        base_payload = {
            "session_id": session_id,
            "kind": session.get("kind", "resume"),
            "job_id": session.get("job_id"),
            "user_id": session.get("user_id"),
            "rerank_applied": bool(session.get("rerank_applied")),
        }

        if current_status == "coarse_ready":
            patch_recommend_session(session_id, {"status": "rerank_queued"})
            rerank_recommend_session_task.delay(session_id)
            return {
                **base_payload,
                "status": "processing",
                "session_status": "rerank_queued",
                "rerank_available": False,
                "message": "精排任务已加入队列",
            }

        if current_status in ("rerank_queued", "reranking"):
            return {
                **base_payload,
                "status": "processing",
                "session_status": current_status,
                "rerank_available": False,
                "message": "精排排队中" if current_status == "rerank_queued" else "精排进行中",
            }

        if current_status != "rerank_ready" or not session.get("rerank_items"):
            return {"status": "error", "message": "精排尚未完成，请稍后再试"}

        kind = session.get("kind", "resume")
        id_key = "job_id" if kind == "job" else "resume_id"
        pool = session["rerank_items"]
        limit = min(max(limit, 1), RERANK_POOL_SIZE)
        batch = self._take_from_pool(pool, set(), limit, id_key=id_key)

        if kind == "job":
            origin_coords, origin_city = self._user_location_context(session.get("user_id"))
            results = self._pool_job_items_to_results(
                batch,
                session.get("user_skill_display") or {},
                use_rerank=True,
                origin_coords=origin_coords,
                origin_city=origin_city,
            )
        else:
            job = self.db.get(JobPosition, session.get("job_id"))
            results = self._pool_items_to_results(
                batch,
                session.get("job_skill_display") or {},
                use_rerank=True,
                job=job,
            )

        shown_ids = {x[id_key] for x in batch}
        patch_recommend_session(session_id, {"rerank_applied": True})

        return {
            "status": "success",
            "session_id": session_id,
            "job_id": session.get("job_id"),
            "user_id": session.get("user_id"),
            "data": results,
            "has_more": self._pool_has_more(pool, shown_ids, id_key=id_key),
            "ranking": "rerank",
            "session_status": "rerank_ready",
            "rerank_applied": True,
        }

    def complete_session_rerank(self, session_id: str) -> None:
        session = load_recommend_session(session_id)
        if not session or session.get("status") == "rerank_ready":
            return
        if session.get("kind") == "job":
            self._complete_job_session_rerank(session_id, session)
        else:
            self._complete_resume_session_rerank(session_id, session)

    def _complete_resume_session_rerank(self, session_id: str, session: Dict[str, Any]) -> None:
        patch_recommend_session(session_id, {"status": "reranking"})

        job = self.db.get(JobPosition, session["job_id"])
        if not job:
            patch_recommend_session(session_id, {"status": "error"})
            return

        job_info = self.extract_job_info(job)
        search_text = job_info["search_text"]
        coarse_items = list(session.get("coarse_items") or [])[:RERANK_POOL_SIZE]
        if not coarse_items:
            patch_recommend_session(session_id, {"status": "rerank_ready", "rerank_items": []})
            return

        resume_ids = [x["resume_id"] for x in coarse_items]
        stmt = select(Resume).where(Resume.id.in_(resume_ids))
        resumes = {r.id: r for r in self.db.execute(stmt).scalars().all()}

        rerank_items = [dict(x) for x in coarse_items]
        reranker = get_reranker()
        if reranker:
            try:
                passages = []
                for item in rerank_items:
                    resume = resumes.get(item["resume_id"])
                    passages.append(resume_to_text(resume)[:1000] if resume else "")
                rerank_scores = reranker.compute_score(search_text[:1000], passages)
                for i, score in enumerate(rerank_scores):
                    if i < len(rerank_items):
                        rerank_items[i]["rerank_score"] = float(score)
                rerank_items.sort(
                    key=lambda x: x.get("rerank_score", x.get("final_score", 0)),
                    reverse=True,
                )
                self._apply_rerank_display_scores(rerank_items)
            except Exception as e:
                logger.warning("[RECOMMEND SESSION] 精排失败，保留粗排: %s", e)

        patch_recommend_session(session_id, {
            "status": "rerank_ready",
            "rerank_items": rerank_items,
        })
        logger.info("[RECOMMEND SESSION] 精排完成 session_id=%s count=%s", session_id, len(rerank_items))

    def _job_to_dict(self, job: JobPosition) -> Dict[str, Any]:
        if hasattr(job, "__dict__"):
            return {k: v for k, v in job.__dict__.items() if not k.startswith("_")}
        return {"id": job.id}

    @staticmethod
    def _job_to_text(job: JobPosition) -> str:
        parts = []
        if job.title:
            parts.append(job.title)
        if job.company:
            parts.append(job.company)
        if job.description:
            parts.append(job.description)
        if job.required_skills:
            parts.append(" ".join(job.required_skills))
        return " ".join(parts)

    def _build_user_skill_display(self, resume: Resume) -> Dict[str, str]:
        display = {}
        if resume.skills and isinstance(resume.skills, list):
            for s in resume.skills:
                if s:
                    display[str(s).strip().lower()] = str(s).strip()
        elif resume.skills:
            try:
                skills_list = json.loads(resume.skills)
                if isinstance(skills_list, list):
                    for s in skills_list:
                        if s:
                            display[str(s).strip().lower()] = str(s).strip()
            except (json.JSONDecodeError, TypeError):
                pass
        return display

    def _build_coarse_job_pool(self, resume_info: Dict[str, Any], pool_size: int = COARSE_POOL_SIZE) -> List[Dict[str, Any]]:
        search_text = resume_info["search_text"]
        user_skills = resume_info["skills"]

        search_func = get_hybrid_retriever(self.db)
        merged_candidates = search_func(search_text, pool_size)

        candidate_list = []
        for item in merged_candidates:
            job_obj = item["job_obj"]
            job_skills = self._parse_skills_list(getattr(job_obj, "required_skills", None))
            if job_skills and user_skills:
                matched_lower = user_skills & job_skills
                skill_score = len(matched_lower) / len(job_skills)
            else:
                matched_lower = set()
                skill_score = 0

            rag_score = item.get("rag_score", 0)
            final_score = rag_score * 0.7 + skill_score * 0.3
            candidate_list.append({
                "job_id": item["job_id"],
                "rag_score": rag_score,
                "skill_score": skill_score,
                "final_score": final_score,
                "matched_lower": matched_lower,
            })

        candidate_list.sort(key=lambda x: x["final_score"], reverse=True)
        return candidate_list[:pool_size]

    @staticmethod
    def _serialize_job_pool_item(item: Dict[str, Any]) -> Dict[str, Any]:
        matched = item.get("matched_lower") or set()
        if isinstance(matched, set):
            matched = sorted(matched)
        return {
            "job_id": item["job_id"],
            "final_score": float(item.get("final_score", 0) or 0),
            "skill_score": float(item.get("skill_score", 0) or 0),
            "rag_score": float(item.get("rag_score", 0) or 0),
            "matched_lower": list(matched),
            "rerank_score": item.get("rerank_score"),
            "display_score": item.get("display_score"),
        }

    def _pool_job_items_to_results(
        self,
        pool_items: List[Dict[str, Any]],
        user_skill_display: Dict[str, str],
        use_rerank: bool = False,
        origin_coords=None,
        origin_city: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not pool_items:
            return []

        job_ids = [x["job_id"] for x in pool_items]
        stmt = select(JobPosition).where(JobPosition.id.in_(job_ids))
        jobs = {j.id: j for j in self.db.execute(stmt).scalars().all()}

        results = []
        for item in pool_items:
            job = jobs.get(item["job_id"])
            if not job:
                continue
            matched_lower = set(item.get("matched_lower") or [])
            matched_skills = [
                user_skill_display.get(k, k) for k in matched_lower if k in user_skill_display
            ] or sorted(matched_lower)
            if use_rerank and item.get("display_score") is not None:
                score = int(item["display_score"])
            else:
                score = int(float(item.get("final_score", item.get("rag_score", 0)) or 0) * 100)
            job_coords = self._job_coords(job)
            distance = build_distance_fields(
                origin_coords=origin_coords,
                target_coords=job_coords,
                origin_city=origin_city,
                target_city=job.location,
                target_location_text=job.location,
            )
            results.append({
                "job": self._job_to_dict(job),
                "score": score,
                "matched_skills": matched_skills,
                "ranking": "rerank" if use_rerank and item.get("rerank_score") is not None else "coarse",
                **distance,
            })
        return results

    def create_job_recommend_session(self, user_id: int, page_size: int = 10) -> Dict[str, Any]:
        resume = self.get_user_resume(user_id)
        if not resume:
            return {"status": "error", "message": "请先创建简历"}

        resume_info = self.extract_user_resume_info(resume)
        coarse_pool = self._build_coarse_job_pool(resume_info, COARSE_POOL_SIZE)
        user_skill_display = self._build_user_skill_display(resume)
        coarse_items = [self._serialize_job_pool_item(x) for x in coarse_pool]

        session_id = str(uuid.uuid4())
        first_batch = self._take_from_pool(coarse_items, set(), page_size, id_key="job_id")
        origin_coords, origin_city = self._user_location_context(user_id, resume)
        results = self._pool_job_items_to_results(
            first_batch,
            user_skill_display,
            use_rerank=False,
            origin_coords=origin_coords,
            origin_city=origin_city,
        )
        shown_ids = {x["job_id"] for x in first_batch}

        session = {
            "session_id": session_id,
            "kind": "job",
            "user_id": user_id,
            "status": "coarse_ready",
            "coarse_items": coarse_items,
            "rerank_items": [],
            "rerank_applied": False,
            "user_skill_display": user_skill_display,
            "search_text": resume_info["search_text"],
        }
        save_recommend_session(session_id, session)

        return {
            "status": "success",
            "session_id": session_id,
            "user_id": user_id,
            "data": results,
            "has_more": self._pool_has_more(coarse_items, shown_ids, id_key="job_id"),
            "ranking": "coarse",
            "session_status": "coarse_ready",
        }

    def _complete_job_session_rerank(self, session_id: str, session: Dict[str, Any]) -> None:
        patch_recommend_session(session_id, {"status": "reranking"})

        search_text = session.get("search_text") or ""
        coarse_items = list(session.get("coarse_items") or [])[:RERANK_POOL_SIZE]
        if not coarse_items:
            patch_recommend_session(session_id, {"status": "rerank_ready", "rerank_items": []})
            return

        job_ids = [x["job_id"] for x in coarse_items]
        stmt = select(JobPosition).where(JobPosition.id.in_(job_ids))
        jobs = {j.id: j for j in self.db.execute(stmt).scalars().all()}

        rerank_items = [dict(x) for x in coarse_items]
        reranker = get_reranker()
        if reranker and search_text:
            try:
                passages = []
                for item in rerank_items:
                    job = jobs.get(item["job_id"])
                    passages.append(self._job_to_text(job)[:1000] if job else "")
                rerank_scores = reranker.compute_score(search_text[:1000], passages)
                for i, score in enumerate(rerank_scores):
                    if i < len(rerank_items):
                        rerank_items[i]["rerank_score"] = float(score)
                rerank_items.sort(
                    key=lambda x: x.get("rerank_score", x.get("final_score", 0)),
                    reverse=True,
                )
                self._apply_rerank_display_scores(rerank_items)
            except Exception as e:
                logger.warning("[JOB RECOMMEND SESSION] 精排失败，保留粗排: %s", e)

        patch_recommend_session(session_id, {
            "status": "rerank_ready",
            "rerank_items": rerank_items,
        })
        logger.info("[JOB RECOMMEND SESSION] 精排完成 session_id=%s count=%s", session_id, len(rerank_items))

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
            try:
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
            except Exception as e:
                logger.warning("[RECOMMEND SERVICE] Reranker 精排失败，使用粗排结果: %s", e)
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


@celery_app.task(bind=True, name="app.recommendation_service.generate_resume_recommendation_task")
def generate_resume_recommendation_task(self, job_id: int, top_k: int = 5):
    """后台异步执行的简历推荐任务（HR：职位 → 简历）"""
    start_time = time.time()
    try:
        logger.info(f"[Celery Worker] 开始为职位 {job_id} 异步生成简历推荐...")
        db = SessionLocal()
        try:
            service = RecommendationService(db)
            results = service.recommend_resumes(job_id, top_k)
            elapsed_time = time.time() - start_time
            return {
                "status": "success",
                "result": results,
                "job_id": job_id,
                "elapsed_time": elapsed_time,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[Celery Worker] 简历推荐任务失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


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
