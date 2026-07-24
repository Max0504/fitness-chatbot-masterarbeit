from typing import List, Dict, Optional

# ── Wochentag-Verteilung ──────────────────────────────────────────────────────
DAY_SCHEDULES = {
    1: [3],
    2: [1, 4],
    3: [1, 3, 5],
    4: [1, 2, 4, 5],
    5: [1, 2, 3, 5, 6],
    6: [1, 2, 3, 4, 5, 6],
    7: [1, 2, 3, 4, 5, 6, 7],
}

# ── Phasen-Definitionen je Ziel ───────────────────────────────────────────────
PHASES = {
    "muscle_gain": {
        1: {"name": "Grundaufbau",  "desc": "Bewegungsabläufe lernen und Grundkraft aufbauen. Fokus auf saubere Technik."},
        2: {"name": "Progression",  "desc": "Gewicht steigern, Volumen erhöhen. Jetzt wird's intensiver — du spürst die ersten Ergebnisse!"},
        3: {"name": "Peak & Deload", "desc": "Maximale Intensität mit höchstem Volumen, gefolgt von gezieltem Deload für optimale Superkompensation."},
    },
    "weight_loss": {
        1: {"name": "Aktivierung",    "desc": "Stoffwechsel ankurbeln und Grundausdauer aufbauen. Bewegung zur Gewohnheit machen."},
        2: {"name": "Intensivierung", "desc": "Mehr Volumen, höhere Herzfrequenz. Kalorienverbrauch maximieren und Kraft aufbauen."},
        3: {"name": "Peak & Reset",   "desc": "Maximale Intensität gefolgt von gezielter Erholung. Die letzten Reserven aktivieren."},
    },
    "general_fitness": {
        1: {"name": "Basis",      "desc": "Solide Grundlage schaffen. Technik, Stabilität und Ausdauer aufbauen."},
        2: {"name": "Steigerung", "desc": "Volumen und Intensität erhöhen. Spürbare Verbesserungen in Kraft und Kondition!"},
        3: {"name": "Konsolidierung", "desc": "Erreichte Fitness festigen und weiter ausbauen. Komplexere Bewegungen und höhere Gesamtbelastung."},
    },
    "endurance": {
        1: {"name": "Ausdauer-Basis", "desc": "Aerobe Grundlage aufbauen, Herzfrequenz regulieren. Lange, moderate Einheiten."},
        2: {"name": "Aufbau",         "desc": "Längere und schnellere Einheiten. Ausdauerkapazität systematisch steigern."},
        3: {"name": "Peak",           "desc": "Maximale Ausdauerleistung. Anschließend Tapering für optimale Regeneration."},
    },
    "strength": {
        1: {"name": "Technik & Basis",  "desc": "Grundhebungen lernen und Technik festigen. Moderate Lasten, saubere Ausführung."},
        2: {"name": "Kraft-Aufbau",     "desc": "Gewichte progressiv steigern. 3–5 Wiederholungen mit maximaler Kontrolle."},
        3: {"name": "Peak & Deload",    "desc": "Maximale Lasten bei niedrigem Volumen, dann gezielter Deload für Superkompensation."},
    },
}

