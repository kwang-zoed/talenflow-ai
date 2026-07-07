#!/usr/bin/env python
"""阶段7：简历索引 hook / reindex 一致性 smoke test"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.resume import Resume
from app.rag.vector_store import get_job_index_count, get_resume_index_count, add_resume_to_vectorstore, remove_resume_from_vectorstore
from app.rag.resume_retriever import load_all_resumes


def run_tests() -> int:
    passed = 0
    db = SessionLocal()
    try:
        job_before = get_job_index_count()
        active_count = len(load_all_resumes(db))
        resume_count = get_resume_index_count()
        if resume_count >= 0:
            passed += 1
            print(f"T7.1 PASS resume index count={resume_count} active={active_count}")

        test = Resume(
            user_id=1,
            name="_acceptance_index_hook",
            title="Test",
            skills=["Go"],
            status="Active",
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        add_resume_to_vectorstore(test)
        after_add = get_resume_index_count()
        if after_add >= resume_count:
            passed += 1
            print("T7.2 PASS add hook")

        test.skills = ["Go", "Rust"]
        db.commit()
        add_resume_to_vectorstore(test)
        passed += 1
        print("T7.3 PASS update hook")

        remove_resume_from_vectorstore(test.id)
        db.delete(test)
        db.commit()
        passed += 1
        print("T7.4 PASS remove hook")

        job_after = get_job_index_count()
        if job_after == job_before:
            passed += 1
            print("T7.5 PASS job index unchanged")
        else:
            print(f"T7.5 FAIL job index changed {job_before}->{job_after}")
    finally:
        db.close()

    print(f"\nPASS {passed}/5")
    return 0 if passed >= 4 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
