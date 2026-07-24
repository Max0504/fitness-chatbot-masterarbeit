from fastapi import APIRouter, HTTPException
from ..database import SessionLocal
from ..models import Profile, TrainingPlan
from ..schemas import NutritionTargets
from ..nutrition_generator import get_nutrition_advice, refresh_meals, refresh_nutrients

router = APIRouter()
DEMO_USER_ID = 1


def _has_active_plan(db, user_id: int) -> bool:
    return db.query(TrainingPlan).filter_by(user_id=user_id, active=True).first() is not None


def _get_profile(db):
    profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
    has_plan = _has_active_plan(db, DEMO_USER_ID)
    if not profile or not has_plan:
        raise HTTPException(status_code=404, detail="Noch kein Trainingsplan vorhanden.")
    return {
        "goal": profile.goal,
        "specific_goal": profile.specific_goal,
        "weight_kg": profile.weight_kg,
        "injuries": profile.injuries,
    }


@router.get("/advice")
def get_advice():
    db = SessionLocal()
    try:
        profile_dict = _get_profile(db)
    finally:
        db.close()
    try:
        return get_nutrition_advice(profile_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meals/refresh")
def refresh_meals_endpoint():
    db = SessionLocal()
    try:
        profile_dict = _get_profile(db)
    finally:
        db.close()
    try:
        return refresh_meals(profile_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nutrients/refresh")
def refresh_nutrients_endpoint():
    db = SessionLocal()
    try:
        profile_dict = _get_profile(db)
    finally:
        db.close()
    try:
        return refresh_nutrients(profile_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/targets", response_model=NutritionTargets)
def get_nutrition_targets():
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
    finally:
        db.close()

    if not profile or not all([profile.weight_kg, profile.height_cm, profile.age, profile.gender]):
        return NutritionTargets(
            note="Bitte fülle Alter, Geschlecht, Größe und Gewicht im Profil aus, um Kalorienziele zu erhalten."
        )

    w = profile.weight_kg
    h = profile.height_cm
    a = profile.age
    # FIX 14.07.2026: Vorher `profile.gender == "m"`. Die Datenbank speichert aber "male"
    # (aus dem SetupModal), sodass der Vergleich IMMER fehlschlug und fuer alle Nutzer die
    # Mifflin-St-Jeor-Formel fuer Frauen (-161) statt fuer Maenner (+5) verwendet wurde.
    if (profile.gender or "").strip().lower() in ("m", "male", "mann", "männlich", "maennlich"):
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * a - 161

    days = profile.days_per_week or 3
    if days <= 3:
        factor = 1.4
    elif days == 4:
        factor = 1.55
    else:
        factor = 1.7

    tdee = bmr * factor
    goal = profile.goal or "general_fitness"
    if goal == "weight_loss":
        calories = round(tdee - 500)
    elif goal == "muscle_gain":
        calories = round(tdee + 300)
    else:
        calories = round(tdee)

    if goal == "muscle_gain":
        protein_g = round(w * 2.0)
        fat_g = round(calories * 0.25 / 9)
    elif goal == "weight_loss":
        protein_g = round(w * 1.8)
        fat_g = round(calories * 0.28 / 9)
    else:
        protein_g = round(w * 1.6)
        fat_g = round(calories * 0.30 / 9)

    carbs_g = round((calories - protein_g * 4 - fat_g * 9) / 4)

    return NutritionTargets(
        calories=calories,
        protein_g=protein_g,
        carbs_g=max(carbs_g, 0),
        fat_g=fat_g,
    )