# ── Wöchentliche Progression (Sets / Reps / Pause) je Ziel ───────────────────
WEEKLY_PROGRESSIONS = {
    "muscle_gain": [
        {"week": 1, "sets": 3, "reps": 12, "rest": 75,  "phase": 1},
        {"week": 2, "sets": 4, "reps": 10, "rest": 90,  "phase": 1},
        {"week": 3, "sets": 4, "reps": 8,  "rest": 90,  "phase": 2},
        {"week": 4, "sets": 5, "reps": 6,  "rest": 120, "phase": 2},
        {"week": 5, "sets": 5, "reps": 5,  "rest": 120, "phase": 3},
        {"week": 6, "sets": 3, "reps": 10, "rest": 75,  "phase": 3},
    ],
    "weight_loss": [
        {"week": 1, "sets": 3, "reps": 15, "rest": 45, "phase": 1},
        {"week": 2, "sets": 3, "reps": 15, "rest": 40, "phase": 1},
        {"week": 3, "sets": 4, "reps": 15, "rest": 45, "phase": 2},
        {"week": 4, "sets": 4, "reps": 12, "rest": 40, "phase": 2},
        {"week": 5, "sets": 4, "reps": 15, "rest": 30, "phase": 3},
        {"week": 6, "sets": 3, "reps": 12, "rest": 45, "phase": 3},
    ],
    "general_fitness": [
        {"week": 1, "sets": 3, "reps": 12, "rest": 60, "phase": 1},
        {"week": 2, "sets": 3, "reps": 12, "rest": 55, "phase": 1},
        {"week": 3, "sets": 4, "reps": 12, "rest": 60, "phase": 2},
        {"week": 4, "sets": 4, "reps": 10, "rest": 55, "phase": 2},
        {"week": 5, "sets": 4, "reps": 10, "rest": 50, "phase": 3},
        {"week": 6, "sets": 3, "reps": 12, "rest": 60, "phase": 3},
    ],
    "endurance": [
        {"week": 1, "sets": 3, "reps": 20, "rest": 40, "phase": 1},
        {"week": 2, "sets": 3, "reps": 20, "rest": 35, "phase": 1},
        {"week": 3, "sets": 4, "reps": 20, "rest": 30, "phase": 2},
        {"week": 4, "sets": 4, "reps": 20, "rest": 25, "phase": 2},
        {"week": 5, "sets": 4, "reps": 20, "rest": 25, "phase": 3},
        {"week": 6, "sets": 3, "reps": 15, "rest": 35, "phase": 3},
    ],
    "strength": [
        {"week": 1, "sets": 3, "reps": 6,  "rest": 150, "phase": 1},
        {"week": 2, "sets": 4, "reps": 5,  "rest": 150, "phase": 1},
        {"week": 3, "sets": 4, "reps": 4,  "rest": 180, "phase": 2},
        {"week": 4, "sets": 5, "reps": 3,  "rest": 180, "phase": 2},
        {"week": 5, "sets": 5, "reps": 3,  "rest": 180, "phase": 3},
        {"week": 6, "sets": 3, "reps": 5,  "rest": 120, "phase": 3},
    ],
}

PLAN_NAMES = {
    "muscle_gain":      "Muskelaufbau-Plan",
    "weight_loss":      "Abnehm-Plan",
    "general_fitness":  "Fitness-Plan",
    "endurance":        "Ausdauer-Plan",
    "endurance_running": "Lauf-Plan",
    "endurance_cycling": "Rad-Ausdauer-Plan",
    "endurance_mixed":   "Ausdauer-Plan (Laufen & Radfahren)",
    "strength":         "Kraft-Plan",
}


def _endurance_subtype(specific_goal: str) -> str:
    """Detect endurance subtype from specific_goal text."""
    if not specific_goal:
        return "endurance"
    sg = specific_goal.lower()
    if any(kw in sg for kw in ("radfahren", "fahrrad", "cycling", "rad", "bike", "rennrad", "mountainbike")):
        return "endurance_cycling"
    if any(kw in sg for kw in ("gemischt", "beides", "mixed", "kombiniert", "combined")):
        return "endurance_mixed"
    if any(kw in sg for kw in ("laufen", "joggen", "running", "lauf")):
        return "endurance_running"
    return "endurance"

# ── Fallback-Tagesstruktur je Ziel ────────────────────────────────────────────
# Verwendet wenn Gemini nicht verfügbar ist. Übungen als reiner Freitext, kein exercises.json.
# 7 Einträge je Ziel — für bis zu 7 Trainingstage pro Woche.

