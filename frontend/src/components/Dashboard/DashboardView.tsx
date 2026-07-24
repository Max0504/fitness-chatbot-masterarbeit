import { useEffect, useState } from "react";
import { Flame, Dumbbell, Trophy, Activity, TrendingDown } from "lucide-react";
import { api } from "../../api/backend";
import type { AllBadge, ActivityEntry, CardioStats } from "../../api/backend";
import type { DashboardData, Badge, Profile } from "../../types";
import StatsCard from "./StatsCard";

export default function DashboardView() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const handler = () => setRefreshKey((k) => k + 1);
    window.addEventListener("activity_logged", handler);
    return () => window.removeEventListener("activity_logged", handler);
  }, []);

  useEffect(() => {
    api.getDashboard()
      .then(async (d) => {
        setData(d);
        for (const b of d.new_badges) {
          api.markBadgeSeen(b.badge_key).catch(() => {});
        }
      })
      .catch(() => setError(true));
  }, [refreshKey]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        Dashboard konnte nicht geladen werden.
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        Lade Dashboard…
      </div>
    );
  }

  const { level, streak_days, total_workouts, next_workout, new_badges, progress_summary } = data;

  const isEmpty = total_workouts === 0 && !next_workout && streak_days === 0;

  const progressPct = level.points_to_next > 0
    ? Math.round((level.total_points / (level.total_points + level.points_to_next)) * 100)
    : 100;

  if (isEmpty) {
    return (
      <div className="h-full flex flex-col items-center justify-center px-6 text-center space-y-3">
        <span className="text-4xl">🌱</span>
        <p className="text-text font-semibold">Noch kein Training gestartet</p>
        <p className="text-sm text-text-muted max-w-xs">
          Geh in den Chat und starte das Onboarding — dann erstellen wir gemeinsam deinen persönlichen Trainingsplan.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-6 space-y-5">

      {/* New badge notification */}
      {new_badges.length > 0 && (
        <div className="bg-accent-subtle border border-accent rounded-[10px] p-4 space-y-2">
          <p className="text-sm font-semibold text-accent">Neue Auszeichnungen! 🎉</p>
          <div className="flex flex-wrap gap-2">
            {new_badges.map((b) => <BadgePill key={b.badge_key} badge={b} />)}
          </div>
        </div>
      )}

      {/* Level card */}
      <div className="bg-bg-surface border border-border rounded-[10px] p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-3xl">{level.icon}</span>
            <div>
              <p className="font-bold text-text">{level.name}</p>
              <p className="text-xs text-text-muted">{level.total_points} Punkte gesamt</p>
            </div>
          </div>
          {level.next_level_name && (
            <div className="text-right">
              <p className="text-xs text-text-subtle">Nächstes Level</p>
              <p className="text-xs font-medium text-accent">{level.next_level_name}</p>
              <p className="text-xs text-text-muted">noch {level.points_to_next} Punkte</p>
            </div>
          )}
        </div>
        <div className="w-full h-2 bg-bg-hover rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-700"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <StatsCard icon={Flame} label="Streak" value={streak_days} sub={streak_days === 1 ? "Tag" : "Tage"} />
        <StatsCard icon={Dumbbell} label="Workouts gesamt" value={total_workouts} />
      </div>

      {/* Recent activities */}
      <RecentActivitiesCard />

      {/* Cardio stats */}
      <CardioStatsCard />

      {/* Specific goal */}
      <GoalCard />

      {/* Progress summary */}
      {progress_summary && <ProgressSummaryCard summary={progress_summary} />}

      {/* Next workout */}
      <div className="bg-bg-surface border border-border rounded-[10px] p-5">
        <h2 className="text-sm font-semibold text-text mb-3">Nächstes Workout</h2>
        {next_workout ? (
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-text">{next_workout.name}</p>
              <p className="text-sm text-text-muted mt-0.5">{next_workout.exercises_count} Übungen</p>
            </div>
            <span className="text-accent text-xl">→</span>
          </div>
        ) : (
          <p className="text-sm text-text-muted">Kein Plan aktiv — erstell einen im Chat.</p>
        )}
      </div>

      {/* Badges all */}
      <BadgesSection />
    </div>
  );
}

