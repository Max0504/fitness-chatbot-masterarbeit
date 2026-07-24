import json
import random
from pathlib import Path
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import joinedload
from ..database import SessionLocal
from ..models import TrainingPlan, PlanWorkout, Profile
from ..schemas import TrainingPlanSchema, SwapExerciseRequest, SwapExerciseResponse, ExerciseInPlan

router = APIRouter()
DEMO_USER_ID = 1
EXERCISES_PATH = Path(__file__).parent.parent.parent / "data" / "exercises.json"
_STATUS_FILE = Path(__file__).parent.parent.parent / "data" / "plan_status.json"


def _load_exercises():
    with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _filter_pool(exercises, equipment, difficulty, injury_tags):
    diff_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    max_diff = diff_order.get(difficulty, 0)
    eq_set = set(equipment) if equipment else {"bodyweight"}
    if "gym" in eq_set:
        eq_set.update({"bodyweight", "dumbbells", "barbell", "cardio", "kettlebell"})
    if "bicycle" in eq_set:
        eq_set.add("cardio")
    result = []
    for ex in exercises:
        if diff_order.get(ex.get("difficulty", "beginner"), 0) > max_diff:
            continue
        if not (set(ex.get("equipment", [])) & eq_set):
            continue
        if injury_tags and (set(ex.get("injuries_avoid", [])) & injury_tags):
            continue
        result.append(ex)
    return result


def _parse_injuries(text: str):
    if not text:
        return set()
    keywords = {
        "knie": "knee", "knieschmerzen": "knee",
        "rücken": "back", "bandscheibe": "back",
        "schulter": "shoulder", "handgelenk": "wrist",
        "knöchel": "ankle", "hüfte": "hip", "nacken": "neck",
        "ellenbogen": "elbow",
    }
    lower = text.lower()
    return {tag for kw, tag in keywords.items() if kw in lower}


@router.get("/status")
def get_plan_status():
    try:
        return json.loads(_STATUS_FILE.read_text())
    except Exception:
        return {"status": "idle", "error": "", "ts": 0}


@router.get("/active", response_model=TrainingPlanSchema)
def get_active_plan():
    db = SessionLocal()
    try:
        plan = (
            db.query(TrainingPlan)
            .options(joinedload(TrainingPlan.workouts))
            .filter_by(user_id=DEMO_USER_ID, active=True)
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Kein aktiver Trainingsplan gefunden")
        return TrainingPlanSchema.from_orm(plan)
    finally:
        db.close()


@router.post("/swap-exercise/{workout_id}", response_model=SwapExerciseResponse)
def swap_exercise(workout_id: int, body: SwapExerciseRequest):
    """Replaces one exercise in all workouts of the plan that share the same name."""
    db = SessionLocal()
    try:
        workout = db.query(PlanWorkout).filter_by(id=workout_id).first()
        if not workout:
            raise HTTPException(status_code=404, detail="Workout nicht gefunden")

        profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
        equipment = (profile.equipment or ["bodyweight"]) if profile else ["bodyweight"]
        difficulty = (profile.fitness_level or "beginner") if profile else "beginner"
        injury_tags = _parse_injuries(profile.injuries if profile else "")

        all_exercises = _load_exercises()
        pool = _filter_pool(all_exercises, equipment, difficulty, injury_tags)

        # Find the exercise being replaced
        original = next((ex for ex in all_exercises if ex["id"] == body.exercise_id), None)
        if not original:
            raise HTTPException(status_code=404, detail="Übung nicht gefunden")

        target_muscles = set(original.get("muscle_groups", []))
        target_type = original.get("type", "strength")

        # Find replacement: same type + overlapping muscles, exclude original and current workout exercises
        current_ids = {e["exercise_id"] for e in (workout.exercises or [])}
        candidates = [
            ex for ex in pool
            if ex["id"] not in current_ids
            and ex.get("type", "strength") == target_type
            and bool(set(ex.get("muscle_groups", [])) & target_muscles)
        ]
        if not candidates:
            candidates = [
                ex for ex in pool
                if ex["id"] not in current_ids
                and ex.get("type", "strength") == target_type
            ]
        if not candidates:
            raise HTTPException(status_code=409, detail="Keine passende Ersatzübung gefunden")

        replacement = random.choice(candidates)

        # Find the params from the original exercise slot
        orig_slot = next((e for e in (workout.exercises or []) if e["exercise_id"] == body.exercise_id), None)
        sets = orig_slot["sets"] if orig_slot else 3
        reps = orig_slot.get("reps") if orig_slot else 12
        rest_sec = orig_slot.get("rest_sec") if orig_slot else 60

        new_ex = {
            "exercise_id": replacement["id"],
            "name": replacement["name"],
            "sets": sets,
            "reps": reps,
            "rest_sec": rest_sec,
            "type": replacement.get("type", "strength"),
            "duration_min": replacement.get("duration_min"),
        }

        # Update ALL workouts in the same plan that contain this exercise (plan-wide swap)
        plan_workouts = db.query(PlanWorkout).filter_by(plan_id=workout.plan_id).all()
        for pw in plan_workouts:
            updated = False
            new_list = []
            for e in (pw.exercises or []):
                if e["exercise_id"] == body.exercise_id:
                    new_list.append(new_ex)
                    updated = True
                else:
                    new_list.append(e)
            if updated:
                pw.exercises = new_list

        db.commit()

        return SwapExerciseResponse(
            ok=True,
            new_exercise=ExerciseInPlan(**new_ex),
        )
    finally:
        db.close()
