from fastapi import APIRouter
from datetime import datetime, timedelta
from collections import defaultdict
from ..database import SessionLocal
from ..models import CardioLog, StrengthLog, WorkoutLog

router = APIRouter()
DEMO_USER_ID = 1


@router.get("/recent")
def get_recent_activities():
    """Letzte 10 Aktivitäten (Cardio + Strength gemischt, nach Datum sortiert)."""
    db = SessionLocal()
    try:
        cardio = db.query(CardioLog).filter_by(user_id=DEMO_USER_ID).order_by(CardioLog.logged_at.desc()).limit(20).all()
        strength = db.query(StrengthLog).filter_by(user_id=DEMO_USER_ID).order_by(StrengthLog.logged_at.desc()).limit(20).all()

        entries = []

        for c in cardio:
            parts = []
            if c.distance_km:
                parts.append(f"{c.distance_km} km")
            if c.duration_min:
                parts.append(f"{int(c.duration_min)} min")
            if c.pace_min_per_km and c.activity_type == "running":
                m = int(c.pace_min_per_km)
                s = int((c.pace_min_per_km - m) * 60)
                parts.append(f"{m}:{s:02d} min/km")
            elif c.speed_kmh and c.activity_type == "cycling":
                parts.append(f"{c.speed_kmh:.1f} km/h")
            label = "Lauf" if c.activity_type == "running" else "Radtour"
            if c.running_type:
                label = f"{c.running_type.capitalize()}-{label}"
            entries.append({
                "type": "cardio",
                "activity_type": c.activity_type,
                "date": c.logged_at.isoformat(),
                "summary": f"{label}: {' · '.join(parts)}" if parts else label,
                "distance_km": c.distance_km,
                "duration_min": c.duration_min,
                "pace_min_per_km": c.pace_min_per_km,
                "speed_kmh": c.speed_kmh,
                "running_type": c.running_type,
                "intensity": c.subjective_intensity,
            })

        # Strength-Einträge nach Session gruppieren (gleicher Tag = eine Session)
        sessions: dict = defaultdict(list)
        for s in strength:
            day_key = s.logged_at.date().isoformat()
            sessions[day_key].append(s)

        for day, items in sessions.items():
            exercises = list({i.exercise for i in items})
            summary = ", ".join(exercises[:3])
            if len(exercises) > 3:
                summary += f" +{len(exercises) - 3}"
            entries.append({
                "type": "strength",
                "activity_type": "strength",
                "date": items[0].logged_at.isoformat(),
                "summary": f"Krafttraining: {summary}",
                "exercises": [
                    {
                        "exercise": i.exercise,
                        "sets": i.sets,
                        "reps": i.reps,
                        "weight_kg": i.weight_kg,
                    }
                    for i in items
                ],
                "intensity": items[0].subjective_intensity,
            })

        entries.sort(key=lambda x: x["date"], reverse=True)
        return entries[:10]
    finally:
        db.close()


@router.get("/cardio/stats")
def get_cardio_stats():
    """Lauf- und Radstatistiken inkl. Pace-Trend der letzten 5 Läufe."""
    db = SessionLocal()
    try:
        all_runs = (
            db.query(CardioLog)
            .filter_by(user_id=DEMO_USER_ID, activity_type="running")
            .order_by(CardioLog.logged_at.desc())
            .all()
        )
        all_cycling = (
            db.query(CardioLog)
            .filter_by(user_id=DEMO_USER_ID, activity_type="cycling")
            .order_by(CardioLog.logged_at.desc())
            .all()
        )
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # Laufen
        run_km = [r.distance_km for r in all_runs if r.distance_km]
        run_paces = [r.pace_min_per_km for r in all_runs if r.pace_min_per_km]
        runs_last_7 = sum(1 for r in all_runs if r.logged_at >= seven_days_ago)

        pace_trend = [
            {
                "date": r.logged_at.date().isoformat(),
                "pace": round(r.pace_min_per_km, 2),
                "distance_km": r.distance_km,
                "running_type": r.running_type,
            }
            for r in all_runs[:5]
            if r.pace_min_per_km
        ]

        # Radfahren
        cycling_km = [c.distance_km for c in all_cycling if c.distance_km]
        cycling_speeds = [c.speed_kmh for c in all_cycling if c.speed_kmh]
        cycling_last_7 = sum(1 for c in all_cycling if c.logged_at >= seven_days_ago)

        return {
            "running": {
                "total_runs": len(all_runs),
                "total_km": round(sum(run_km), 1) if run_km else 0,
                "avg_pace": round(sum(run_paces) / len(run_paces), 2) if run_paces else None,
                "best_pace": round(min(run_paces), 2) if run_paces else None,
                "last_7_days": runs_last_7,
                "pace_trend": pace_trend,
            },
            "cycling": {
                "total_rides": len(all_cycling),
                "total_km": round(sum(cycling_km), 1) if cycling_km else 0,
                "avg_speed": round(sum(cycling_speeds) / len(cycling_speeds), 1) if cycling_speeds else None,
                "last_7_days": cycling_last_7,
            },
        }
    finally:
        db.close()