function GoalCard() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [progress, setProgress] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.getProfile().then(setProfile).catch(() => {});
    api.getGoalProgress().then(setProgress).catch(() => {});
  }, []);

  if (!profile?.specific_goal) return null;

  const targetDate = profile.target_date ? new Date(profile.target_date) : null;
  const daysLeft = targetDate
    ? Math.ceil((targetDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;

  const pct =
    progress?.type === "weight" && typeof progress.progress_pct === "number"
      ? (progress.progress_pct as number)
      : null;

  return (
    <div className="bg-bg-surface border border-border rounded-[10px] p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">🎯</span>
        <h2 className="text-sm font-semibold text-text">Mein Ziel</h2>
      </div>
      <p className="text-sm text-text mb-3">{profile.specific_goal}</p>

      {pct !== null && (
        <div className="mb-2">
          <div className="flex justify-between text-xs text-text-muted mb-1">
            <span>{progress!.start as number} kg</span>
            <span className="text-accent font-medium">{pct}%</span>
            <span>{progress!.target as number} kg</span>
          </div>
          <div className="w-full h-2 bg-bg-hover rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-700"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-text-muted mt-1 text-center">
            Aktuell: {progress!.current as number} kg
          </p>
        </div>
      )}

      {daysLeft !== null && daysLeft > 0 && (
        <div className="flex items-center gap-1.5 mt-1">
          <span className="text-xs text-text-muted">⏳ Noch</span>
          <span className="text-xs font-semibold text-accent">{daysLeft} Tage</span>
          <span className="text-xs text-text-muted">bis zum Zieldatum</span>
        </div>
      )}
      {daysLeft !== null && daysLeft <= 0 && (
        <p className="text-xs text-accent font-medium mt-1">🏁 Zieldatum erreicht!</p>
      )}
    </div>
  );
}

function BadgePill({ badge }: { badge: Badge }) {
  return (
    <div className="flex items-center gap-1.5 bg-bg-surface border border-border rounded-full px-3 py-1">
      <span>{badge.icon}</span>
      <span className="text-xs font-medium text-text">{badge.title}</span>
    </div>
  );
}

function ProgressSummaryCard({ summary }: { summary: Record<string, unknown> }) {
  if (summary.type === "weight") {
    const current = summary.current_kg as number;
    const target = summary.target_kg as number | null;
    const change = summary.last_change as number;
    const arrow = summary.arrow as string;
    const arrowColor = arrow === "↓" ? "text-green-400" : arrow === "↑" ? "text-red-400" : "text-text-muted";
    return (
      <div className="bg-bg-surface border border-border rounded-[10px] p-5">
        <h2 className="text-sm font-semibold text-text mb-3">Gewichtsfortschritt</h2>
        <div className="flex items-end gap-4">
          <div>
            <p className="text-2xl font-bold text-text">{current} kg</p>
            <p className={`text-sm font-medium ${arrowColor}`}>
              {arrow} {Math.abs(change)} kg seit letztem Eintrag
            </p>
          </div>
          {target && (
            <div className="ml-auto text-right">
              <p className="text-xs text-text-muted">Ziel</p>
              <p className="text-sm font-semibold text-accent">{target} kg</p>
            </div>
          )}
        </div>
      </div>
    );
  }
  return null;
}

function RecentActivitiesCard() {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const handler = () => setRefreshKey((k) => k + 1);
    window.addEventListener("activity_logged", handler);
    return () => window.removeEventListener("activity_logged", handler);
  }, []);

  useEffect(() => {
    api.getRecentActivities()
      .then((e) => { setEntries(e.slice(0, 5)); setLoaded(true); })
      .catch(() => setLoaded(true));
  }, [refreshKey]);

  if (!loaded || entries.length === 0) return null;

  return (
    <div className="bg-bg-surface border border-border rounded-[10px] p-5">
      <div className="flex items-center gap-2 mb-3">
        <Activity size={15} className="text-accent" />
        <h2 className="text-sm font-semibold text-text">Letzte Aktivitäten</h2>
      </div>
      <div className="space-y-2">
        {entries.map((e, i) => {
          const icon = e.type === "strength" ? "💪" : e.activity_type === "cycling" ? "🚴" : "🏃";
          const dateStr = new Date(e.date).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
          return (
            <div key={i} className="flex items-start gap-3 py-2 border-b border-border last:border-0">
              <span className="text-lg leading-none mt-0.5">{icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text truncate">{e.summary}</p>
                {e.type === "strength" && e.exercises && e.exercises.length > 0 && (
                  <p className="text-xs text-text-muted mt-0.5">
                    {e.exercises.slice(0, 2).map((ex) => `${ex.exercise} ${ex.sets}×${ex.reps}${ex.weight_kg ? ` @ ${ex.weight_kg} kg` : ""}`).join(" · ")}
                    {e.exercises.length > 2 && ` +${e.exercises.length - 2}`}
                  </p>
                )}
              </div>
              <span className="text-xs text-text-muted shrink-0">{dateStr}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatPace(pace: number): string {
  const m = Math.floor(pace);
  const s = Math.round((pace - m) * 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function CardioStatsCard() {
  const [stats, setStats] = useState<CardioStats | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const handler = () => setRefreshKey((k) => k + 1);
    window.addEventListener("activity_logged", handler);
    return () => window.removeEventListener("activity_logged", handler);
  }, []);

  useEffect(() => {
    api.getCardioStats().then(setStats).catch(() => {});
  }, [refreshKey]);

  if (!stats || stats.running.total_runs === 0) return null;

  const { running } = stats;

  return (
    <div className="bg-bg-surface border border-border rounded-[10px] p-5">
      <div className="flex items-center gap-2 mb-3">
        <TrendingDown size={15} className="text-accent" />
        <h2 className="text-sm font-semibold text-text">Lauf-Statistiken</h2>
        {running.last_7_days > 0 && (
          <span className="ml-auto text-xs text-text-muted">{running.last_7_days}× diese Woche</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center">
          <p className="text-lg font-bold text-text">{running.total_km}</p>
          <p className="text-xs text-text-muted">km gesamt</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-text">
            {running.avg_pace ? formatPace(running.avg_pace) : "–"}
          </p>
          <p className="text-xs text-text-muted">Ø Tempo</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-text">
            {running.best_pace ? formatPace(running.best_pace) : "–"}
          </p>
          <p className="text-xs text-text-muted">Bestpace</p>
        </div>
      </div>

      {running.pace_trend.length >= 2 && (
        <div>
          <p className="text-xs text-text-muted mb-2">Letzte {running.pace_trend.length} Läufe</p>
          <div className="flex items-end gap-1 h-10">
            {running.pace_trend.slice().reverse().map((pt, i) => {
              const paces = running.pace_trend.map((p) => p.pace);
              const minPace = Math.min(...paces);
              const maxPace = Math.max(...paces);
              const range = maxPace - minPace || 1;
              const heightPct = ((maxPace - pt.pace) / range) * 70 + 30;
              return (
                <div
                  key={i}
                  className="flex-1 bg-accent rounded-sm opacity-80"
                  style={{ height: `${heightPct}%` }}
                  title={`${new Date(pt.date).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}: ${formatPace(pt.pace)} min/km · ${pt.distance_km} km`}
                />
              );
            })}
          </div>
          <div className="flex justify-between mt-1">
            {running.pace_trend.slice().reverse().map((pt, i) => (
              <span key={i} className="text-[9px] text-text-muted flex-1 text-center">
                {new Date(pt.date).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BadgesSection() {
  const [badges, setBadges] = useState<AllBadge[]>([]);

  useEffect(() => {
    api.getAllBadges().then(setBadges).catch(() => {});
  }, []);

  if (badges.length === 0) return null;

  const earned = badges.filter((b) => b.earned);

  return (
    <div className="bg-bg-surface border border-border rounded-[10px] p-5">
      <div className="flex items-center gap-2 mb-3">
        <Trophy size={15} className="text-accent" />
        <h2 className="text-sm font-semibold text-text">Auszeichnungen</h2>
        <span className="text-xs text-text-muted">{earned.length}/{badges.length}</span>
      </div>
      <div className="grid grid-cols-4 gap-3">
        {badges.map((b) => (
          <div
            key={b.badge_key}
            title={b.desc}
            className={`flex flex-col items-center gap-1 text-center p-2 rounded-[8px] transition-colors ${
              b.earned
                ? "bg-accent-subtle"
                : "bg-bg-hover opacity-40"
            }`}
          >
            <span className={`text-2xl ${!b.earned ? "grayscale" : ""}`}
              style={!b.earned ? { filter: "grayscale(1)" } : {}}>
              {b.icon}
            </span>
            <span className="text-[10px] text-text-muted leading-tight">{b.title}</span>
            {b.earned && b.earned_at && (
              <span className="text-[9px] text-accent">
                {new Date(b.earned_at).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
