from fastapi import APIRouter
from datetime import datetime, timedelta
from ..database import SessionLocal
from ..models import WorkoutLog, PointsHistory, TrainingPlan, Badge, WeightLog, Profile
from ..gamification import get_level, check_badges, BADGES, POINTS

router = APIRouter()
DEMO_USER_ID = 1


@router.get("")
def get_dashboard():
    db = SessionLocal()
    try:
        # Punkte & Level
        total_points = sum(
            p.points for p in db.query(PointsHistory).filter_by(user_id=DEMO_USER_ID).all()
        ) or 0
        level_info = get_level(total_points)

        # Workout-Logs
        logs = (
            db.query(WorkoutLog)
            .filter_by(user_id=DEMO_USER_ID)
            .order_by(WorkoutLog.completed_at.desc())
            .all()
        )
        streak = _compute_streak(logs)
        total_workouts = len(logs)

        # Badges prüfen & neue vergeben
        existing_keys = {b.badge_key for b in db.query(Badge).filter_by(user_id=DEMO_USER_ID).all()}
        new_badge_keys = check_badges(total_workouts, streak, existing_keys)
        for key in new_badge_keys:
            db.add(Badge(user_id=DEMO_USER_ID, badge_key=key))
            db.add(PointsHistory(user_id=DEMO_USER_ID, points=POINTS["badge_earned"], reason="badge_earned"))
        if new_badge_keys:
            db.commit()

        # Ungesehene Badges für Notification
        unseen = db.query(Badge).filter_by(user_id=DEMO_USER_ID, seen=False).all()
        new_badges = []
        for b in unseen:
            meta = BADGES.get(b.badge_key, {"title": b.badge_key, "desc": "", "icon": "🏅"})
            new_badges.append({
                "badge_key": b.badge_key,
                "title": meta["title"],
                "desc": meta["desc"],
                "icon": meta["icon"],
                "earned_at": b.earned_at.isoformat(),
                "seen": b.seen,
            })

        # Nächstes Workout
        plan = db.query(TrainingPlan).filter_by(user_id=DEMO_USER_ID, active=True).first()
        next_workout = None
        if plan and plan.workouts:
            workouts = sorted(plan.workouts, key=lambda w: (w.week_number, w.day_of_week))
            logged_count = sum(1 for log in logs if log.plan_workout_id is not None)
            idx = logged_count % len(workouts)
            next_workout = {
                "id": workouts[idx].id,
                "name": workouts[idx].name,
                "exercises_count": len(workouts[idx].exercises or []),
            }

        # Fortschritts-Snapshot für Dashboard (zielabhängig)
        progress_summary = _get_progress_summary(db)

        return {
            "level": {
                "name": level_info["name"],
                "icon": level_info["icon"],
                "total_points": total_points,
                "points_to_next": level_info["points_to_next"],
                "next_level_name": level_info["next_level_name"],
            },
            "streak_days": streak,
            "total_workouts": total_workouts,
            "next_workout": next_workout,
            "new_badges": new_badges,
            "progress_summary": progress_summary,
        }
    finally:
        db.close()


def _get_progress_summary(db) -> dict | None:
    profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
    if not profile or not profile.goal:
        return None

    if profile.goal in ("weight_loss", "muscle_gain"):
        logs = (
            db.query(WeightLog)
            .filter_by(user_id=DEMO_USER_ID)
            .order_by(WeightLog.logged_at.desc())
            .limit(2)
            .all()
        )
        if not logs:
            return {"type": "weight", "message": "Noch kein Gewicht eingetragen"}
        current = logs[0].weight_kg
        change = round(current - logs[1].weight_kg, 1) if len(logs) > 1 else 0
        arrow = "↓" if change < 0 else ("↑" if change > 0 else "→")
        return {
            "type": "weight",
            "current_kg": current,
            "target_kg": profile.target_value,
            "last_change": change,
            "arrow": arrow,
        }

    return None


def _compute_streak(logs: list) -> int:
    if not logs:
        return 0
    days = sorted({log.completed_at.date() for log in logs}, reverse=True)
    today = datetime.utcnow().date()
    if (today - days[0]).days > 1:
        return 0
    streak = 1
    for i in range(1, len(days)):
        if (days[i - 1] - days[i]).days == 1:
            streak += 1
        else:
            break
    return streak