@router.get("/strength/stats")
def get_strength_stats():
    """Krafttraining-Statistiken: Sessions, meistgeloggte Übung, Gewichtsverlauf."""
    db = SessionLocal()
    try:
        all_entries = (
            db.query(StrengthLog)
            .filter_by(user_id=DEMO_USER_ID)
            .order_by(StrengthLog.logged_at.desc())
            .all()
        )
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # Eindeutige Sessions (nach Tag)
        session_days = {e.logged_at.date() for e in all_entries}
        sessions_last_7 = sum(1 for d in session_days if d >= seven_days_ago.date())

        # Übungen aggregieren
        exercise_map: dict = defaultdict(lambda: {"count": 0, "last_weight": None, "last_date": None})
        for e in all_entries:
            ex = exercise_map[e.exercise]
            ex["count"] += 1
            if ex["last_date"] is None or e.logged_at > ex["last_date"]:
                ex["last_date"] = e.logged_at
                ex["last_weight"] = e.weight_kg

        exercises = [
            {
                "exercise": name,
                "count": data["count"],
                "last_weight_kg": data["last_weight"],
                "last_date": data["last_date"].date().isoformat() if data["last_date"] else None,
            }
            for name, data in exercise_map.items()
        ]
        exercises.sort(key=lambda x: x["count"], reverse=True)

        most_logged = exercises[0]["exercise"] if exercises else None

        return {
            "total_sessions": len(session_days),
            "total_entries": len(all_entries),
            "most_logged_exercise": most_logged,
            "last_7_days": sessions_last_7,
            "exercises": exercises[:10],
        }
    finally:
        db.close()


@router.get("/overload-check")
def get_overload_check():
    """Überprüft ob der Nutzer in den letzten 7 Tagen zu viel trainiert hat."""
    db = SessionLocal()
    try:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        workout_days = {
            l.completed_at.date()
            for l in db.query(WorkoutLog).filter(
                WorkoutLog.user_id == DEMO_USER_ID,
                WorkoutLog.completed_at >= seven_days_ago,
            ).all()
        }
        cardio_days = {
            l.logged_at.date()
            for l in db.query(CardioLog).filter(
                CardioLog.user_id == DEMO_USER_ID,
                CardioLog.logged_at >= seven_days_ago,
            ).all()
        }
        strength_days = {
            l.logged_at.date()
            for l in db.query(StrengthLog).filter(
                StrengthLog.user_id == DEMO_USER_ID,
                StrengthLog.logged_at >= seven_days_ago,
            ).all()
        }

        all_days = workout_days | cardio_days | strength_days
        training_days = len(all_days)
        overloaded = training_days > 6

        if overloaded:
            message = f"Du hast diese Woche schon {training_days} Tage trainiert. Ein Ruhetag wäre jetzt sinnvoll."
        elif training_days >= 5:
            message = f"{training_days} Trainingstage diese Woche — du bist sehr aktiv. Achte auf genug Schlaf."
        else:
            message = f"{training_days} Trainingstage diese Woche."

        return {
            "overloaded": overloaded,
            "training_days_last_7": training_days,
            "message": message,
        }
    finally:
        db.close()
