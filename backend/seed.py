import json
from pathlib import Path
from sqlalchemy import text
from .database import SessionLocal, engine
from .models import Base, User, Profile


EXERCISES_PATH = Path(__file__).parent.parent / "data" / "exercises.json"

# Idempotente Migrationen — Reihenfolge beibehalten, neue ans Ende
_MIGRATIONS = [
    # Phase A–C (bestehend)
    "ALTER TABLE profiles ADD COLUMN name VARCHAR",
    "ALTER TABLE profiles ADD COLUMN avatar VARCHAR DEFAULT '🏃'",
    "ALTER TABLE training_plans ADD COLUMN phases JSON DEFAULT '[]'",
    "ALTER TABLE plan_workouts ADD COLUMN phase_number INTEGER DEFAULT 1",
    "ALTER TABLE plan_workouts ADD COLUMN phase_name VARCHAR DEFAULT 'Phase 1'",

    # Phase 1 — Profil-Erweiterungen
    "ALTER TABLE profiles ADD COLUMN specific_goal TEXT",
    "ALTER TABLE profiles ADD COLUMN target_value REAL",
    "ALTER TABLE profiles ADD COLUMN target_unit VARCHAR",
    "ALTER TABLE profiles ADD COLUMN target_date DATETIME",

    # Phase 1 — WorkoutLog-Erweiterungen
    "ALTER TABLE workout_logs ADD COLUMN perceived_effort INTEGER",
    "ALTER TABLE workout_logs ADD COLUMN mood INTEGER",

    # Phase 1 — Neue Tabellen
    """CREATE TABLE IF NOT EXISTS weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        weight_kg REAL NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS performance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        metric_type VARCHAR NOT NULL,
        value REAL NOT NULL,
        unit VARCHAR NOT NULL,
        notes TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        badge_key VARCHAR NOT NULL,
        earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        seen INTEGER DEFAULT 0
    )""",
]


def _run_migrations():
    with engine.connect() as conn:
        for sql in _MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Spalte / Tabelle existiert bereits


def seed_if_empty():
    _run_migrations()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=1).first()
        if not user:
            user = User(id=1, username="demo_user")
            db.add(user)
            db.flush()
            print("Seed: Demo-User angelegt (id=1).")
        else:
            print("Seed: Demo-User bereits vorhanden, überspringe.")

        profile = db.query(Profile).filter_by(user_id=1).first()
        if not profile:
            db.add(Profile(user_id=1, equipment=[]))
            print("Seed: Demo-Profil angelegt.")

        db.commit()
    finally:
        db.close()
