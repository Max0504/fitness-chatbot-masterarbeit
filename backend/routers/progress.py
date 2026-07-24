from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..database import SessionLocal
from ..models import WeightLog, PerformanceLog, Badge, PointsHistory, WorkoutLog, Profile
from ..schemas import WeightLogCreate, WeightLogSchema, PerformanceLogCreate, PerformanceLogSchema, BadgeSchema
from ..gamification import BADGES, get_level, check_badges, POINTS

router = APIRouter()
DEMO_USER_ID = 1


# ── Gewicht ───────────────────────────────────────────────────────────────────

@router.post("/weight", response_model=WeightLogSchema)
def log_weight(body: WeightLogCreate):
    db = SessionLocal()
    try:
        entry = WeightLog(user_id=DEMO_USER_ID, weight_kg=body.weight_kg)
        db.add(entry)
        # Aktuelles Profilgewicht ebenfalls aktualisieren
        profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
        if profile:
            profile.weight_kg = body.weight_kg
        db.commit()
        db.refresh(entry)
        return entry
    finally:
        db.close()


@router.get("/weight", response_model=list[WeightLogSchema])
def get_weight_history(limit: int = 90):
    db = SessionLocal()
    try:
        return (
            db.query(WeightLog)
            .filter_by(user_id=DEMO_USER_ID)
            .order_by(WeightLog.logged_at.asc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


# ── Leistung ──────────────────────────────────────────────────────────────────

@router.post("/performance", response_model=PerformanceLogSchema)
def log_performance(body: PerformanceLogCreate):
    db = SessionLocal()
    try:
        # Prüfen ob das eine persönliche Bestleistung ist
        existing = (
            db.query(PerformanceLog)
            .filter_by(user_id=DEMO_USER_ID, metric_type=body.metric_type)
            .order_by(PerformanceLog.logged_at.desc())
            .all()
        )
        entry = PerformanceLog(
            user_id=DEMO_USER_ID,
            metric_type=body.metric_type,
            value=body.value,
            unit=body.unit,
            notes=body.notes,
        )
        db.add(entry)

        # Persönliche Bestleistung Badge prüfen
        existing_badge_keys = {
            b.badge_key for b in db.query(Badge).filter_by(user_id=DEMO_USER_ID).all()
        }
        is_pb = _is_personal_best(body.metric_type, body.value, existing)
        if is_pb and "pb_set" not in existing_badge_keys:
            db.add(Badge(user_id=DEMO_USER_ID, badge_key="pb_set"))
            db.add(PointsHistory(user_id=DEMO_USER_ID, points=POINTS["badge_earned"], reason="badge_earned"))

        db.commit()
        db.refresh(entry)
        return entry
    finally:
        db.close()


@router.delete("/performance/{metric_type}")
def delete_performance_metric(metric_type: str):
    db = SessionLocal()
    try:
        deleted = db.query(PerformanceLog).filter_by(user_id=DEMO_USER_ID, metric_type=metric_type).delete()
        db.commit()
        return {"ok": True, "deleted": deleted}
    finally:
        db.close()


@router.get("/performance/{metric_type}", response_model=list[PerformanceLogSchema])
def get_performance_history(metric_type: str, limit: int = 50):
    db = SessionLocal()
    try:
        return (
            db.query(PerformanceLog)
            .filter_by(user_id=DEMO_USER_ID, metric_type=metric_type)
            .order_by(PerformanceLog.logged_at.asc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


@router.get("/performance", response_model=list[dict])
def get_all_performance_metrics():
    """Gibt alle verfügbaren Metriken zurück (für Diagramm-Auswahl im Frontend)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(PerformanceLog.metric_type, PerformanceLog.unit)
            .filter_by(user_id=DEMO_USER_ID)
            .distinct()
            .all()
        )
        return [{"metric_type": r[0], "unit": r[1]} for r in rows]
    finally:
        db.close()


# ── Badges ────────────────────────────────────────────────────────────────────

@router.get("/badges", response_model=list[BadgeSchema])
def get_badges():
    db = SessionLocal()
    try:
        earned = db.query(Badge).filter_by(user_id=DEMO_USER_ID).order_by(Badge.earned_at.asc()).all()
        result = []
        for b in earned:
            meta = BADGES.get(b.badge_key, {"title": b.badge_key, "desc": "", "icon": "🏅"})
            result.append(BadgeSchema(
                badge_key=b.badge_key,
                title=meta["title"],
                desc=meta["desc"],
                icon=meta["icon"],
                earned_at=b.earned_at,
                seen=b.seen,
            ))
        return result
    finally:
        db.close()


@router.get("/badges/all")
def get_all_badges():
    """Gibt alle möglichen Badges zurück — verdiente farbig, nicht verdiente als locked."""
    db = SessionLocal()
    try:
        earned_map = {
            b.badge_key: b.earned_at.isoformat()
            for b in db.query(Badge).filter_by(user_id=DEMO_USER_ID).all()
        }
        return [
            {
                "badge_key": key,
                "title": meta["title"],
                "desc": meta["desc"],
                "icon": meta["icon"],
                "earned": key in earned_map,
                "earned_at": earned_map.get(key),
            }
            for key, meta in BADGES.items()
        ]
    finally:
        db.close()


@router.post("/badges/{badge_key}/seen")
def mark_badge_seen(badge_key: str):
    db = SessionLocal()
    try:
        badge = db.query(Badge).filter_by(user_id=DEMO_USER_ID, badge_key=badge_key).first()
        if not badge:
            raise HTTPException(status_code=404, detail="Badge nicht gefunden")
        badge.seen = True
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ── Zielfortschritt ───────────────────────────────────────────────────────────

@router.get("/goal-progress")
def get_goal_progress():
    """Berechnet den Fortschritt zum aktuellen Ziel des Nutzers."""
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
        if not profile or not profile.goal:
            return {"available": False}

        goal = profile.goal
        result = {"goal": goal, "available": True}

        if goal in ("weight_loss", "muscle_gain") and profile.target_value:
            logs = (
                db.query(WeightLog)
                .filter_by(user_id=DEMO_USER_ID)
                .order_by(WeightLog.logged_at.asc())
                .all()
            )
            if logs:
                start_weight = logs[0].weight_kg
                current_weight = logs[-1].weight_kg
                target = profile.target_value
                total_change_needed = abs(target - start_weight)
                change_so_far = abs(current_weight - start_weight)
                progress_pct = min(100, round(change_so_far / total_change_needed * 100) if total_change_needed > 0 else 0)
                result.update({
                    "type": "weight",
                    "start": start_weight,
                    "current": current_weight,
                    "target": target,
                    "unit": "kg",
                    "progress_pct": progress_pct,
                    "data_points": [{"date": l.logged_at.date().isoformat(), "value": l.weight_kg} for l in logs],
                })

        elif goal == "endurance" and profile.target_value:
            metric = f"run_{int(profile.target_value)}m_seconds" if profile.target_unit == "m" else "run_5km_seconds"
            logs = (
                db.query(PerformanceLog)
                .filter_by(user_id=DEMO_USER_ID, metric_type=metric)
                .order_by(PerformanceLog.logged_at.asc())
                .all()
            )
            if logs:
                start_time = logs[0].value
                current_time = logs[-1].value
                target_time = profile.target_value
                improvement = start_time - current_time
                needed = start_time - target_time
                progress_pct = min(100, round(improvement / needed * 100) if needed > 0 else 0)
                result.update({
                    "type": "time",
                    "start": start_time,
                    "current": current_time,
                    "target": target_time,
                    "unit": "seconds",
                    "progress_pct": progress_pct,
                    "data_points": [{"date": l.logged_at.date().isoformat(), "value": l.value} for l in logs],
                })

        elif goal == "strength":
            # Stärkstes 1RM über alle Kraft-Metriken
            logs = (
                db.query(PerformanceLog)
                .filter_by(user_id=DEMO_USER_ID)
                .filter(PerformanceLog.metric_type.like("%_1rm_%"))
                .order_by(PerformanceLog.logged_at.asc())
                .all()
            )
            if logs:
                result.update({
                    "type": "strength",
                    "unit": "kg",
                    "data_points": [{"date": l.logged_at.date().isoformat(), "value": l.value, "metric": l.metric_type} for l in logs[-20:]],
                })

        return result
    finally:
        db.close()


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _is_personal_best(metric_type: str, new_value: float, existing: list) -> bool:
    if not existing:
        return True
    best = min(e.value for e in existing) if "seconds" in metric_type else max(e.value for e in existing)
    return new_value < best if "seconds" in metric_type else new_value > best
