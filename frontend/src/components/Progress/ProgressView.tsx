import { useEffect, useState, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Dot,
} from "recharts";
import { api } from "../../api/backend";
import type { WeightLog, PerformanceLog } from "../../types";

// ── Konstanten ────────────────────────────────────────────────────────────────

const METRIC_PRESETS = [
  { label: "5km Zeit",        key: "run_5km_seconds",  unit: "s",    display: "Zeit" },
  { label: "Bankdrücken 1RM", key: "bench_1rm_kg",     unit: "kg",   display: "kg" },
  { label: "Kniebeugen 1RM",  key: "squat_1rm_kg",     unit: "kg",   display: "kg" },
  { label: "Kreuzheben 1RM",  key: "deadlift_1rm_kg",  unit: "kg",   display: "kg" },
  { label: "Klimmzüge",       key: "pullups_reps",      unit: "reps", display: "Wdh" },
  { label: "Liegestütze",     key: "pushups_reps",      unit: "reps", display: "Wdh" },
];

const RANGES = [
  { label: "1W",  days: 7 },
  { label: "1M",  days: 30 },
  { label: "3M",  days: 90 },
  { label: "6M",  days: 180 },
  { label: "1J",  days: 365 },
];

// ── Hilfsfunktionen ───────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
}

function fmtSeconds(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, "0")} min`;
}

function fmtSecondsAxis(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function filterByDays<T extends { logged_at: string }>(logs: T[], days: number): T[] {
  const cutoff = Date.now() - days * 86_400_000;
  return logs.filter((l) => new Date(l.logged_at).getTime() >= cutoff);
}

const CHART_STYLE = {
  background: "#1c1c26",
  border: "1px solid #2a2a38",
  borderRadius: 8,
  fontSize: 12,
  color: "#e5e7eb",
};

// ── Zeitraum-Auswahl ──────────────────────────────────────────────────────────

function RangePills({ range, onChange }: { range: number; onChange: (d: number) => void }) {
  return (
    <div className="flex gap-1">
      {RANGES.map((r) => (
        <button
          key={r.days}
          onClick={() => onChange(r.days)}
          className={`px-2.5 py-0.5 text-xs rounded-full border transition-colors ${
            range === r.days
              ? "bg-accent-subtle border-accent text-accent"
              : "border-border text-text-muted hover:border-text-muted"
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}

// ── Gewicht-Sektion ───────────────────────────────────────────────────────────

