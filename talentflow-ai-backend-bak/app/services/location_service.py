"""所在地坐标解析与距离附加。"""
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.job_position import JobPosition
from app.models.resume import Resume
from app.models.user_profile import UserProfile
from app.services.geocoding_service import geocode
from app.utils.distance_utils import (
    extract_city_label,
    format_distance,
    haversine_km,
    is_remote_location,
)


def _coords_from_location(
    city: Optional[str],
    address: Optional[str],
    lat: Optional[float],
    lng: Optional[float],
) -> Optional[Tuple[float, float]]:
    if lat is not None and lng is not None:
        return lat, lng
    if city or address:
        return geocode(city, address)
    return None


def resolve_resume_coords(resume: Resume, profile: Optional[UserProfile]) -> Optional[Tuple[float, float]]:
    use_profile = getattr(resume, "use_profile_location", 1)
    if not use_profile:
        return _coords_from_location(
            resume.residence_city,
            resume.residence_address,
            resume.latitude,
            resume.longitude,
        )
    if profile:
        coords = _coords_from_location(
            profile.residence_city,
            profile.residence_address,
            profile.latitude,
            profile.longitude,
        )
        if coords:
            return coords
    return _coords_from_location(
        resume.residence_city,
        resume.residence_address,
        resume.latitude,
        resume.longitude,
    )


def resolve_job_coords(job: JobPosition) -> Optional[Tuple[float, float]]:
    if is_remote_location(job.location):
        return None
    return _coords_from_location(job.location, job.work_address, job.latitude, job.longitude)


def apply_geocode_to_profile(profile: UserProfile) -> None:
    if not profile.residence_city and not profile.residence_address:
        profile.latitude = None
        profile.longitude = None
        profile.geocoded_at = None
        return
    coords = geocode(profile.residence_city, profile.residence_address)
    if coords:
        profile.latitude, profile.longitude = coords
        profile.geocoded_at = datetime.utcnow()
    else:
        profile.latitude = None
        profile.longitude = None
        profile.geocoded_at = None


def apply_geocode_to_resume(resume: Resume) -> None:
    if getattr(resume, "use_profile_location", 1):
        resume.latitude = None
        resume.longitude = None
        return
    if not resume.residence_city and not resume.residence_address:
        resume.latitude = None
        resume.longitude = None
        return
    coords = geocode(resume.residence_city, resume.residence_address)
    if coords:
        resume.latitude, resume.longitude = coords
    else:
        resume.latitude = None
        resume.longitude = None


def apply_geocode_to_job(job: JobPosition) -> None:
    if is_remote_location(job.location):
        job.latitude = None
        job.longitude = None
        job.geocoded_at = None
        return
    if not job.location and not job.work_address:
        job.latitude = None
        job.longitude = None
        job.geocoded_at = None
        return
    coords = geocode(job.location, job.work_address)
    if coords:
        job.latitude, job.longitude = coords
        job.geocoded_at = datetime.utcnow()
    else:
        job.latitude = None
        job.longitude = None
        job.geocoded_at = None


def get_user_profile(db: Session, user_id: int) -> Optional[UserProfile]:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def get_or_create_user_profile(db: Session, user_id: int) -> UserProfile:
    profile = get_user_profile(db, user_id)
    if profile:
        return profile
    profile = UserProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def build_distance_fields(
    *,
    origin_coords: Optional[Tuple[float, float]],
    target_coords: Optional[Tuple[float, float]],
    origin_city: Optional[str],
    target_city: Optional[str],
    target_location_text: Optional[str] = None,
) -> Dict[str, Any]:
    if is_remote_location(target_location_text or target_city):
        return {
            "distance_km": None,
            "distance_text": "远程",
            "candidate_city": extract_city_label(origin_city),
            "job_location": target_city or target_location_text,
        }

    distance_km = None
    if origin_coords and target_coords:
        distance_km = round(haversine_km(*origin_coords, *target_coords), 1)

    if distance_km is not None:
        distance_text = format_distance(distance_km)
    elif not origin_coords:
        distance_text = "距离待计算" if origin_city else "未填写所在地"
    elif not target_coords:
        distance_text = "距离未知"
    else:
        distance_text = "距离未知"

    return {
        "distance_km": distance_km,
        "distance_text": distance_text,
        "candidate_city": extract_city_label(origin_city),
        "job_location": target_city or target_location_text,
    }
