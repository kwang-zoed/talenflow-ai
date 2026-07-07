#!/usr/bin/env python
"""阶段2：recommend_resumes 同步服务 smoke test"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.recommendation_service import RecommendationService


def run_tests(job_id: int) -> int:
    passed = 0
    total = 6
    db = SessionLocal()
    try:
        service = RecommendationService(db)
        results = service.recommend_resumes(job_id, top_k=3)
        if isinstance(results, list) and len(results) <= 3:
            passed += 1
            print("T2.1 PASS returns list")
        else:
            print("T2.1 FAIL")

        if not results or all(
            "resume" in r and "score" in r and "matched_skills" in r for r in results
        ):
            passed += 1
            print("T2.2 PASS response shape")
        else:
            print("T2.2 FAIL")

        if not results or any(r.get("matched_skills") for r in results):
            passed += 1
            print("T2.3 PASS matched_skills")
        else:
            print("T2.3 SKIP/ FAIL no matched_skills")

        if len(results) <= 1 or all(
            results[i]["score"] >= results[i + 1]["score"] for i in range(len(results) - 1)
        ):
            passed += 1
            print("T2.4 PASS sort order")
        else:
            print("T2.4 FAIL")

        empty = service.recommend_resumes(999999999, top_k=3)
        if empty == []:
            passed += 1
            print("T2.5 PASS invalid job_id")
        else:
            print("T2.5 FAIL")

        passed += 1
        print("T2.6 PASS no crash")
        for r in results[:3]:
            name = (r.get("resume") or {}).get("name", "?")
            print(f"  - {name} score={r.get('score')} skills={r.get('matched_skills')}")
    finally:
        db.close()

    print(f"\nPASS {passed}/{total}")
    return 0 if passed >= 5 else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--job-id", type=int, default=1)
    sys.exit(run_tests(p.parse_args().job_id))
