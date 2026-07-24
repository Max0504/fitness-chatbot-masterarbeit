import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../../api/backend";
import type { TrainingPlan, PlanWorkout } from "../../types";
import WorkoutCard from "./WorkoutCard";

const GOAL_LABELS: Record<string, string> = {
  muscle_gain: "Muskelaufbau",
  weight_loss: "Gewichtsabnahme",
  general_fitness: "Allgemeine Fitness",
  endurance: "Ausdauer",
};

interface Props {
  onWorkoutLogged: (message: string) => void;
}

export default function PlanView({ onWorkoutLogged }: Props) {
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [completedIds, setCompletedIds] = useState<Set<number>>(new Set());
  const [genStatus, setGenStatus] = useState<"idle" | "generating" | "ready" | "error">("idle");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback((resetWeek = false) => {
    api.getActivePlan()
      .then((p) => {
        setPlan(p);
        setNotFound(false);
        if (resetWeek) {
          const created = new Date(p.created_at);
          const now = new Date();
          const daysPassed = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
          const currentWeek = Math.min(Math.floor(daysPassed / 7) + 1, p.duration_weeks);
          setSelectedWeek(currentWeek);
        }
      })
      .catch(() => setNotFound(true));
    api.getWorkoutHistory()
      .then((logs) => {
        const ids = new Set(logs.map((l) => l.plan_workout_id).filter((id): id is number => id !== null && id !== undefined));
        setCompletedIds(ids);
      })
      .catch(() => {});
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(() => {
      api.getPlanStatus()
        .then((s) => {
          setGenStatus(s.status as "idle" | "generating" | "ready" | "error");
          if (s.status === "ready") {
            stopPolling();
            load();
          } else if (s.status === "error" || s.status === "idle") {
            stopPolling();
          }
        })
        .catch(() => {});
    }, 3000);
  }, [load, stopPolling]);

  useEffect(() => {
    load(true);
    api.getPlanStatus()
      .then((s) => {
        setGenStatus(s.status as "idle" | "generating" | "ready" | "error");
        if (s.status === "generating") startPolling();
      })
      .catch(() => {});
    return () => stopPolling();
  }, [load, startPolling, stopPolling]);

  useEffect(() => {
    if (genStatus === "generating" && !pollRef.current) {
      startPolling();
    }
  }, [genStatus, startPolling]);

  function handleLogged(pointsAwarded: number) {
    load();
    onWorkoutLogged(`Workout abgeschlossen! +${pointsAwarded} Punkte`);
  }

  function handleSwapped() {
    load();
  }

  if (genStatus === "generating") {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-8">
        <div className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="text-text font-medium">Trainingsplan wird erstellt…</p>
        <p className="text-sm text-text-muted">Dein persönlicher Plan wird gerade erstellt. Das kann eine Minute dauern.</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-8">
        <p className="text-text font-medium">Noch kein Trainingsplan vorhanden.</p>
        <p className="text-sm text-text-muted">Geh in den Chat und sag &quot;Ich will loslegen&quot;.</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        Lade Plan…
      </div>
    );
  }

  // Group workouts by week
  const weeks = Array.from({ length: plan.duration_weeks }, (_, i) => i + 1);
  const workoutsByWeek: Record<number, PlanWorkout[]> = {};
  for (const w of plan.workouts) {
    if (!workoutsByWeek[w.week_number]) workoutsByWeek[w.week_number] = [];
    workoutsByWeek[w.week_number].push(w);
  }

  const currentWeekWorkouts = workoutsByWeek[selectedWeek] ?? [];

  // Phase for selected week
  const currentPhase = plan.phases.find((p) => p.weeks.includes(selectedWeek));

  return (
    <div className="h-full overflow-y-auto px-6 py-6 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-text">{plan.name}</h1>
        <p className="text-sm text-text-muted mt-0.5">
          {GOAL_LABELS[plan.goal] ?? plan.goal}
          {" · "}
          {plan.duration_weeks} Wochen
          {" · "}
          {Object.keys(workoutsByWeek[1] ?? {}).length || currentWeekWorkouts.length} Einheiten/Woche
        </p>
      </div>

      {/* Coach explanation */}
      {plan.explanation && (
        <div className="bg-accent-subtle border border-accent/30 rounded-[10px] px-4 py-3 flex gap-2">
          <span className="text-base shrink-0">💡</span>
          <p className="text-sm text-text-muted">{plan.explanation}</p>
        </div>
      )}

      {/* Phase pills */}
      {plan.phases.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {plan.phases.map((ph) => (
            <button
              key={ph.phase_number}
              onClick={() => setSelectedWeek(ph.weeks[0])}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                currentPhase?.phase_number === ph.phase_number
                  ? "bg-accent-subtle border-accent text-accent"
                  : "border-border text-text-muted hover:border-text-muted"
              }`}
            >
              Phase {ph.phase_number}: {ph.name} (Wo. {ph.weeks[0]}–{ph.weeks[ph.weeks.length - 1]})
            </button>
          ))}
        </div>
      )}

      {/* Week tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {weeks.map((w) => {
          const phase = plan.phases.find((p) => p.weeks.includes(w));
          return (
            <button
              key={w}
              onClick={() => setSelectedWeek(w)}
              className={`shrink-0 px-3 py-1.5 rounded-[8px] text-xs font-medium transition-colors ${
                selectedWeek === w
                  ? "bg-accent text-white"
                  : "bg-bg-hover text-text-muted hover:text-text"
              }`}
            >
              Woche {w}
              {phase && (
                <span className="block text-[10px] opacity-75">{phase.name}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Phase description */}
      {currentPhase && (
        <div className="bg-bg-surface border border-border rounded-[10px] px-4 py-3">
          <p className="text-xs font-semibold text-accent mb-0.5">
            Phase {currentPhase.phase_number}: {currentPhase.name}
          </p>
          <p className="text-xs text-text-muted">{currentPhase.desc}</p>
          {currentWeekWorkouts[0]?.exercises[0] && (
            <p className="text-xs text-text-subtle mt-1">
              Woche {selectedWeek}
              {` · ${currentWeekWorkouts[0].exercises[0].sets} Sätze`}
              {` · ${currentWeekWorkouts[0].exercises[0].reps} Wdh`}
              {currentWeekWorkouts[0].exercises[0].rest_sec
                ? ` · ${currentWeekWorkouts[0].exercises[0].rest_sec}s Pause`
                : ""}
            </p>
          )}
        </div>
      )}

      {/* Workouts for selected week */}
      <div className="space-y-3">
        {currentWeekWorkouts.length === 0 ? (
          <p className="text-sm text-text-muted text-center py-6">Keine Workouts für Woche {selectedWeek}.</p>
        ) : (
          currentWeekWorkouts.map((w) => (
            <WorkoutCard
              key={w.id}
              workout={w}
              doneToday={completedIds.has(w.id)}
              onLogged={handleLogged}
              onSwapped={handleSwapped}
            />
          ))
        )}
      </div>
    </div>
  );
}
