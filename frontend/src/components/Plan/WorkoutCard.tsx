import { useState, useEffect, useCallback, useRef } from "react";
import { ChevronDown, ChevronUp, CheckCircle } from "lucide-react";
import type { PlanWorkout } from "../../types";
import ExerciseRow from "./ExerciseRow";
import { api } from "../../api/backend";

const DAY_NAMES = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

interface NewBadge {
  key: string;
  title: string;
  desc: string;
  icon: string;
}

interface LevelUp {
  name: string;
  icon: string;
}

interface Props {
  workout: PlanWorkout;
  doneToday: boolean;
  onLogged: (pointsAwarded: number) => void;
  onSwapped: () => void;
}

function BadgePopup({ badges, onClose }: { badges: NewBadge[]; onClose: () => void }) {
  const [index, setIndex] = useState(0);
  const badge = badges[index];

  const next = useCallback(() => {
    if (index < badges.length - 1) setIndex((i) => i + 1);
    else onClose();
  }, [index, badges.length, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-bg-surface border border-accent rounded-[16px] p-8 mx-6 max-w-xs w-full
        flex flex-col items-center gap-3 shadow-2xl animate-pop text-center relative">
        <button
          onClick={next}
          className="absolute top-3 right-3 text-text-muted hover:text-text transition-colors text-lg leading-none"
          aria-label="Schließen"
        >
          ×
        </button>
        <span className="text-6xl">{badge.icon}</span>
        <div>
          <p className="text-xs font-semibold text-accent uppercase tracking-wider mb-1">
            Auszeichnung freigeschaltet!
          </p>
          <p className="text-lg font-bold text-text">{badge.title}</p>
          <p className="text-sm text-text-muted mt-1">{badge.desc}</p>
        </div>
        {badges.length > 1 && (
          <p className="text-xs text-text-subtle">{index + 1} / {badges.length}</p>
        )}
      </div>
    </div>
  );
}

export default function WorkoutCard({ workout, doneToday, onLogged, onSwapped }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [logged, setLogged] = useState(doneToday);
  const [swappingId, setSwappingId] = useState<string | null>(null);
  const [newBadges, setNewBadges] = useState<NewBadge[]>([]);
  const [levelUp, setLevelUp] = useState<LevelUp | null>(null);
  const pendingCompletedRef = useRef(false);

  useEffect(() => { setLogged(doneToday); }, [doneToday]);

  function dispatchCompletedIfPending() {
    if (pendingCompletedRef.current) {
      pendingCompletedRef.current = false;
      window.dispatchEvent(new CustomEvent("workout_completed"));
    }
  }

  async function handleLog() {
    if (logged || loading) return;
    setLoading(true);
    try {
      const result = await api.logWorkout({ plan_workout_id: workout.id });
      setLogged(true);
      const hasBadges = !!result.new_badges?.length;
      const hasLevelUp = !!(result.level_up && result.new_level_icon);
      if (hasBadges) setNewBadges(result.new_badges);
      if (hasLevelUp) setLevelUp({ name: result.level_up as string, icon: result.new_level_icon as string });
      onLogged(result.points_awarded);
      if (hasBadges || hasLevelUp) {
        pendingCompletedRef.current = true;
      } else {
        window.dispatchEvent(new CustomEvent("workout_completed"));
      }
    } catch {
      // silently ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleSwap(exerciseId: string | null) {
    if (!exerciseId) return;
    setSwappingId(exerciseId);
    try {
      await api.swapExercise(workout.id, exerciseId);
      onSwapped();
    } catch {
      // silently ignore
    } finally {
      setSwappingId(null);
    }
  }

  const dayLabel = DAY_NAMES[(workout.day_of_week - 1) % 7];

  return (
    <>
      {levelUp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-bg-surface border border-yellow-400/60 rounded-[16px] p-8 mx-6 max-w-xs w-full
            flex flex-col items-center gap-3 shadow-2xl animate-pop text-center relative">
            <button
              onClick={() => { setLevelUp(null); if (!newBadges.length) dispatchCompletedIfPending(); }}
              className="absolute top-3 right-3 text-text-muted hover:text-text transition-colors text-lg leading-none"
              aria-label="Schließen"
            >
              ×
            </button>
            <span className="text-6xl">{levelUp.icon}</span>
            <div>
              <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-1">
                Level Up!
              </p>
              <p className="text-lg font-bold text-text">{levelUp.name}</p>
              <p className="text-sm text-text-muted mt-1">Du hast ein neues Level erreicht!</p>
            </div>
          </div>
        </div>
      )}
      {!levelUp && newBadges.length > 0 && (
        <BadgePopup badges={newBadges} onClose={() => { setNewBadges([]); dispatchCompletedIfPending(); }} />
      )}

      <div className="bg-bg-surface border border-border rounded-[10px] overflow-hidden transition-shadow hover:shadow-md">
        <button
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-bg-hover transition-colors text-left"
        >
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-accent bg-accent-subtle px-2 py-0.5 rounded-full">
              {dayLabel}
            </span>
            <span className="font-medium text-text">{workout.name}</span>
            <span className="text-xs text-text-muted">{workout.exercises.length} Übungen</span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {logged && <CheckCircle size={16} className="text-accent" />}
            {open
              ? <ChevronUp size={16} className="text-text-muted" />
              : <ChevronDown size={16} className="text-text-muted" />}
          </div>
        </button>

        {open && (
          <div className="px-5 pb-5 border-t border-border-subtle">
            <div className="mt-3 mb-4">
              {workout.exercises.map((ex, i) => (
                <ExerciseRow
                  key={ex.exercise_id ?? `${ex.name}-${i}`}
                  ex={ex}
                  swapping={!!ex.exercise_id && swappingId === ex.exercise_id}
                  onSwap={() => handleSwap(ex.exercise_id)}
                />
              ))}
            </div>
            <button
              onClick={handleLog}
              disabled={logged || loading}
              className="w-full py-2.5 rounded-[10px] text-sm font-medium transition-colors
                bg-accent hover:bg-accent-hover text-white
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {logged ? "Workout abgeschlossen" : loading ? "Wird gespeichert…" : "Workout abschliessen"}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
