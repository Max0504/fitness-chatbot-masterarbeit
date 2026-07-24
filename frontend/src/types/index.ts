export type View = "chat" | "dashboard" | "plan" | "progress" | "nutrition" | "profile";

export interface NutritionMeal {
  meal_type: string;
  name: string;
  desc: string;
  approx_kcal: number;
}

export interface NutritionAdvice {
  goal_note: string;
  general_tips: string[];
  meals: NutritionMeal[];
  avoid: string[];
  key_nutrients: string[];
}

export interface Profile {
  name: string | null;
  age: number | null;
  gender: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  fitness_level: string | null;
  goal: string | null;
  days_per_week: number | null;
  equipment: string[];
  injuries: string | null;
  avatar: string | null;
  specific_goal: string | null;
  target_value: number | null;
  target_unit: string | null;
  target_date: string | null;
  onboarded: boolean;
}

export interface ExerciseInPlan {
  exercise_id: string | null;
  name: string;
  sets: number;
  reps: number | null;
  rest_sec: number | null;
  type: string;
  duration_min: number | null;
  description: string | null;
}

export interface PlanWorkout {
  id: number;
  week_number: number;
  day_of_week: number;
  name: string;
  phase_number: number;
  phase_name: string;
  exercises: ExerciseInPlan[];
}

export interface PhaseInfo {
  phase_number: number;
  name: string;
  desc: string;
  weeks: number[];
}

export interface TrainingPlan {
  id: number;
  name: string;
  goal: string;
  duration_weeks: number;
  created_at: string;
  phases: PhaseInfo[];
  workouts: PlanWorkout[];
  explanation?: string;
}

export interface LevelInfo {
  name: string;
  icon: string;
  total_points: number;
  points_to_next: number;
  next_level_name: string | null;
}

export interface Badge {
  badge_key: string;
  title: string;
  desc: string;
  icon: string;
  earned_at: string;
  seen: boolean;
}

export interface NextWorkout {
  id: number;
  name: string;
  exercises_count: number;
}

export interface DashboardData {
  level: LevelInfo;
  streak_days: number;
  total_workouts: number;
  next_workout: NextWorkout | null;
  new_badges: Badge[];
  progress_summary: Record<string, unknown> | null;
}

export interface WeightLog {
  id: number;
  logged_at: string;
  weight_kg: number;
}

export interface PerformanceLog {
  id: number;
  logged_at: string;
  metric_type: string;
  value: number;
  unit: string;
  notes: string | null;
}

export interface WorkoutLog {
  completed_at: string;
  duration_min: number | null;
  notes: string | null;
  plan_workout_id: number | null;
}
