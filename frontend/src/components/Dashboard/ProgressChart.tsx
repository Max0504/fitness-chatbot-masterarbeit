import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Dot } from "recharts";
import type { WeightLog } from "../../types";

interface Props {
  data: WeightLog[];
  unit?: string;
  label?: string;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
}

export default function ProgressChart({ data, unit = "kg", label = "Gewicht" }: Props) {
  const chartData = data.map((d) => ({
    date: formatDate(d.logged_at),
    value: d.weight_kg,
  }));

  if (chartData.length === 0) {
    return (
      <div className="bg-bg-surface border border-border rounded-[10px] p-5 text-center text-sm text-text-muted">
        Noch keine Daten vorhanden.
      </div>
    );
  }

  return (
    <div className="bg-bg-surface border border-border rounded-[10px] p-5">
      <h2 className="text-sm font-semibold text-text mb-4">{label}</h2>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            domain={["auto", "auto"]}
          />
          <Tooltip
            cursor={{ stroke: "rgba(255,255,255,0.08)" }}
            contentStyle={{
              background: "#1c1c26",
              border: "1px solid #2a2a38",
              borderRadius: 8,
              fontSize: 12,
              color: "#e5e7eb",
            }}
            formatter={(v: number) => [`${v} ${unit}`, label]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#10b981"
            strokeWidth={2}
            dot={<Dot r={3} fill="#10b981" />}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
