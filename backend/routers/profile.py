from fastapi import APIRouter, HTTPException
from ..database import SessionLocal
from ..models import Profile, WeightLog
from ..schemas import ProfileSchema, ProfileUpdate

router = APIRouter()
DEMO_USER_ID = 1


@router.get("", response_model=ProfileSchema)
def get_profile():
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profil nicht gefunden")
        return profile
    finally:
        db.close()


@router.put("", response_model=ProfileSchema)
def update_profile(data: ProfileUpdate):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profil nicht gefunden")

        incoming = data.model_dump(exclude_none=True)
        new_weight = incoming.get("weight_kg")
        old_weight = profile.weight_kg

        for field, value in incoming.items():
            setattr(profile, field, value)

        if new_weight is not None and new_weight != old_weight:
            db.add(WeightLog(user_id=DEMO_USER_ID, weight_kg=new_weight))

        db.commit()
        db.refresh(profile)
        return profile
    finally:
        db.close()