_FALLBACK_SPLITS: Dict[str, List[Dict]] = {
    "muscle_gain": [
        {"name": "Push A",          "exercises": ["Bankdrücken", "Schulterdrücken", "Dips", "Schrägbankdrücken", "Trizeps-Dips"]},
        {"name": "Pull A",          "exercises": ["Klimmzüge", "Langhantelrudern", "Latziehen", "Bizepscurls", "Face Pulls"]},
        {"name": "Beine & Core",    "exercises": ["Kniebeugen", "Rumänisches Kreuzheben", "Ausfallschritte", "Beinpresse", "Wadenheben"]},
        {"name": "Push B",          "exercises": ["Schrägbank Hanteln", "Seitheben", "Liegestütze", "Trizeps-Kickback", "Schulterdrücken Hanteln"]},
        {"name": "Pull B",          "exercises": ["Einarmiges Rudern", "Hammer Curls", "Klimmzüge Untergriff", "Reverse Flyes", "Kabelrudern"]},
        {"name": "Beine B",         "exercises": ["Front Squats", "Ausfallschritte rückwärts", "Beinbeuger", "Sumo-Kniebeugen", "Plank"]},
        {"name": "Aktive Erholung", "exercises": ["Foam Rolling 15 Min", "Hüftflexoren-Dehnung", "Schulter-Mobilisation", "Leichtes Gehen 20 Min"]},
    ],
    "weight_loss": [
        {"name": "Kraft Oberkörper",  "exercises": ["Liegestütze", "Kurzhantel-Rudern", "Schulterdrücken", "Trizeps-Dips", "Bizepscurls"]},
        {"name": "HIIT Intervall",    "exercises": ["Burpees 8×30s", "High Knees 8×40s", "Jump Squats 6×30s", "Mountain Climbers 6×40s", "Box Jumps 4×10"]},
        {"name": "Kraft Unterkörper", "exercises": ["Kniebeugen", "Ausfallschritte", "Glutebrücken", "Beinbeuger", "Wadenheben"]},
        {"name": "Cardio HIIT",       "exercises": ["Seilspringen 3×5 Min", "Burpees 3×10", "Laufen 20 Min zügig", "Mountain Climbers 3×20", "Jump Squats 3×15"]},
        {"name": "Ganzkörper Kraft",  "exercises": ["Kreuzheben", "Bankdrücken", "Kniebeugen", "Langhantelrudern", "Plank"]},
        {"name": "Cardio + Core",     "exercises": ["Laufen 30 Min locker", "Plank 3×45s", "Russian Twists 3×20", "Leg Raises 3×15", "Seitstütz 3×30s"]},
        {"name": "Aktive Erholung",   "exercises": ["Yoga-Flow 20 Min", "Ganzkörper-Dehnen 15 Min", "Spaziergang 30 Min"]},
    ],
    "general_fitness": [
        {"name": "Oberkörper",          "exercises": ["Liegestütze", "Kurzhantel-Rudern", "Schulterdrücken", "Klimmzüge", "Plank"]},
        {"name": "Cardio + Core",       "exercises": ["Laufen 30 Min locker", "Plank 3×30s", "Russian Twists 3×15", "Crunch 3×20", "Seilspringen 5 Min"]},
        {"name": "Unterkörper + Kraft", "exercises": ["Kniebeugen", "Ausfallschritte", "Glutebrücken", "Wadenheben", "Seitstütz"]},
        {"name": "Ganzkörper",          "exercises": ["Burpees 3×10", "Kniebeugen 3×15", "Liegestütze 3×10", "Kurzhantel-Rudern 3×10", "Plank 3×30s"]},
        {"name": "Oberkörper B",        "exercises": ["Bankdrücken", "Latziehen", "Seitheben", "Trizeps-Dips", "Bizepscurls"]},
        {"name": "Unterkörper B",       "exercises": ["Sumo-Kniebeugen", "Ausfallschritte seitlich", "Beinpresse", "Glutebrücken", "Wadenheben"]},
        {"name": "Aktive Erholung",     "exercises": ["Spaziergang 30 Min", "Ganzkörper-Dehnen 15 Min", "Leichtes Radfahren"]},
    ],
    "endurance": [
        {"name": "Cardio Intervall",    "exercises": ["Einlaufen 5 Min locker", "8×(1 Min schnell / 2 Min locker) Laufen", "Auslaufen 5 Min", "Dehnen Beine 5 Min"]},
        {"name": "Kraft + Core",        "exercises": ["Kniebeugen 3×15", "Ausfallschritte 3×12", "Glutebrücken 3×20", "Plank 3×45s", "Seitstütz 3×30s"]},
        {"name": "Langer Lauf",         "exercises": ["Einlaufen 5 Min", "40 Min ruhiges Dauerlauftempo (Zone 2)", "Auslaufen 5 Min", "Dehnen 5 Min"]},
        {"name": "Tempolauf",           "exercises": ["Einlaufen 5 Min", "20 Min zügiges Tempo", "Auslaufen 5 Min", "Dehnübungen 5 Min"]},
        {"name": "Kraft Unterkörper",   "exercises": ["Einbeinige Kniebeugen 3×8", "Step-ups 3×12", "Wadenheben einbeinig 3×15", "Glutebrücken 3×20", "Plank 3×30s"]},
        {"name": "Kraft Ganzkörper",    "exercises": ["Liegestütze 3×15", "Klimmzüge 3×8", "Langhantelrudern 3×12", "Kniebeugen 3×15", "Plank 3×45s"]},
        {"name": "Aktive Erholung",     "exercises": ["Leichtes Joggen 20 Min", "Yoga 15 Min", "Dehnen Beine und Hüfte"]},
    ],
    "endurance_running": [
        {"name": "Lauf-Intervall",      "exercises": ["Einlaufen 5 Min locker", "8×(1 Min schnell / 2 Min locker)", "Auslaufen 5 Min", "Beinedehnen 5 Min"]},
        {"name": "Lauf-Kraft Core",     "exercises": ["Kniebeugen 3×15", "Ausfallschritte 3×12", "Glutebrücken 3×20", "Plank 3×45s", "Seitstütz 3×30s"]},
        {"name": "Langer Lauf",         "exercises": ["Einlaufen 5 Min", "40 Min Zone-2-Dauerlauf", "Auslaufen 5 Min", "Dehnen 5 Min"]},
        {"name": "Tempolauf",           "exercises": ["Einlaufen 5 Min", "20 Min zügiges Tempo", "Auslaufen 5 Min", "Dehnübungen 5 Min"]},
        {"name": "Kraft Beine",         "exercises": ["Einbeinige Kniebeugen 3×8", "Step-ups 3×12", "Wadenheben einbeinig 3×15", "Glutebrücken 3×20", "Plank 3×30s"]},
        {"name": "Fahrtspiel",          "exercises": ["Einlaufen 5 Min", "Fartlek 25 Min (freie Tempowechsel)", "Auslaufen 5 Min", "Dehnen 5 Min"]},
        {"name": "Aktive Erholung",     "exercises": ["Leichtes Joggen 20 Min", "Yoga 15 Min", "Bein- und Hüftdehnung"]},
    ],
    "endurance_cycling": [
        {"name": "Rad-Intervall",       "exercises": ["Einrollen 5 Min", "6×(3 Min hohes Tempo / 2 Min locker) Radfahren", "Ausrollen 5 Min", "Beinedehnen 5 Min"]},
        {"name": "Rad-Kraft Core",      "exercises": ["Kniebeugen 3×15", "Ausfallschritte 3×12", "Glutebrücken 3×20", "Plank 3×45s", "Wadenheben 3×20"]},
        {"name": "Lange Ausfahrt",      "exercises": ["Einrollen 5 Min", "50 Min ruhige Ausfahrt (Zone 2)", "Ausrollen 5 Min", "Stretching 5 Min"]},
        {"name": "Tempo-Ausfahrt",      "exercises": ["Einrollen 5 Min", "25 Min zügiges Tempo auf dem Rad", "Ausrollen 5 Min", "Beinedehnen 5 Min"]},
        {"name": "Kraft Beine",         "exercises": ["Einbeinige Kniebeugen 3×8", "Step-ups 3×12", "Wadenheben einbeinig 3×15", "Glutebrücken 3×20", "Plank 3×30s"]},
        {"name": "Rad-Hügel",           "exercises": ["Einrollen 5 Min", "5×(3 Min Bergauf-Widerstand hoch / 2 Min locker)", "Ausrollen 5 Min", "Stretching 5 Min"]},
        {"name": "Aktive Erholung",     "exercises": ["Leichtes Radfahren 20 Min", "Yoga 15 Min", "Bein- und Hüftdehnung"]},
    ],
    "endurance_mixed": [
        {"name": "Lauf-Intervall",      "exercises": ["Einlaufen 5 Min locker", "6×(2 Min schnell / 2 Min locker) Laufen", "Auslaufen 5 Min", "Dehnen 5 Min"]},
        {"name": "Rad-Ausdauer",        "exercises": ["Einrollen 5 Min", "40 Min ruhige Ausfahrt Zone 2", "Ausrollen 5 Min", "Stretching 5 Min"]},
        {"name": "Lauf-Kraft Core",     "exercises": ["Kniebeugen 3×15", "Ausfallschritte 3×12", "Glutebrücken 3×20", "Plank 3×45s", "Seitstütz 3×30s"]},
        {"name": "Langer Lauf",         "exercises": ["Einlaufen 5 Min", "35 Min Zone-2-Dauerlauf", "Auslaufen 5 Min", "Dehnen 5 Min"]},
        {"name": "Rad-Intervall",       "exercises": ["Einrollen 5 Min", "5×(3 Min Widerstand hoch / 2 Min locker)", "Ausrollen 5 Min", "Beinedehnen 5 Min"]},
        {"name": "Kraft Beine",         "exercises": ["Einbeinige Kniebeugen 3×8", "Step-ups 3×12", "Wadenheben einbeinig 3×15", "Glutebrücken 3×20", "Plank 3×30s"]},
        {"name": "Aktive Erholung",     "exercises": ["Leichtes Joggen oder Radfahren 20 Min", "Yoga 15 Min", "Bein- und Hüftdehnung"]},
    ],
    "strength": [
        {"name": "Kniebeugen-Tag",    "exercises": ["Kniebeugen", "Rumänisches Kreuzheben", "Beinpresse", "Wadenheben", "Plank"]},
        {"name": "Bankdrücken-Tag",   "exercises": ["Bankdrücken", "Schrägbankdrücken", "Schulterdrücken", "Trizeps-Dips", "Seitheben"]},
        {"name": "Kreuzheben-Tag",    "exercises": ["Kreuzheben", "Klimmzüge", "Langhantelrudern", "Bizepscurls", "Plank"]},
        {"name": "Schulter & Rücken", "exercises": ["Schulterdrücken", "Langhantelrudern", "Klimmzüge", "Face Pulls", "Bizepscurls"]},
        {"name": "Kniebeugen B",      "exercises": ["Front Squats", "Ausfallschritte", "Beinbeuger", "Wadenheben", "Core-Rotation"]},
        {"name": "Bankdrücken B",     "exercises": ["Enge Griffweite Bankdrücken", "Schrägbank Hanteln", "Dips", "Trizeps-Kickback", "Seitheben"]},
        {"name": "Aktive Erholung",   "exercises": ["Foam Rolling 15 Min", "Hüft-Mobilisation", "Schulter-Dehnung", "Leichtes Gehen 20 Min"]},
    ],
}

