import { RefreshCw } from "lucide-react";
import type { ExerciseInPlan } from "../../types";

interface Props {
  ex: ExerciseInPlan;
  swapping: boolean;
  onSwap: () => void;
}

export default function ExerciseRow({ ex, swapping, onSwap }: Props) {
  const detail = ex.duration_min
    ? `${ex.duration_min} min`
    : `${ex.sets} × ${ex.reps}${ex.rest_sec ? `, ${ex.rest_sec}s Pause` : ""}`;

  return (
    <div className="py-2 border-b border-border-subtle last:border-0 group">
      <div className="flex items-center justify-between">
        <span className="text-sm text-text">{ex.name}</span>
        <div className="flex items-center gap-3 shrink-0 ml-4">
          <span className="text-xs text-text-muted">{detail}</span>
          {ex.exercise_id && (
            <button
              onClick={onSwap}
              disabled={swapping}
              title="Übung tauschen"
              className="opacity-0 group-hover:opacity-100 transition-opacity text-text-subtle hover:text-accent disabled:opacity-30"
            >
              <RefreshCw size={13} className={swapping ? "animate-spin" : ""} />
            </button>
          )}
        </div>
      </div>
      {ex.description && (
        <p className="text-[11px] text-text-subtle mt-0.5 pr-2">{ex.description}</p>
      )}
    </div>
  );
}
