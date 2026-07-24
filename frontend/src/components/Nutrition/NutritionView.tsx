import { useEffect, useState } from "react";
import { RefreshCw, Utensils, Flame, Zap, ShieldAlert } from "lucide-react";
import { api } from "../../api/backend";
import type { NutritionAdvice } from "../../types";

const MEAL_ICONS: Record<string, string> = {
  "Frühstück": "☀️",
  "Mittagessen": "🍽️",
  "Abendessen": "🌙",
  "Snack": "🍎",
};

export default function NutritionView() {
  const [advice, setAdvice] = useState<NutritionAdvice | null>(null);
  const [targets, setTargets] = useState<{ calories?: number; protein_g?: number; carbs_g?: number; fat_g?: number; note?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshingMeals, setRefreshingMeals] = useState(false);
  const [refreshingNutrients, setRefreshingNutrients] = useState(false);
  const [noPlan, setNoPlan] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    load();
    api.getNutritionTargets().then(setTargets).catch(() => {});
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    setNoPlan(false);
    try {
      const data = await api.getNutritionAdvice();
      setAdvice(data);
    } catch (e) {
      if (String(e).includes("404")) {
        setNoPlan(true);
      } else {
        setError("Generierung fehlgeschlagen. Bitte versuche es später nochmal.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshMeals() {
    setRefreshingMeals(true);
    try {
      const data = await api.refreshNutritionMeals();
      setAdvice(data);
    } catch {
      setError("Generierung fehlgeschlagen. Bitte versuche es später nochmal.");
    } finally {
      setRefreshingMeals(false);
    }
  }

  async function handleRefreshNutrients() {
    setRefreshingNutrients(true);
    try {
      const data = await api.refreshNutritionNutrients();
      setAdvice(data);
    } catch {
      setError("Generierung fehlgeschlagen. Bitte versuche es später nochmal.");
    } finally {
      setRefreshingNutrients(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-text-muted">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="text-sm">Ernährungstipps werden generiert…</p>
      </div>
    );
  }

  if (noPlan) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted px-8 text-center">
        <Utensils size={40} className="text-border" />
        <p className="text-sm font-medium text-text">Noch kein Trainingsplan vorhanden</p>
        <p className="text-xs text-text-subtle">Erstelle zuerst deinen Trainingsplan im Chat — danach erscheinen hier personalisierte Ernährungstipps.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted px-8 text-center">
        <Utensils size={40} className="text-border" />
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!advice) return null;

  return (
    <div className="h-full overflow-y-auto px-6 py-6 space-y-6 max-w-3xl mx-auto">

      {/* Ziel-Erklärung (statisch) */}
      <div>
        <h1 className="text-xl font-semibold text-text">Ernährung</h1>
        <p className="text-sm text-text-muted mt-1 leading-relaxed">{advice.goal_note}</p>
      </div>

      {/* Kalorienziele (statisch) */}
      {targets && !targets.note && targets.calories && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Kalorien", value: `${targets.calories} kcal`, color: "text-orange-400" },
            { label: "Protein", value: `${targets.protein_g}g`, color: "text-accent" },
            { label: "Kohlenhydrate", value: `${targets.carbs_g}g`, color: "text-yellow-400" },
            { label: "Fett", value: `${targets.fat_g}g`, color: "text-purple-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-bg-elevated rounded-lg p-3 border border-border text-center">
              <div className={`text-lg font-semibold ${color}`}>{value}</div>
              <div className="text-xs text-text-muted mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}
      {targets?.note && (
        <div className="text-xs text-text-subtle bg-bg-elevated border border-border rounded px-3 py-2">
          {targets.note}
        </div>
      )}

      {/* Beispiel-Mahlzeiten (refreshbar) */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider flex items-center gap-2">
            <Utensils size={14} /> Beispiel-Mahlzeiten
          </h2>
          <button
            onClick={handleRefreshMeals}
            disabled={refreshingMeals}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs text-text-muted hover:text-text hover:bg-bg-hover transition-colors disabled:opacity-40"
            title="Neue Mahlzeiten vorschlagen"
          >
            <RefreshCw size={12} className={refreshingMeals ? "animate-spin" : ""} />
            Neu vorschlagen
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {advice.meals.map((meal) => (
            <div key={meal.meal_type} className="bg-bg-elevated border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-subtle font-medium">
                  {MEAL_ICONS[meal.meal_type] ?? "🍴"} {meal.meal_type}
                </span>
                <span className="text-xs text-text-subtle">{meal.approx_kcal} kcal</span>
              </div>
              <div className="font-medium text-text text-sm">{meal.name}</div>
              <div className="text-xs text-text-muted mt-1 leading-relaxed">{meal.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Wichtige Tipps (statisch) */}
      <section>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
          <Zap size={14} /> Wichtige Tipps
        </h2>
        <ul className="space-y-2">
          {advice.general_tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
              <span className="text-accent mt-0.5 shrink-0">•</span>
              {tip}
            </li>
          ))}
        </ul>
      </section>

      {/* Wichtige Nährstoffe + Besser meiden (refreshbar) */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider flex items-center gap-2">
            <Flame size={14} /> Nährstoffe & Meiden
          </h2>
          <button
            onClick={handleRefreshNutrients}
            disabled={refreshingNutrients}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs text-text-muted hover:text-text hover:bg-bg-hover transition-colors disabled:opacity-40"
            title="Neue Empfehlungen generieren"
          >
            <RefreshCw size={12} className={refreshingNutrients ? "animate-spin" : ""} />
            Neu generieren
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <h3 className="text-xs font-semibold text-text-subtle uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Flame size={12} className="text-yellow-400" /> Wichtige Nährstoffe
            </h3>
            <ul className="space-y-2">
              {advice.key_nutrients.map((n, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                  <span className="text-yellow-400 mt-0.5 shrink-0">★</span>
                  {n}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-xs font-semibold text-text-subtle uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ShieldAlert size={12} className="text-red-400" /> Besser meiden
            </h3>
            <ul className="space-y-2">
              {advice.avoid.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                  <span className="text-red-400 mt-0.5 shrink-0">✕</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
