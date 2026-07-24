import type { View } from "../../types";

export interface TutorialStep {
  highlightTab?: View;
  title: string;
  description: string;
  emoji: string;
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    title: "Willkommen bei FitCoach!",
    description: "Lass mich dir kurz zeigen, was du hier alles machen kannst.",
    emoji: "👋",
  },
  {
    highlightTab: "dashboard",
    title: "Dashboard",
    description: "Sieh deine Punkte, deinen Level und deine Aktivitätsübersicht auf einen Blick.",
    emoji: "📊",
  },
  {
    highlightTab: "plan",
    title: "Trainingsplan",
    description: "Hier ist dein persönlicher Plan. Hak Workouts ab und tausch Übungen aus.",
    emoji: "🏋️",
  },
  {
    highlightTab: "progress",
    title: "Fortschritt",
    description: "Verfolge dein Gewicht und deine Leistungsentwicklung mit Diagrammen.",
    emoji: "📈",
  },
  {
    highlightTab: "nutrition",
    title: "Ernährung",
    description: "Personalisierte Ernährungstipps und Mahlzeitenvorschläge passend zu deinem Ziel.",
    emoji: "🥗",
  },
  {
    highlightTab: "profile",
    title: "Profil",
    description: "Passe deinen Namen, Avatar und deine persönlichen Daten an.",
    emoji: "👤",
  },
  {
    highlightTab: "chat",
    title: "Chat mit FitCoach",
    description: "Ich bin immer für dich da. Frag mich alles – von Übungen bis zur Ernährung.",
    emoji: "💬",
  },
];

// Sidebar nav order (must match Sidebar.tsx navItems order)
const NAV_ORDER: View[] = ["chat", "dashboard", "plan", "progress", "nutrition", "profile"];

function getTooltipTop(view: View): number {
  const idx = NAV_ORDER.indexOf(view);
  if (idx === -1) return 200;
  // Sidebar header ~64px, nav top padding 16px, each item ~44px, item center +22px
  return 64 + 16 + idx * 44 + 22 - 60;
}

interface Props {
  step: number;
  onNext: () => void;
  onSkip: () => void;
}

export default function TutorialOverlay({ step, onNext, onSkip }: Props) {
  const current = TUTORIAL_STEPS[step];
  if (!current) return null;

  const isLast = step === TUTORIAL_STEPS.length - 1;
  const hasHighlight = !!current.highlightTab;

  return (
    <>
      {/* Backdrop — click to skip */}
      <div
        className="fixed inset-0 bg-black/55 z-[98]"
        onClick={onSkip}
      />

      {hasHighlight ? (
        /* Sidebar-anchored tooltip */
        <div
          className="fixed z-[100] bg-bg-elevated border border-accent/30 rounded-lg shadow-2xl p-4 w-64"
          style={{ left: 256, top: Math.max(getTooltipTop(current.highlightTab!), 80) }}
          onClick={(e) => e.stopPropagation()}
        >
          <Arrow />
          <CardBody
            current={current}
            step={step}
            total={TUTORIAL_STEPS.length}
            isLast={isLast}
            onNext={onNext}
            onSkip={onSkip}
          />
        </div>
      ) : (
        /* Welcome step — centered card */
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="bg-bg-elevated border border-border rounded-xl shadow-2xl p-6 w-80">
            <CardBody
              current={current}
              step={step}
              total={TUTORIAL_STEPS.length}
              isLast={isLast}
              onNext={onNext}
              onSkip={onSkip}
            />
          </div>
        </div>
      )}
    </>
  );
}

function Arrow() {
  return (
    <div
      className="absolute w-3 h-3 bg-bg-elevated border-l border-b border-accent/30 rotate-45"
      style={{ left: -7, top: 20 }}
    />
  );
}

function CardBody({
  current, step, total, isLast, onNext, onSkip,
}: {
  current: TutorialStep;
  step: number;
  total: number;
  isLast: boolean;
  onNext: () => void;
  onSkip: () => void;
}) {
  return (
    <>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{current.emoji}</span>
        <h3 className="font-semibold text-text text-sm">{current.title}</h3>
      </div>
      <p className="text-xs text-text-muted leading-relaxed mb-4">{current.description}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-subtle">{step + 1} / {total}</span>
        <div className="flex gap-2">
          <button
            onClick={onSkip}
            className="text-xs text-text-subtle hover:text-text-muted px-2 py-1 transition-colors"
          >
            Überspringen
          </button>
          <button
            onClick={onNext}
            className="text-xs bg-accent text-white px-3 py-1 rounded font-medium hover:opacity-90 transition-opacity"
          >
            {isLast ? "Los geht's! 🚀" : "Weiter →"}
          </button>
        </div>
      </div>
    </>
  );
}
