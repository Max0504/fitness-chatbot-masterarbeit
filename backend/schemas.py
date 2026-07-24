from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Profil ────────────────────────────────────────────────────────────────────

class ProfileSchema(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    avatar: Optional[str] = "🏃"
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    days_per_week: Optional[int] = None
    equipment: List[str] = []
    injuries: Optional[str] = None
    specific_goal: Optional[str] = None
    target_value: Optional[float] = None
    target_unit: Optional[str] = None
    target_date: Optional[datetime] = None
    onboarded: bool = False

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    avatar: Optional[str] = None
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    days_per_week: Optional[int] = None
    equipment: Optional[List[str]] = None
    injuries: Optional[str] = None
    specific_goal: Optional[str] = None
    target_value: Optional[float] = None
    target_unit: Optional[str] = None
    target_date: Optional[datetime] = None


# ── Trainingsplan ─────────────────────────────────────────────────────────────

class ExerciseInPlan(BaseModel):
    exercise_id: Optional[str] = None   # optional — nicht nötig bei Gemini-generierten Plänen
    name: str
    sets: int
    reps: Optional[int] = None
    rest_sec: Optional[int] = None
    type: str = "strength"
    duration_min: Optional[int] = None
    description: Optional[str] = None   # Gemini-generierte Kurzbeschreibung / Hinweise


class PhaseInfo(BaseModel):
    phase_number: int
    name: str
    desc: str
    weeks: List[int]


class PlanWorkoutSchema(BaseModel):
    id: int
    week_number: int
    day_of_week: int
    name: str
    phase_number: int = 1
    phase_name: str = "Phase 1"
    exercises: List[ExerciseInPlan]

    class Config:
        from_attributes = True


class TrainingPlanSchema(BaseModel):
    id: int
    name: str
    goal: str
    duration_weeks: int
    created_at: datetime
    phases: List[PhaseInfo] = []
    workouts: List[PlanWorkoutSchema]
    explanation: Optional[str] = None

    class Config:
        from_attributes = True


class SwapExerciseRequest(BaseModel):
    exercise_id: str


class SwapExerciseResponse(BaseModel):
    ok: bool
    new_exercise: ExerciseInPlan


# ── Workout-Log ───────────────────────────────────────────────────────────────

class WorkoutLogCreate(BaseModel):
    plan_workout_id: Optional[int] = None
    duration_min: Optional[int] = None
    notes: Optional[str] = None
    perceived_effort: Optional[int] = None   # 1–10
    mood: Optional[int] = None               # 1–5


class WorkoutLogSchema(BaseModel):
    id: int
    completed_at: datetime
    duration_min: Optional[int] = None
    notes: Optional[str] = None
    plan_workout_id: Optional[int] = None
    perceived_effort: Optional[int] = None
    mood: Optional[int] = None

    class Config:
        from_attributes = True


# ── Fortschritts-Tracking ─────────────────────────────────────────────────────

class WeightLogCreate(BaseModel):
    weight_kg: float


class WeightLogSchema(BaseModel):
    id: int
    logged_at: datetime
    weight_kg: float

    class Config:
        from_attributes = True


class PerformanceLogCreate(BaseModel):
    metric_type: str     # z.B. "run_5km_seconds", "max_pushups", "squat_1rm_kg"
    value: float
    unit: str            # "seconds", "reps", "kg"
    notes: Optional[str] = None


class PerformanceLogSchema(BaseModel):
    id: int
    logged_at: datetime
    metric_type: str
    value: float
    unit: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ── Badges ────────────────────────────────────────────────────────────────────

class BadgeSchema(BaseModel):
    badge_key: str
    title: str
    desc: str
    icon: str
    earned_at: datetime
    seen: bool

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class LevelInfo(BaseModel):
    name: str
    icon: str
    total_points: int
    points_to_next: int
    next_level_name: Optional[str] = None


class DashboardData(BaseModel):
    level: LevelInfo
    streak_days: int
    total_workouts: int
    next_workout: Optional[dict] = None
    new_badges: List[BadgeSchema] = []   # ungesehene Badges → für Notification
    progress_summary: Optional[dict] = None  # zielabhängige Zusammenfassung


class NutritionTargets(BaseModel):
    calories: Optional[int] = None
    protein_g: Optional[int] = None
    carbs_g: Optional[int] = None
    fat_g: Optional[int] = None
    note: Optional[str] = None
