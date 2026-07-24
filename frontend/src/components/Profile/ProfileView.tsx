import { useEffect, useState } from "react";
import { api } from "../../api/backend";
import type { Profile } from "../../types";

const EQUIPMENT_OPTIONS = [
  { value: "bodyweight", label: "Körpergewicht" },
  { value: "dumbbells", label: "Kurzhanteln" },
  { value: "barbell", label: "Langhantel" },
  { value: "gym", label: "Fitnessstudio" },
  { value: "cardio", label: "Cardio-Geräte" },
];

const GOAL_LABELS: Record<string, string> = {
  muscle_gain: "Muskelaufbau",
  weight_loss: "Gewichtsabnahme",
  general_fitness: "Allgemeine Fitness",
  endurance: "Ausdauer",
  strength: "Kraft",
};

const LEVEL_LABELS: Record<string, string> = {
  beginner: "Anfänger",
  intermediate: "Fortgeschritten",
  advanced: "Erfahren",
};

const AVATARS = ["🏃", "💪", "🧗", "🚴", "🏋️", "🤸", "⚽", "🎯", "🔥", "⚡", "🦁", "🐯"];

export default function ProfileView({ onSaved }: { onSaved?: () => void }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(false);

  const [name, setName] = useState("");
  const [avatar, setAvatar] = useState("🏃");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [equipment, setEquipment] = useState<string[]>([]);

  useEffect(() => {
    api.getProfile().then((p) => {
      setProfile(p);
      setName(p.name ?? "");
      setAvatar(p.avatar ?? "🏃");
      setAge(p.age?.toString() ?? "");
      setGender(p.gender ?? "");
      setHeight(p.height_cm?.toString() ?? "");
      setWeight(p.weight_kg?.toString() ?? "");
      setEquipment(p.equipment ?? []);
    }).catch(() => setError(true));
  }, []);

  function toggleEquipment(val: string) {
    setEquipment((prev) =>
      prev.includes(val) ? prev.filter((e) => e !== val) : [...prev, val]
    );
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await api.updateProfile({
        name: name || null,
        avatar,
        age: age ? parseInt(age) : null,
        gender: gender || null,
        height_cm: height ? parseInt(height) : null,
        weight_kg: weight ? parseFloat(weight) : null,
        equipment,
      });
      setSaved(true);
      onSaved?.();
      window.dispatchEvent(new CustomEvent("weight_updated"));
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return <div className="flex items-center justify-center h-full text-text-muted text-sm">Profil konnte nicht geladen werden.</div>;
  }
  if (!profile) {
    return <div className="flex items-center justify-center h-full text-text-muted text-sm">Lade Profil…</div>;
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-6">
      <h1 className="text-xl font-bold text-text mb-1">Profil</h1>
      <p className="text-xs text-text-subtle mb-6">Trainingsziel, Level und Wochentage setzt du im Chat.</p>

      <div className="max-w-lg space-y-5">

        {/* Avatar */}
        <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-3">
          <h2 className="text-sm font-semibold text-text">Avatar</h2>
          <div className="flex flex-wrap gap-2">
            {AVATARS.map((emoji) => (
              <button
                key={emoji}
                onClick={() => setAvatar(emoji)}
                className={`w-11 h-11 text-2xl rounded-[10px] transition-all border-2 ${
                  avatar === emoji
                    ? "border-accent bg-accent-subtle scale-110"
                    : "border-transparent bg-bg-hover hover:border-border"
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </section>

        {/* Name */}
        <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-3">
          <h2 className="text-sm font-semibold text-text">Name</h2>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Dein Name"
            className="w-full bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
          />
        </section>

        {/* Read-only training info */}
        {profile.onboarded && (
          <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-3">
            <h2 className="text-sm font-semibold text-text">Trainingsprofil</h2>
            <div className="grid grid-cols-3 gap-3">
              <ReadField label="Ziel" value={GOAL_LABELS[profile.goal ?? ""] ?? profile.goal ?? "—"} />
              <ReadField label="Level" value={LEVEL_LABELS[profile.fitness_level ?? ""] ?? profile.fitness_level ?? "—"} />
              <ReadField label="Tage/Woche" value={profile.days_per_week?.toString() ?? "—"} />
            </div>
            {profile.specific_goal && (
              <p className="text-xs text-text-subtle pt-1 border-t border-border">{profile.specific_goal}</p>
            )}
          </section>
        )}

        {/* Body data */}
        <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-4">
          <h2 className="text-sm font-semibold text-text">Körperdaten</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Alter" type="number" value={age} onChange={setAge} placeholder="Jahre" />
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-text-muted">Geschlecht</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text focus:outline-none focus:border-accent"
              >
                <option value="">—</option>
                <option value="male">Männlich</option>
                <option value="female">Weiblich</option>
                <option value="diverse">Divers</option>
              </select>
            </div>
            <Field label="Größe (cm)" type="number" value={height} onChange={setHeight} placeholder="cm" />
            <Field label="Gewicht (kg)" type="number" value={weight} onChange={setWeight} placeholder="kg" step="0.5" />
          </div>
        </section>

        {/* Equipment */}
        <section className="bg-bg-surface border border-border rounded-[10px] p-5 space-y-3">
          <h2 className="text-sm font-semibold text-text">Equipment</h2>
          <p className="text-xs text-text-subtle">Wird bei der nächsten Plan-Erstellung berücksichtigt.</p>
          <div className="flex flex-wrap gap-2">
            {EQUIPMENT_OPTIONS.map(({ value, label }) => {
              const active = equipment.includes(value);
              return (
                <button
                  key={value}
                  onClick={() => toggleEquipment(value)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                    active
                      ? "bg-accent-subtle border-accent text-accent"
                      : "border-border text-text-muted hover:border-text-muted"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </section>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-3 rounded-[10px] text-sm font-semibold bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-50"
        >
          {saved ? "Gespeichert ✓" : saving ? "Speichern…" : "Speichern"}
        </button>
      </div>
    </div>
  );
}

function ReadField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-sm text-text font-medium">{value}</span>
    </div>
  );
}

function Field({ label, type, value, onChange, placeholder, step }: {
  label: string; type: string; value: string;
  onChange: (v: string) => void; placeholder?: string; step?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs text-text-muted">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        step={step}
        className="bg-bg-hover border border-border rounded-[8px] px-3 py-2 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent"
      />
    </div>
  );
}
