from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, JSON, Text
)
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, default="demo_user")
    created_at = Column(DateTime, default=datetime.utcnow)
    profile = relationship("Profile", uselist=False, back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)          # "male", "female", "diverse"
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    avatar = Column(String, nullable=True, default="🏃")

    # Training
    fitness_level = Column(String, nullable=True)   # "beginner", "intermediate", "advanced"
    goal = Column(String, nullable=True)            # "weight_loss", "muscle_gain", "general_fitness", "endurance", "strength"
    days_per_week = Column(Integer, nullable=True)
    equipment = Column(JSON, default=list)          # ["bodyweight", "dumbbells", "barbell", "gym"]
    injuries = Column(Text, nullable=True)

    # Spezifisches Ziel
    specific_goal = Column(Text, nullable=True)     # Freitext, z.B. "In 3 Monaten 70 kg"
    target_value = Column(Float, nullable=True)     # numerischer Zielwert (kg, Sekunden, Wiederholungen)
    target_unit = Column(String, nullable=True)     # "kg", "seconds", "reps", "km"
    target_date = Column(DateTime, nullable=True)   # Wunsch-Zieldatum

    onboarded = Column(Boolean, default=False)
    wellbeing_last_checked = Column(Date, nullable=True)
    plan_feedback_requested_at = Column(Date, nullable=True)
    user = relationship("User", back_populates="profile")


class TrainingPlan(Base):
    __tablename__ = "training_plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    goal = Column(String)
    duration_weeks = Column(Integer, default=4)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    phases = Column(JSON, default=list)   # [{"phase_number":1,"name":"...","desc":"...","weeks":[1,2]}]
    explanation = Column(Text, nullable=True)
    workouts = relationship("PlanWorkout", back_populates="plan", cascade="all, delete")


class PlanWorkout(Base):
    __tablename__ = "plan_workouts"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("training_plans.id"))
    week_number = Column(Integer, default=1)
    day_of_week = Column(Integer)
    name = Column(String)
    phase_number = Column(Integer, default=1)
    phase_name = Column(String, default="Phase 1")
    exercises = Column(JSON)        # [{"exercise_id": "squat", "sets": 3, "reps": 12, ...}]
    plan = relationship("TrainingPlan", back_populates="workouts")


class WorkoutLog(Base):
    __tablename__ = "workout_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_workout_id = Column(Integer, ForeignKey("plan_workouts.id"), nullable=True)
    completed_at = Column(DateTime, default=datetime.utcnow)
    duration_min = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    perceived_effort = Column(Integer, nullable=True)   # 1–10 (RPE), für Studie interessant
    mood = Column(Integer, nullable=True)               # 1–5 (Stimmung vor/nach Training)


class PointsHistory(Base):
    __tablename__ = "points_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    points = Column(Integer)
    reason = Column(String)   # "workout_completed", "streak_bonus", "badge_earned", "onboarding"
    created_at = Column(DateTime, default=datetime.utcnow)


class WeightLog(Base):
    """Gewichtsverlauf — wird nach dem Login abgefragt (bei Zielen wo Gewicht relevant ist)."""
    __tablename__ = "weight_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    logged_at = Column(DateTime, default=datetime.utcnow)
    weight_kg = Column(Float, nullable=False)


class PerformanceLog(Base):
    """Allgemeiner Leistungsfortschritt — Laufzeiten, Max-Wiederholungen, 1RM, etc."""
    __tablename__ = "performance_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    logged_at = Column(DateTime, default=datetime.utcnow)
    metric_type = Column(String, nullable=False)   # "run_5km_seconds", "max_pushups", "squat_1rm_kg"
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)          # "seconds", "reps", "kg", "km"
    notes = Column(Text, nullable=True)


class CardioLog(Base):
    __tablename__ = "cardio_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    logged_at = Column(DateTime, default=datetime.utcnow)
    activity_type = Column(String, nullable=False)          # "running" | "cycling"
    distance_km = Column(Float, nullable=True)
    duration_min = Column(Float, nullable=True)
    pace_min_per_km = Column(Float, nullable=True)          # berechnet
    speed_kmh = Column(Float, nullable=True)                # berechnet
    running_type = Column(String, nullable=True)            # "locker" | "intervall" | "tempo" | "lang" | "fartlek"
    subjective_intensity = Column(String, nullable=True)    # "leicht" | "mittel" | "schwer"
    notes = Column(Text, nullable=True)


class StrengthLog(Base):
    __tablename__ = "strength_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    logged_at = Column(DateTime, default=datetime.utcnow)
    exercise = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=True)
    reps = Column(Integer, nullable=True)
    sets = Column(Integer, nullable=True)
    subjective_intensity = Column(String, nullable=True)    # "leicht" | "mittel" | "schwer"
    notes = Column(Text, nullable=True)


class Badge(Base):
    """Verdiente Abzeichen."""
    __tablename__ = "badges"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_key = Column(String, nullable=False)     # z.B. "first_workout", "streak_7"
    earned_at = Column(DateTime, default=datetime.utcnow)
    seen = Column(Boolean, default=False)          # False = noch nicht gesehen → Notification anzeigen