function WeightSection() {
  const [logs, setLogs] = useState<WeightLog[]>([]);
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [range, setRange] = useState(90);

  const load = useCallback(() => {
    api.getWeightHistory(400).then(setLogs).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handler = () => load();
    window.addEventListener("weight_updated", handler);
    return () => window.removeEventListener("weight_updated", handler);
  }, [load]);

  async function handleLog() {
    const val = parseFloat(input.replace(",", "."));
    if (!val || val < 20 || val > 400) return;
    setSaving(true);
    try {
      await api.logWeight(val);
      setInput("");
      load();
    } finally {
      setSaving(false);
    }
  }

  const filtered = filterByDays(logs, range);
  const chartData = filtered.map((l) => ({ date: fmtDate(l.logged_at), value: l.weight_kg }));
  const latest = logs[logs.length - 1];

  return (
    <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-text">Gewicht</h2>
          {latest && (
            <span className="text-xs text-text-muted">
              Aktuell: <span className="font-semibold text-text">{latest.weight_kg} kg</span>
            </span>
          )}
        </div>
        <RangePills range={range} onChange={setRange} />
      </div>

      {/* Eingabe */}
      <div className="flex gap-2">
        <input
          type="number"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLog()}
          placeholder="kg eingeben…"
          step="0.1"
          className="flex-1 bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
        />
        <button
          onClick={handleLog}
          disabled={saving || !input}
          className="px-4 py-2 rounded-[8px] text-sm font-medium bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-40"
        >
          {saving ? "…" : "Eintragen"}
        </button>
      </div>

      {/* Chart */}
      {chartData.length > 1 ? (
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="date" axisLine={false} tickLine={false}
              tick={{ fill: "#9ca3af", fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis axisLine={false} tickLine={false}
              tick={{ fill: "#9ca3af", fontSize: 11 }} domain={["auto", "auto"]} />
            <Tooltip contentStyle={CHART_STYLE}
              formatter={(v: number) => [`${v} kg`, "Gewicht"]} />
            <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2}
              dot={<Dot r={3} fill="#10b981" />} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="text-center py-4 space-y-1">
          <p className="text-xs text-text-subtle">
            {logs.length === 0
              ? "Noch kein Gewicht eingetragen."
              : logs.length === 1
              ? "Noch ein weiterer Eintrag nötig um das Diagramm zu sehen."
              : "Keine Einträge im gewählten Zeitraum."}
          </p>
          {logs.length < 2 && (
            <p className="text-xs text-text-subtle opacity-60">
              Mindestens 2 Messungen werden für das Diagramm benötigt.
            </p>
          )}
        </div>
      )}

      {/* Letzte Einträge */}
      {filtered.length > 0 && (
        <div className="space-y-1">
          {[...filtered].reverse().slice(0, 5).map((l) => (
            <div key={l.id} className="flex justify-between text-xs text-text-muted">
              <span>{fmtDate(l.logged_at)}</span>
              <span className="font-medium text-text">{l.weight_kg} kg</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ── Leistungs-Sektion ─────────────────────────────────────────────────────────

function PerformanceSection() {
  const [existingMetrics, setExistingMetrics] = useState<{ metric_type: string; unit: string }[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>(METRIC_PRESETS[0].key);
  const [logs, setLogs] = useState<PerformanceLog[]>([]);
  const [input, setInput] = useState("");
  const [timeMins, setTimeMins] = useState("");
  const [timeSecs, setTimeSecs] = useState("");
  const [saving, setSaving] = useState(false);
  const [customMetric, setCustomMetric] = useState(false);
  const [customKey, setCustomKey] = useState("");
  const [customUnit, setCustomUnit] = useState("");
  const [range, setRange] = useState(90);
  const [confirmDelete, setConfirmDelete] = useState<{ key: string; label: string } | null>(null);

  const activeKey = customMetric ? customKey : selectedKey;
  const preset = METRIC_PRESETS.find((p) => p.key === activeKey);
  const activeUnit = customMetric ? customUnit : (preset?.unit ?? "");
  const isTime = activeKey.includes("seconds") || activeUnit === "s";

  const loadMetrics = useCallback(() => {
    api.getAllPerformanceMetrics().then(setExistingMetrics).catch(() => {});
  }, []);

  const loadHistory = useCallback(() => {
    if (!activeKey) return;
    api.getPerformanceHistory(activeKey, 400).then(setLogs).catch(() => setLogs([]));
  }, [activeKey]);

  useEffect(() => { loadMetrics(); }, [loadMetrics]);
  useEffect(() => {
    setInput("");
    setTimeMins("");
    setTimeSecs("");
    loadHistory();
  }, [loadHistory]);

  async function handleDeleteConfirmed() {
    if (!confirmDelete) return;
    const { key } = confirmDelete;
    setConfirmDelete(null);
    await api.deletePerformanceMetric(key).catch(() => {});
    if (activeKey === key) {
      setSelectedKey(METRIC_PRESETS[0].key);
      setCustomMetric(false);
      setLogs([]);
    }
    loadMetrics();
  }

  async function handleLog() {
    let val: number;
    if (isTime) {
      const m = parseInt(timeMins || "0", 10);
      const s = parseInt(timeSecs || "0", 10);
      if (isNaN(m) || isNaN(s) || s > 59 || (m === 0 && s === 0)) return;
      val = m * 60 + s;
    } else {
      val = parseFloat(input.replace(",", "."));
      if (!val) return;
    }
    if (!activeKey || !activeUnit) return;
    setSaving(true);
    try {
      await api.logPerformance({ metric_type: activeKey, value: val, unit: activeUnit });
      setInput("");
      setTimeMins("");
      setTimeSecs("");
      loadHistory();
      loadMetrics();
    } finally {
      setSaving(false);
    }
  }

  const filtered = filterByDays(logs, range);
  const chartData = filtered.map((l) => ({ date: fmtDate(l.logged_at), value: l.value }));
  const latest = logs[logs.length - 1];

  const allPresetKeys = new Set(METRIC_PRESETS.map((p) => p.key));
  const extraMetrics = existingMetrics.filter((m) => !allPresetKeys.has(m.metric_type));

  const logDisabled = saving || !activeKey || !activeUnit
    || (isTime ? (timeMins === "" && timeSecs === "") : !input);

  return (
    <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-sm font-semibold text-text">Leistung</h2>
        <RangePills range={range} onChange={setRange} />
      </div>

      {/* Bestätigungs-Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-bg-surface border border-border rounded-[12px] p-6 mx-4 max-w-sm w-full space-y-4 shadow-xl">
            <h3 className="text-sm font-semibold text-text">Einträge löschen?</h3>
            <p className="text-xs text-text-muted">
              Alle gespeicherten Werte für <span className="font-medium text-text">{confirmDelete.label}</span> werden
              unwiderruflich gelöscht. Dein Fortschritt geht dabei verloren.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 text-xs rounded-[8px] border border-border text-text-muted hover:text-text transition-colors"
              >
                Abbrechen
              </button>
              <button
                onClick={handleDeleteConfirmed}
                className="px-4 py-2 text-xs rounded-[8px] bg-red-500 hover:bg-red-600 text-white font-medium transition-colors"
              >
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preset-Chips */}
      <div className="flex flex-wrap gap-2">
        {METRIC_PRESETS.map((p) => {
          const isActive = !customMetric && selectedKey === p.key;
          return (
            <div key={p.key} className="flex items-stretch">
              <button
                onClick={() => { setSelectedKey(p.key); setCustomMetric(false); }}
                className={`px-2.5 py-1 text-xs rounded-l-full border border-r-0 transition-colors ${
                  isActive
                    ? "bg-accent-subtle border-accent text-accent"
                    : "border-border text-text-muted hover:border-text-muted"
                }`}
              >
                {p.label}
              </button>
              <button
                onClick={() => setConfirmDelete({ key: p.key, label: p.label })}
                title="Löschen"
                className={`px-1.5 text-xs rounded-r-full border border-l-0 transition-colors flex items-center justify-center ${
                  isActive
                    ? "bg-accent-subtle border-accent text-accent hover:text-red-400 hover:border-red-400"
                    : "border-border text-text-subtle hover:text-red-400 hover:border-red-400"
                }`}
              >
                ×
              </button>
            </div>
          );
        })}
        {extraMetrics.map((m) => {
          const isActive = !customMetric && selectedKey === m.metric_type;
          return (
            <div key={m.metric_type} className="flex items-stretch">
              <button
                onClick={() => { setSelectedKey(m.metric_type); setCustomMetric(false); }}
                className={`px-2.5 py-1 text-xs rounded-l-full border border-r-0 transition-colors ${
                  isActive
                    ? "bg-accent-subtle border-accent text-accent"
                    : "border-border text-text-muted hover:border-text-muted"
                }`}
              >
                {m.metric_type}
              </button>
              <button
                onClick={() => setConfirmDelete({ key: m.metric_type, label: m.metric_type })}
                title="Löschen"
                className={`px-1.5 text-xs rounded-r-full border border-l-0 transition-colors flex items-center justify-center ${
                  isActive
                    ? "bg-accent-subtle border-accent text-accent hover:text-red-400 hover:border-red-400"
                    : "border-border text-text-subtle hover:text-red-400 hover:border-red-400"
                }`}
              >
                ×
              </button>
            </div>
          );
        })}
        <button
          onClick={() => setCustomMetric((v) => !v)}
          className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
            customMetric
              ? "bg-accent-subtle border-accent text-accent"
              : "border-border text-text-muted hover:border-text-muted"
          }`}
        >
          + Eigene
        </button>
      </div>

      {/* Custom-Eingabe */}
      {customMetric && (
        <div className="flex gap-2">
          <input
            type="text"
            value={customKey}
            onChange={(e) => setCustomKey(e.target.value)}
            placeholder="Name (z.B. Plank, 10km Zeit)"
            className="flex-1 bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
          />
          <select
            value={customUnit}
            onChange={(e) => setCustomUnit(e.target.value)}
            className="bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text focus:outline-none focus:border-accent"
          >
            <option value="" disabled>Einheit</option>
            <option value="kg">Kilogramm</option>
            <option value="s">Min : Sek</option>
            <option value="reps">Wiederholungen</option>
          </select>
        </div>
      )}

      {/* Wert-Eingabe */}
      <div className="flex gap-2 items-center">
        {isTime ? (
          <div className="flex gap-1 flex-1 items-center">
            <input
              type="number"
              value={timeMins}
              onChange={(e) => setTimeMins(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLog()}
              placeholder="Min"
              min="0"
              className="w-20 bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
            />
            <span className="text-text-muted text-sm font-medium">:</span>
            <input
              type="number"
              value={timeSecs}
              onChange={(e) => setTimeSecs(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLog()}
              placeholder="Sek"
              min="0"
              max="59"
              className="w-20 bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
            />
            <span className="text-xs text-text-muted">min : sek</span>
          </div>
        ) : (
          <input
            type="number"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLog()}
            placeholder={`Wert in ${activeUnit || "…"}`}
            step="0.1"
            className="flex-1 bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
          />
        )}
        {latest && (
          <span className="text-xs text-text-muted shrink-0">
            Bisher: <span className="font-medium text-text">
              {isTime ? fmtSeconds(latest.value) : `${latest.value} ${activeUnit}`}
            </span>
          </span>
        )}
        <button
          onClick={handleLog}
          disabled={logDisabled}
          className="px-4 py-2 rounded-[8px] text-sm font-medium bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-40 shrink-0"
        >
          {saving ? "…" : "Eintragen"}
        </button>
      </div>

      {/* Chart */}
      {chartData.length > 1 ? (
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: isTime ? -8 : -20, bottom: 0 }}>
            <XAxis dataKey="date" axisLine={false} tickLine={false}
              tick={{ fill: "#9ca3af", fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              domain={["auto", "auto"]}
              tickFormatter={isTime ? fmtSecondsAxis : undefined}
            />
            <Tooltip
              contentStyle={CHART_STYLE}
              formatter={(v: number) => [
                isTime ? fmtSeconds(v) : `${v} ${activeUnit}`,
                preset?.label ?? activeKey,
              ]}
            />
            <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2}
              dot={<Dot r={3} fill="#6366f1" />} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="text-center py-4 space-y-1">
          <p className="text-xs text-text-subtle">
            {logs.length === 0
              ? "Noch keine Einträge für diese Metrik."
              : logs.length === 1
              ? "Noch ein weiterer Eintrag nötig um das Diagramm zu sehen."
              : "Keine Einträge im gewählten Zeitraum."}
          </p>
          {logs.length < 2 && (
            <p className="text-xs text-text-subtle opacity-60">
              Mindestens 2 Messungen werden für das Diagramm benötigt.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// ── Zielfortschritt-Sektion ───────────────────────────────────────────────────

function GoalProgressSection() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.getGoalProgress().then((d) => {
      if (d.available) setData(d);
    }).catch(() => {});
  }, []);

  if (!data) return null;

  if (data.type === "weight") {
    const pct = data.progress_pct as number;
    const current = data.current as number;
    const target = data.target as number;
    const start = data.start as number;
    const unit = data.unit as string;
    const points = (data.data_points as { date: string; value: number }[]) ?? [];
    const chartData = points.map((p) => ({ date: fmtDate(p.date), value: p.value }));

    return (
      <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text">Zielfortschritt</h2>
          <span className="text-xs font-semibold text-accent">{pct}%</span>
        </div>
        <div className="w-full h-2 bg-bg-hover rounded-full overflow-hidden">
          <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex justify-between text-xs text-text-muted">
          <span>Start: {start} {unit}</span>
          <span>Jetzt: <span className="text-text font-medium">{current} {unit}</span></span>
          <span>Ziel: {target} {unit}</span>
        </div>
        {chartData.length > 1 && (
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <XAxis dataKey="date" axisLine={false} tickLine={false}
                tick={{ fill: "#9ca3af", fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis axisLine={false} tickLine={false}
                tick={{ fill: "#9ca3af", fontSize: 11 }} domain={["auto", "auto"]} />
              <Tooltip contentStyle={CHART_STYLE}
                formatter={(v: number) => [`${v} ${unit}`, "Gewicht"]} />
              <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2}
                dot={<Dot r={3} fill="#10b981" />} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>
    );
  }

  return null;
}

// ── Haupt-View ────────────────────────────────────────────────────────────────

export default function ProgressView() {
  return (
    <div className="h-full overflow-y-auto px-6 py-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-text">Fortschritt</h1>
        <p className="text-xs text-text-subtle mt-0.5">Gewicht und Leistung über Zeit tracken.</p>
      </div>
      <GoalProgressSection />
      <WeightSection />
      <PerformanceSection />
    </div>
  );
}
