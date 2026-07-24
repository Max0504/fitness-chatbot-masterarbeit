import type { LucideIcon } from "lucide-react";

interface Props {
  icon: LucideIcon;
  label: string;
  value: string | number;
  sub?: string;
  progress?: { value: number; max: number };
}

export default function StatsCard({ icon: Icon, label, value, sub, progress }: Props) {
  return (
    <div className="bg-bg-surface border border-border rounded-[10px] p-5 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-[8px] bg-accent-subtle flex items-center justify-center shrink-0">
          <Icon size={18} className="text-accent" />
        </div>
        <span className="text-xs font-medium text-text-muted uppercase tracking-wide">{label}</span>
      </div>
      <div>
        <span className="text-3xl font-bold text-text">{value}</span>
        {sub && <span className="text-sm text-text-muted ml-2">{sub}</span>}
      </div>
      {progress && (
        <div>
          <div className="h-1.5 bg-bg-hover rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all"
              style={{ width: `${Math.min(100, (progress.value / progress.max) * 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-text-subtle mt-1">{progress.value} / {progress.max} zum nächsten Level</p>
        </div>
      )}
    </div>
  );
}
