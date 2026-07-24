import { useState } from "react";
import { api } from "../../api/backend";

const AVATARS = ["🏃", "💪", "🧗", "🚴", "🏋️", "🤸", "⚽", "🎯", "🔥", "⚡", "🦁", "🐯"];

const EQUIPMENT_OPTIONS = [
  { value: "bodyweight", label: "Körpergewicht", icon: "🤸" },
  { value: "dumbbells", label: "Kurzhanteln", icon: "🏋️" },
  { value: "barbell", label: "Langhantel", icon: "⚡" },
  { value: "gym", label: "Fitnessstudio", icon: "🏟️" },
  { value: "cardio", label: "Cardio-Geräte", icon: "🚴" },
];

interface Props {
  onComplete: (name: string) => void;
}

export default function SetupModal({ onComplete }: Props) {
  const [step, setStep] = useState<1 | 2>(1);
  const [saving, setSaving] = useState(false);

  // Step 1 – Basics
  const [avatar, setAvatar] = useState("🏃");
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");

  // Step 2 – Equipment
  const [equipment, setEquipment] = useState<string[]>(["bodyweight"]);

  function toggleEquipment(val: string) {
    setEquipment((prev) =>
      prev.includes(val) ? prev.filter((e) => e !== val) : [...prev, val]
    );
  }

  async function handleFinish() {
    setSaving(true);
    try {
      await api.updateProfile({
        name: name.trim() || null,
        avatar,
        age: age ? parseInt(age) : null,
        gender: gender || null,
        height_cm: height ? parseInt(height) : null,
        weight_kg: weight ? parseFloat(weight) : null,
        equipment,
      });
      onComplete(name.trim() || "");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg/90 backdrop-blur-sm">
      <div className="w-full max-w-md mx-4 bg-bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="px-6 pt-7 pb-4 text-center">
          <div className="text-4xl mb-3">{avatar}</div>
          <h1 className="text-xl font-bold text-text">Willkommen bei FitCoach</h1>
          <p className="text-sm text-text-muted mt-1">
            {step === 1 ? "Sag uns kurz wer du bist." : "Was steht dir zur Verfügung?"}
          </p>

          {/* Step dots */}
          <div className="flex items-center justify-center gap-2 mt-4">
            <div className={`h-1.5 rounded-full transition-all ${step === 1 ? "w-6 bg-accent" : "w-3 bg-border"}`} />
            <div className={`h-1.5 rounded-full transition-all ${step === 2 ? "w-6 bg-accent" : "w-3 bg-border"}`} />
          </div>
        </div>

        <div className="px-6 pb-6 space-y-5">
          {step === 1 ? (
            <>
              {/* Avatar */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Avatar</label>
                <div className="flex flex-wrap gap-2">
                  {AVATARS.map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => setAvatar(emoji)}
                      className={`w-11 h-11 text-2xl rounded-xl transition-all border-2 ${
                        avatar === emoji
                          ? "border-accent bg-accent-subtle scale-110"
                          : "border-transparent bg-bg-hover hover:border-border"
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>

              {/* Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Dein Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="z.B. Max"
                  autoFocus
                  className="w-full bg-bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent transition-colors"
                />
              </div>

              {/* Grid: age + gender */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Alter</label>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    placeholder="Jahre"
                    min={10}
                    max={99}
                    className="w-full bg-bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Geschlecht</label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full bg-bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-text focus:outline-none focus:border-accent transition-colors"
                  >
                    <option value="">—</option>
                    <option value="male">Männlich</option>
                    <option value="female">Weiblich</option>
                    <option value="diverse">Divers</option>
                  </select>
                </div>
              </div>

              {/* Grid: height + weight */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Größe (cm)</label>
                  <input
                    type="number"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    placeholder="cm"
                    min={100}
                    max={250}
                    className="w-full bg-bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Gewicht (kg)</label>
                  <input
                    type="number"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    placeholder="kg"
                    min={30}
                    max={300}
                    step={0.5}
                    className="w-full bg-bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
              </div>

              <button
                onClick={() => setStep(2)}
                disabled={!name.trim()}
                className="w-full py-3 rounded-xl text-sm font-semibold bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-40"
              >
                Weiter →
              </button>
            </>
          ) : (
            <>
              {/* Equipment */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Trainings-Equipment
                </label>
                <p className="text-xs text-text-subtle">
                  Wähle alles aus, was dir zur Verfügung steht.
                </p>
                <div className="space-y-2 mt-2">
                  {EQUIPMENT_OPTIONS.map(({ value, label, icon }) => {
                    const active = equipment.includes(value);
                    return (
                      <button
                        key={value}
                        onClick={() => toggleEquipment(value)}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left ${
                          active
                            ? "border-accent bg-accent-subtle text-accent"
                            : "border-border bg-bg-hover text-text-muted hover:border-text-subtle"
                        }`}
                      >
                        <span className="text-xl">{icon}</span>
                        <span className="text-sm font-medium">{label}</span>
                        {active && <span className="ml-auto text-accent">✓</span>}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex gap-3 pt-1">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-3 rounded-xl text-sm font-semibold border border-border text-text-muted hover:border-text-muted transition-colors"
                >
                  ← Zurück
                </button>
                <button
                  onClick={handleFinish}
                  disabled={saving || equipment.length === 0}
                  className="flex-1 py-3 rounded-xl text-sm font-semibold bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-40"
                >
                  {saving ? "Speichern…" : "Los geht's!"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
