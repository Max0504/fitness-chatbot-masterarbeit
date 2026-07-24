from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..database import SessionLocal
from ..models import WorkoutLog, PointsHistory, Badge, TrainingPlan, PlanWorkout
from ..schemas import WorkoutLogCreate, WorkoutLogSchema
from ..gamification import check_badges, BADGES, POINTS, get_level
from .dashboard import _compute_streak

router = APIRouter()
DEMO_USER_ID = 1


@router.post("/log")
def log_workout(data: WorkoutLogCreate):
    db = SessionLocal()
    try:
        if data.plan_workout_id is not None:
            already = db.query(WorkoutLog).filter_by(
                user_id=DEMO_USER_ID, plan_workout_id=data.plan_workout_id
            ).first()
            if already:
                raise HTTPException(status_code=409, detail="Workout bereits abgeschlossen")

        # Level vor dem Logging merken
        points_before = sum(
            p.points for p in db.query(PointsHistory).filter_by(user_id=DEMO_USER_ID).all()
        )
        level_before = get_level(points_before)["name"]

        log = WorkoutLog(
            user_id=DEMO_USER_ID,
            plan_workout_id=data.plan_workout_id,
            duration_min=data.duration_min,
            notes=data.notes,
            completed_at=datetime.utcnow(),
        )
        db.add(log)
        db.add(PointsHistory(user_id=DEMO_USER_ID, points=20, reason="workout_completed"))

        # Streak-Bonus prüfen
        existing_logs = (
            db.query(WorkoutLog)
            .filter_by(user_id=DEMO_USER_ID)
            .order_by(WorkoutLog.completed_at.desc())
            .all()
        )
        streak = _compute_streak(existing_logs)
        streak_bonus = 0
        if streak >= 1:
            db.add(PointsHistory(user_id=DEMO_USER_ID, points=10, reason="streak_bonus"))
            streak_bonus = 10

        # Badge-Check
        total_workouts = len(existing_logs) + 1
        existing_keys = {b.badge_key for b in db.query(Badge).filter_by(user_id=DEMO_USER_ID).all()}
        new_badge_keys = check_badges(total_workouts, streak, existing_keys)

        # Plan-Completion prüfen
        if data.plan_workout_id and "plan_completed" not in existing_keys:
            active_plan = db.query(TrainingPlan).filter_by(user_id=DEMO_USER_ID, active=True).first()
            if active_plan:
                plan_workout_ids = {
                    pw.id for pw in db.query(PlanWorkout).filter_by(plan_id=active_plan.id).all()
                }
                already_logged_ids = {
                    wl.plan_workout_id for wl in db.query(WorkoutLog)
                    .filter(WorkoutLog.user_id == DEMO_USER_ID,
                            WorkoutLog.plan_workout_id.in_(plan_workout_ids))
                    .all()
                }
                # +1: aktuelles Workout noch nicht committed
                newly_logged = already_logged_ids | {data.plan_workout_id}
                if plan_workout_ids and newly_logged >= plan_workout_ids:
                    new_badge_keys.append("plan_completed")

        for key in new_badge_keys:
            db.add(Badge(user_id=DEMO_USER_ID, badge_key=key))
            db.add(PointsHistory(user_id=DEMO_USER_ID, points=POINTS["badge_earned"], reason="badge_earned"))

        db.commit()

        # Level nach dem Logging prüfen
        points_after = points_before + 20 + streak_bonus + len(new_badge_keys) * POINTS["badge_earned"]
        new_level_info = get_level(points_after)
        level_up = new_level_info["name"] if new_level_info["name"] != level_before else None

        new_badges = [
            {"key": k, "title": BADGES[k]["title"], "desc": BADGES[k]["desc"], "icon": BADGES[k]["icon"]}
            for k in new_badge_keys if k in BADGES
        ]
        return {
            "ok": True,
            "points_awarded": 20 + streak_bonus,
            "new_badges": new_badges,
            "level_up": level_up,
            "new_level_icon": new_level_info["icon"] if level_up else None,
        }
    finally:
        db.close()


@router.get("/history", response_model=list[WorkoutLogSchema])
def get_workout_history():
    db = SessionLocal()
    try:
        logs = (
            db.query(WorkoutLog)
            .filter_by(user_id=DEMO_USER_ID)
            .order_by(WorkoutLog.completed_at.desc())
            .limit(30)
            .all()
        )
        return logs
    finally:
        db.close()