_CARDIO_KEYWORDS = (
    "min", "laufen", "joggen", "radfahren", "spaziergang",
    "yoga", "dehnen", "foam", "tempo", "seilspringen",
    "lauf", "einlaufen", "auslaufen", "intervall",
    "einrollen", "ausrollen", "ausfahrt", "ausfahren", "zone",
)


def _build_fallback_exercises(day_template: Dict, sets: int, reps: int, rest: int) -> List[Dict]:
    exercises = []
    for name in day_template["exercises"]:
        is_cardio = any(kw in name.lower() for kw in _CARDIO_KEYWORDS)
        exercises.append({
            "exercise_id": None,
            "name": name,
            "sets": 1 if is_cardio else sets,
            "reps": None if is_cardio else reps,
            "rest_sec": 0 if is_cardio else rest,
            "type": "cardio" if is_cardio else "strength",
            "duration_min": None,
            "description": None,
        })
    return exercises


# ── Gemini-Validierung & Normalisierung ───────────────────────────────────────

def _validate_gemini_plan(data: dict, expected_days: int, expected_weeks: int) -> bool:
    if not isinstance(data, dict):
        return False
    workouts = data.get("workouts")
    if not workouts or not isinstance(workouts, list):
        return False
    weeks_found = {w.get("week_number") for w in workouts if isinstance(w, dict)}
    if len(weeks_found) < max(1, expected_weeks - 1):
        return False
    first_week = [w for w in workouts if w.get("week_number") == 1]
    if len(first_week) < expected_days:
        return False
    for w in workouts[:3]:
        if len(w.get("exercises") or []) < 3:
            return False
    return True


