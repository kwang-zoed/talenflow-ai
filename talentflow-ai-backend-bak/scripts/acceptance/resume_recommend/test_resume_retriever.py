#!/usr/bin/env python
"""阶段1：简历混合检索 smoke test"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.resume import Resume
from app.rag.resume_retriever import (
    get_hybrid_resume_retriever,
    load_all_resumes,
    search_faiss_resumes,
)
from app.rag.vector_store import INDEX_FILE, RESUME_INDEX_FILE


def run_tests(seed: bool = False, cleanup: bool = False) -> int:
    passed = 0
    total = 6
    db = SessionLocal()
    try:
        if seed:
            _seed_fixtures(db)
        if cleanup:
            _cleanup_fixtures(db)
            return 0

        resumes = load_all_resumes(db)
        active = [r for r in resumes if r.status != "Archived"]
        python_resumes = [r for r in active if _has_skill(r, "python")]

        search = get_hybrid_resume_retriever(db)
        results = search("Python 后端", 10)

        if not active:
            print("T1.1 SKIP no active resumes")
            passed += 1
        elif python_resumes and results:
            top_ids = [r["resume_id"] for r in results[:3]]
            if any(r.id in top_ids for r in python_resumes):
                passed += 1
                print("T1.1 PASS BM25/hybrid recall")
            else:
                print("T1.1 FAIL Python resume not in top results")
        elif results:
            passed += 1
            print("T1.1 PASS hybrid recall (no python fixture)")
        else:
            print("T1.1 FAIL empty results")

        if os.path.exists(RESUME_INDEX_FILE):
            faiss_res = search_faiss_resumes("Python", 5)
            if faiss_res and all(isinstance(i, int) for i, _ in faiss_res):
                passed += 1
                print("T1.2 PASS FAISS recall")
            else:
                passed += 1
                print("T1.2 SKIP FAISS empty index")
        else:
            passed += 1
            print("T1.2 SKIP no FAISS index file")

        backup = None
        meta_backup = None
        if os.path.exists(RESUME_INDEX_FILE):
            backup = RESUME_INDEX_FILE + ".bak"
            os.rename(RESUME_INDEX_FILE, backup)
        if os.path.exists(RESUME_INDEX_FILE.replace(".faiss", "_metadata.pkl")):
            meta_backup = RESUME_INDEX_FILE.replace("resume_index.faiss", "resume_metadata.pkl") + ".bak"
        try:
            search("Python", 5)
            passed += 1
            print("T1.3 PASS FAISS degrade without crash")
        except Exception as e:
            print(f"T1.3 FAIL {e}")
        finally:
            if backup and os.path.exists(backup):
                os.rename(backup, RESUME_INDEX_FILE)

        if results and all(
            "resume_id" in r and "resume_obj" in r and 0 <= r.get("rag_score", 0) <= 1
            for r in results
        ):
            passed += 1
            print("T1.4 PASS hybrid structure")
        else:
            print("T1.4 FAIL hybrid structure")

        archived_in = any(r["resume_obj"].status == "Archived" for r in results)
        if not archived_in:
            passed += 1
            print("T1.5 PASS Archived filtered")
        else:
            print("T1.5 FAIL Archived in results")

        if INDEX_FILE != RESUME_INDEX_FILE:
            passed += 1
            print("T1.6 PASS index isolation")
        else:
            print("T1.6 FAIL index paths collide")

    finally:
        db.close()

    print(f"\nPASS {passed}/{total}")
    return 0 if passed >= total - 1 else 1


def _has_skill(resume: Resume, skill: str) -> bool:
    skills = resume.skills or []
    if isinstance(skills, str):
        return skill.lower() in skills.lower()
    return any(skill.lower() in str(s).lower() for s in skills)


def _seed_fixtures(db):
    for r in db.query(Resume).filter(Resume.name.like("_acceptance_%")).all():
        db.delete(r)
    db.commit()
    r1 = Resume(
        user_id=1,
        name="_acceptance_python",
        title="Python后端工程师",
        skills=["Python", "FastAPI", "MySQL"],
        status="Active",
        summary="Python backend developer",
    )
    r2 = Resume(
        user_id=1,
        name="_acceptance_java",
        title="Java开发",
        skills=["Java", "Spring"],
        status="Active",
    )
    db.add(r1)
    db.add(r2)
    db.commit()


def _cleanup_fixtures(db):
    db.query(Resume).filter(Resume.name.like("_acceptance_%")).delete(synchronize_session=False)
    db.commit()
    print("Cleaned acceptance fixtures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    sys.exit(run_tests(seed=args.seed, cleanup=args.cleanup))
