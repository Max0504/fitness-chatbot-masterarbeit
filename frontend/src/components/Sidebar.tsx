import { MessageCircle, LayoutDashboard, Dumbbell, TrendingUp, Salad, User } from "lucide-react";
import { useEffect, useState } from "react";
import type { View } from "../types";
import { api } from "../api/backend";

interface Props {
  current: View;
  onChange: (v: View) => void;
  refreshKey: number;
  tutorialHighlightTab?: View;
}

const navItems: { view: View; label: string; Icon: React.ElementType }[] = [
  { view: "chat",      label: "Chat",         Icon: MessageCircle },
  { view: "dashboard", label: "Dashboard",    Icon: LayoutDashboard },
  { view: "plan",      label: "Trainingsplan", Icon: Dumbbell },
  { view: "progress",   label: "Fortschritt",  Icon: TrendingUp },
  { view: "nutrition",  label: "Ernährung",    Icon: Salad },
  { view: "profile",    label: "Profil",       Icon: User },
];

export default function Sidebar({ current, onChange, refreshKey, tutorialHighlightTab }: Props) {
  const [levelLabel, setLevelLabel] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<{ name: string | null; avatar: string | null }>({ name: null, avatar: null });

  useEffect(() => {
    api.getDashboard().then((d) => setLevelLabel(`${d.level.icon} ${d.level.name}`)).catch(() => {});
    api.getProfile().then((p) => setUserInfo({ name: p.name, avatar: p.avatar })).catch(() => {});
  }, [refreshKey]);

  return (
    <aside className="flex flex-col w-60 shrink-0 h-full bg-bg-elevated border-r border-border">
      <div className="px-6 py-5 border-b border-border">
        <span className="text-lg font-bold text-accent tracking-tight">FitCoach</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ view, label, Icon }) => {
          const active = current === view;
          return (
            <button
              key={view}
              onClick={() => onChange(view)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded text-sm font-medium transition-colors ${
                active
                  ? "bg-accent-subtle text-accent"
                  : "text-text-muted hover:bg-bg-hover hover:text-text"
              } ${tutorialHighlightTab === view ? "relative z-[99] ring-2 ring-accent shadow-lg shadow-accent/20" : ""}`}
            >
              <Icon size={18} />
              {label}
            </button>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-border flex items-center gap-2.5">
        <span className="text-2xl">{userInfo.avatar ?? "🏃"}</span>
        <div className="text-xs text-text-subtle leading-tight">
          <div className="font-medium text-text-muted">{userInfo.name ?? "Demo User"}</div>
          <div>{levelLabel ?? "…"}</div>
        </div>
      </div>
    </aside>
  );
}