def _normalize_gemini_plan(data: dict, goal: str, days: int) -> dict:
    for workout in data.get("workouts", []):
        for ex in workout.get("exercises", []):
            ex["exercise_id"] = None
            ex.setdefault("type", "strength")
            ex.setdefault("duration_min", None)
            ex.setdefault("description", None)
            try:
                ex["sets"] = int(ex.get("sets") or 3)
            except (ValueError, TypeError):
                ex["sets"] = 3
            try:
                ex["reps"] = int(ex["reps"]) if ex.get("reps") is not None else None
            except (ValueError, TypeError):
                ex["reps"] = None
            try:
                ex["rest_sec"] = int(ex.get("rest_sec") or 60)
            except (ValueError, TypeError):
                ex["rest_sec"] = 60
    data["goal"] = goal
    data.setdefault("name", PLAN_NAMES.get(goal, "Trainingsplan"))
    first_week_days = {w.get("day_of_week") for w in data.get("workouts", []) if w.get("week_number") == 1}
    data["workouts_per_week"] = len(first_week_days) or days
    return data


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def generate_plan(profile: dict) -> dict:
    """Generiert Trainingsplan algorithmisch (schnell, kein LLM-Aufruf)."""
    return _generate_plan_algorithmic(profile)


def _generate_plan_algorithmic(profile: dict) -> dict:
    """Einfacher Fallback ohne externes Übungskatalog — reine Freitext-Übungen."""
    goal = profile.get("goal") or "general_fitness"
    specific_goal = profile.get("specific_goal") or ""
    days = max(1, min(7, int(profile.get("days_per_week") or 3)))

    # Endurance: detect subtype and use specialised splits/names
    if goal == "endurance":
        subtype = _endurance_subtype(specific_goal)
        splits_key = subtype if subtype in _FALLBACK_SPLITS else "endurance"
    else:
        subtype = goal
        splits_key = goal

    progressions = WEEKLY_PROGRESSIONS.get(goal, WEEKLY_PROGRESSIONS["general_fitness"])
    duration_weeks = len(progressions)
    day_schedule = DAY_SCHEDULES.get(days, DAY_SCHEDULES[3])

    # Phasen-Metadaten
    phase_map: Dict[int, Dict] = {}
    phase_weeks: Dict[int, list] = {}
    for prog in progressions:
        pn = prog["phase"]
        if pn not in phase_map:
            phase_map[pn] = PHASES.get(goal, {}).get(pn, {"name": f"Phase {pn}", "desc": ""})
            phase_weeks[pn] = []
        phase_weeks[pn].append(prog["week"])

    phases_meta = [
        {
            "phase_number": pn,
            "name": phase_map[pn]["name"],
            "desc": phase_map[pn]["desc"],
            "weeks": phase_weeks[pn],
        }
        for pn in sorted(phase_map.keys())
    ]

    splits = _FALLBACK_SPLITS.get(splits_key, _FALLBACK_SPLITS.get(goal, _FALLBACK_SPLITS["general_fitness"]))

    # Filter "Aktive Erholung" aus Rotation heraus (nur für 7-Tage-Pläne)
    active_splits = [s for s in splits if "erholung" not in s["name"].lower()]
    if days == 7:
        active_splits = splits  # Recovery-Tag bleibt bei 7 Tagen

    workouts = []
    for prog in progressions:
        week_num = prog["week"]
        phase_num = prog["phase"]
        sets, reps, rest = prog["sets"], prog["reps"], prog["rest"]
        phase_name_str = phase_map[phase_num]["name"]

        # Jede Phase bekommt einen anderen Startindex → andere Übungen pro Phase
        phase_offset = (phase_num - 1) % len(active_splits)
        day_templates_phase = [
            active_splits[(phase_offset + i) % len(active_splits)]
            for i in range(days)
        ]

        for idx, day_tmpl in enumerate(day_templates_phase):
            actual_day = day_schedule[idx] if idx < len(day_schedule) else idx + 1
            exercises = _build_fallback_exercises(day_tmpl, sets, reps, rest)
            workouts.append({
                "week_number": week_num,
                "day_of_week": actual_day,
                "name": day_tmpl["name"],
                "phase_number": phase_num,
                "phase_name": phase_name_str,
                "exercises": exercises,
            })

    return {
        "name": PLAN_NAMES.get(subtype, PLAN_NAMES.get(goal, "Trainingsplan")),
        "goal": goal,
        "duration_weeks": duration_weeks,
        "phases": phases_meta,
        "workouts_per_week": days,
        "workouts": workouts,
    }
