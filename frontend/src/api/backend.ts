import type {
  Profile, TrainingPlan, DashboardData, WorkoutLog, ExerciseInPlan,
  WeightLog, PerformanceLog, Badge, NutritionAdvice,
} from "../types";

export interface AllBadge {
  badge_key: string;
  title: string;
  desc: string;
  icon: string;
  earned: boolean;
  earned_at: string | null;
}

export interface ActivityEntry {
  type: "cardio" | "strength";
  activity_type: string;
  date: string;
  summary: string;
  distance_km?: number;
  duration_min?: number;
  pace_min_per_km?: number;
  speed_kmh?: number;
  running_type?: string;
  intensity?: number;
  exercises?: { exercise: string; sets: number; reps: number; weight_kg: number }[];
}

export interface CardioStats {
  running: {
    total_runs: number;
    total_km: number;
    avg_pace: number | null;
    best_pace: number | null;
    last_7_days: number;
    pace_trend: { date: string; pace: number; distance_km: number; running_type: string | null }[];
  };
  cycling: {
    total_rides: number;
    total_km: number;
    avg_speed: number | null;
    last_7_days: number;
  };
}

export interface StrengthStats {
  total_sessions: number;
  total_entries: number;
  most_logged_exercise: string | null;
  last_7_days: number;
  exercises: { exercise: string; count: number; last_weight_kg: number | null; last_date: string | null }[];
}

const API_BASE = "http://localhost:8000/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json();
}

async function putJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  // Profile
  getProfile: () => get<Profile>("/profile"),
  updateProfile: (data: Partial<Profile>) => putJson<Profile>("/profile", data),

  // Plan
  getActivePlan: () => get<TrainingPlan>("/plan/active"),
  getPlanStatus: () => get<{ status: string; error: string; ts: number }>("/plan/status"),
swapExercise: (workoutId: number, exerciseId: string) =>
    postJson<{ ok: boolean; new_exercise: ExerciseInPlan }>(
      `/plan/swap-exercise/${workoutId}`,
      { exercise_id: exerciseId }
    ),

  // Dashboard
  getDashboard: () => get<DashboardData>("/dashboard"),

  // Workouts
  logWorkout: (data: { plan_workout_id?: number; duration_min?: number; notes?: string; perceived_effort?: number; mood?: number }) =>
    postJson<{
      ok: boolean;
      points_awarded: number;
      new_badges: { key: string; title: string; desc: string; icon: string }[];
      level_up: string | null;
      new_level_icon: string | null;
    }>("/workouts/log", data),
  getWorkoutHistory: () => get<WorkoutLog[]>("/workouts/history"),

  // Progress – Gewicht
  logWeight: (weight_kg: number) =>
    postJson<WeightLog>("/progress/weight", { weight_kg }),
  getWeightHistory: (limit = 90) =>
    get<WeightLog[]>(`/progress/weight?limit=${limit}`),

  // Progress – Leistung
  logPerformance: (data: { metric_type: string; value: number; unit: string; notes?: string }) =>
    postJson<PerformanceLog>("/progress/performance", data),
  getPerformanceHistory: (metric_type: string, limit = 50) =>
    get<PerformanceLog[]>(`/progress/performance/${metric_type}?limit=${limit}`),
  getAllPerformanceMetrics: () =>
    get<{ metric_type: string; unit: string }[]>("/progress/performance"),
  deletePerformanceMetric: (metric_type: string) =>
    fetch(`${API_BASE}/progress/performance/${encodeURIComponent(metric_type)}`, {
      method: "DELETE",
    }).then((r) => { if (!r.ok) throw new Error(); return r.json(); }),

  // Badges
  getBadges: () => get<Badge[]>("/progress/badges"),
  getAllBadges: () => get<AllBadge[]>("/progress/badges/all"),
  markBadgeSeen: (badge_key: string) =>
    postJson<{ ok: boolean }>(`/progress/badges/${badge_key}/seen`, {}),

  // Zielfortschritt
  getGoalProgress: () => get<Record<string, unknown>>("/progress/goal-progress"),

  // Aktivität
  getRecentActivities: () => get<ActivityEntry[]>("/activity/recent"),
  getCardioStats: () => get<CardioStats>("/activity/cardio/stats"),
  getStrengthStats: () => get<StrengthStats>("/activity/strength/stats"),

  // Ernährung
  getNutritionAdvice: () => get<NutritionAdvice>("/nutrition/advice"),
  refreshNutritionMeals: () =>
    fetch(`${API_BASE}/nutrition/meals/refresh`, { method: "POST" })
      .then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<NutritionAdvice>; }),
  refreshNutritionNutrients: () =>
    fetch(`${API_BASE}/nutrition/nutrients/refresh`, { method: "POST" })
      .then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<NutritionAdvice>; }),
  getNutritionTargets: () => get<{ calories?: number; protein_g?: number; carbs_g?: number; fat_g?: number; note?: string }>("/nutrition/targets"),
};
