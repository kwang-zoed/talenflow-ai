"""批量补全已有职位/简历/用户资料的地理坐标。"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.bootstrap import load_all_models
from app.models.job_position import JobPosition
from app.models.resume import Resume
from app.models.user_profile import UserProfile
from app.services.location_service import apply_geocode_to_job, apply_geocode_to_profile, apply_geocode_to_resume

load_all_models()


def main():
    db = SessionLocal()
    updated = 0
    try:
        for profile in db.query(UserProfile).all():
            apply_geocode_to_profile(profile)
            db.add(profile)
            updated += 1
            time.sleep(0.2)
        for resume in db.query(Resume).all():
            apply_geocode_to_resume(resume)
            db.add(resume)
            updated += 1
            time.sleep(0.2)
        for job in db.query(JobPosition).all():
            apply_geocode_to_job(job)
            db.add(job)
            updated += 1
            time.sleep(0.2)
        db.commit()
        print(f"backfill done, processed={updated}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
