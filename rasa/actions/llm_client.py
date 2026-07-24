"""
LLM Client — aktuell Google Gemini (google-generativeai SDK).
Diese Datei ist die einzige, die provider-spezifischen Code enthält.
Wechsel zu Anthropic/OpenAI/Ollama: nur diese Datei tauschen.
Die öffentliche Funktion heißt überall ask_llm(), nicht ask_gemini().
"""
import os
import time
import json
from pathlib import Path
from typing import Optional, List, Dict

LOG_PATH = Path(__file__).parent.parent.parent / "data" / "logs"

_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
_configured = False


def _configure():
    global _configured
    if _configured:
        return True
    # .env explizit laden falls nicht schon in der Umgebung
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH, override=False)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    _configured = True
    return True


MODEL = os.environ.get("LLM_MODEL", "models/gemini-3.1-flash-lite")

SYSTEM_PROMPT_BASE = """Du bist ein freundlicher, motivierender und kompetenter Fitness-Coach für eine Web-App.
Du kommunizierst auf Deutsch, in einem lockeren, ermutigenden Ton (du-Form).
Du gibst keine medizinischen Diagnosen. Bei Anzeichen von Verletzungen oder Schmerzen empfiehlst du einen Arzt.
Antworte präzise und nicht zu lang (max. 4-5 Sätze für die meisten Fragen, längere Antworten nur wenn der User es will).
Verwende ab und zu Emojis.
Du bist Teil eines Hybrid-Systems: Strukturierte Aufgaben (Plan-Erstellung, Tracking, Begrüßungen) macht eine andere Komponente (Rasa). Du bist für Übungs-Erklärungen, Motivation, Ernährung und freie Konversation zuständig."""


def ask_llm(
    user_message: str,
    system_extra: str = "",
    user_context: Optional[Dict] = None,
    history: Optional[List[Dict]] = None,
    max_tokens: int = 600,
    timeout_sec: int = 50,
) -> str:
    """Generischer LLM-Call mit User-Kontext und Konversations-Historie.

    history: Liste von {"role": "user"|"assistant", "content": "..."}
    timeout_sec: Maximale Wartezeit in Sekunden (50s < Rasa-Timeout 60s).
    """
    if not _configure():
        return "GEMINI_API_KEY ist nicht gesetzt — bitte .env-Datei anlegen. Siehe .env.example."

    import google.generativeai as genai

    # System-Prompt zusammenbauen
    system = SYSTEM_PROMPT_BASE
    if user_context:
        system += "\n\nUser-Kontext:\n"
        for k, v in user_context.items():
            if v is not None:
                system += f"- {k}: {v}\n"
    if system_extra:
        system += "\n\n" + system_extra

    # Konversationshistorie (Gemini erwartet "user"/"model" als Rollen)
    contents = []
    if history:
        for msg in history[-16:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [msg["content"]]})
    contents.append({"role": "user", "parts": [user_message]})

    t_start = time.time()
    try:
        model = genai.GenerativeModel(
            MODEL,
            system_instruction=system,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        response = model.generate_content(
            contents,
            request_options={"timeout": timeout_sec},
        )
        result = response.text.strip()
        _log_event("llm_call", {
            "duration_ms": round((time.time() - t_start) * 1000),
            "tokens_out": len(result.split()),
            "mode": system_extra[:40] if system_extra else "fallback",
        })
        return result
    except Exception as e:
        _log_event("llm_error", {"error": str(e)})
        err_name = type(e).__name__
        if "DeadlineExceeded" in err_name or "Timeout" in err_name or "timeout" in str(e).lower():
            return "Ich brauche gerade etwas länger zum Nachdenken. Stell die Frage nochmal — ich bin gleich schneller."
        return "Sorry, kurzer technischer Aussetzer. Versuch es gleich nochmal."


_GOAL_LABELS = {
    "muscle_gain": "Muskelaufbau", "weight_loss": "Gewichtsabnahme",
    "general_fitness": "Allgemeine Fitness", "endurance": "Ausdauer", "strength": "Kraft",
}
_LEVEL_LABELS = {
    "beginner": "Anfänger", "intermediate": "Fortgeschritten", "advanced": "Erfahren",
}
_EQUIPMENT_LABELS = {
    "bodyweight": "Körpergewicht", "dumbbells": "Kurzhanteln",
    "barbell": "Langhantel", "gym": "Fitnessstudio (alle Geräte)",
    "cardio": "Cardio-Geräte (Laufband)",
    "bicycle": "Fahrrad (Rennrad/Mountainbike)",
}
_DAY_SCHEDULES = {
    1: [3], 2: [1, 4], 3: [1, 3, 5], 4: [1, 2, 4, 5],
    5: [1, 2, 3, 5, 6], 6: [1, 2, 3, 4, 5, 6], 7: [1, 2, 3, 4, 5, 6, 7],
}
_DAY_NAMES = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}
_DURATION_MAP = {
    "muscle_gain": 6, "weight_loss": 6, "general_fitness": 6,
    "endurance": 6, "strength": 6,
}
_PHASE_GUIDANCE = {
    "muscle_gain": (
        "3 Phasen: Grundaufbau (Wo 1-2, 3-4×12-10 Reps, 75-90s Pause) → Progression (Wo 3-4, 4-5×8-6 Reps, 90-120s Pause) → "
        "Peak & Deload (Wo 5-6, Wo5: 5×5 Reps 120s, Wo6 Deload: 3×10 Reps 75s). "
        "Push/Pull/Legs oder Ober-/Unterkörper Split. Compound-Übungen priorisieren."
    ),
    "weight_loss": (
        "3 Phasen: Aktivierung (Wo 1-2, 3×15 Reps, 45s) → Intensivierung (Wo 3-4, 4×15 Reps, 40s) → "
        "Peak (Wo 5-6, 4×15 Reps, 30s). HIIT-Einheiten einbauen. Hohe Herzfrequenz."
    ),
    "general_fitness": (
        "3 Phasen: Basis (Wo 1-2, 3×12 Reps, 60s) → Steigerung (Wo 3-4, 4×12-10 Reps, 60-55s) → "
        "Konsolidierung (Wo 5-6, Wo5: 4×10 Reps 50s, Wo6 Deload: 3×12 Reps 60s). "
        "Mix aus Kraft, Cardio und Core."
    ),
    "endurance": (
        "3 Phasen: Ausdauer-Basis → Aufbau → Peak. Cardio-Fokus (Laufen, HIIT, Intervalle). "
        "Ergänzende Kraft NUR für Beine und Core. KEINE isolierten Oberkörper-Übungen. Hohe Reps (20+), kurze Pausen."
    ),
    "endurance_running": (
        "3 Phasen: Lauf-Basis (Wo 1-2, Zone-2-Dauerläufe, Lauf-Intervalle) → Aufbau (Wo 3-4, Tempoläufe, Fahrtspiel) → "
        "Peak & Tapering (Wo 5-6, Wettkampftempo, Wo6 Tapering mit kürzeren Einheiten). "
        "Lauf-Einheiten: lockere Läufe, Intervalle, Tempoläufe, Fahrtspiel, lange Läufe. "
        "Begleitende Kraft NUR für Beine und Core (Kniebeugen, Ausfallschritte, Glutebrücken, Plank). "
        "KEINE Oberkörper-Isolationsübungen."
    ),
    "endurance_cycling": (
        "3 Phasen: Rad-Basis (Wo 1-2, Zone-2-Ausfahrten, Einrollen/Ausrollen) → Aufbau (Wo 3-4, Tempo-Ausfahrten, Hügel) → "
        "Peak & Tapering (Wo 5-6, Intervall-Einheiten auf dem Rad, Wo6 kürzere Ausfahrten). "
        "Rad-Einheiten: ruhige Ausfahrten, Tempo-Ausfahrten, Intervall (Widerstand), Hügelfahrten. "
        "Begleitende Kraft NUR für Beine und Core (Kniebeugen, Wadenheben, Glutebrücken, Plank). "
        "KEINE Oberkörper-Isolationsübungen."
    ),
    "endurance_mixed": (
        "3 Phasen: Ausdauer-Basis (Wo 1-2, abwechselnd Laufen und Radfahren in Zone 2) → "
        "Aufbau (Wo 3-4, Lauf-Intervalle und Rad-Tempo) → Peak & Tapering (Wo 5-6, Wettkampftempo, Wo6 Tapering). "
        "Mix aus Lauf- und Rad-Einheiten. Begleitende Kraft NUR für Beine und Core. "
        "KEINE Oberkörper-Isolationsübungen."
    ),
    "strength": (
        "3 Phasen: Technik & Basis (Wo 1-2, 3×6 Reps, 150s) → Kraft-Aufbau (Wo 3-4, 4-5×3-4 Reps, 180s) → "
        "Peak & Deload (Wo 5-6, 5×3 Reps dann 3×5 Reps Deload). Grundübungen: Kniebeugen, Kreuzheben, "
        "Bankdrücken, Rudern, Schulterdrücken."
    ),
}


def generate_complete_plan(profile: dict) -> Optional[dict]:
    """Generates a complete training plan in a single Gemini call.

    Returns the full plan dict (compatible with generate_plan() output) or None on failure.
    """
    if not _configure():
        return None

    import google.generativeai as genai
    from datetime import datetime as _dt

    goal = profile.get("goal") or "general_fitness"
    level = profile.get("fitness_level") or "beginner"
    days = max(1, min(7, int(profile.get("days_per_week") or 3)))
    equipment = profile.get("equipment") or ["bodyweight"]
    injuries = (profile.get("injuries") or "").strip() or "keine"
    specific_goal_text = (profile.get("specific_goal") or "").strip()
    specific_goal_lower = specific_goal_text.lower()
    target_date_str = profile.get("target_date")

    # Resolve endurance subtype for phase guidance
    if goal == "endurance":
        if any(kw in specific_goal_lower for kw in ("radfahren", "fahrrad", "cycling", "rad", "bike", "rennrad", "mountainbike")):
            phase_key = "endurance_cycling"
        elif any(kw in specific_goal_lower for kw in ("gemischt", "beides", "mixed", "kombiniert")):
            phase_key = "endurance_mixed"
        elif any(kw in specific_goal_lower for kw in ("laufen", "joggen", "running", "lauf")):
            phase_key = "endurance_running"
        else:
            phase_key = "endurance"
    else:
        phase_key = goal

    # Dynamic duration from target_date
    duration_weeks = _DURATION_MAP.get(goal, 6)
    if target_date_str:
        try:
            target_dt = _dt.fromisoformat(target_date_str[:10])
            weeks_to_target = max(2, min(16, round((target_dt - _dt.utcnow()).days / 7)))
            duration_weeks = weeks_to_target
        except (ValueError, TypeError):
            pass

    schedule = _DAY_SCHEDULES.get(days, [1, 3, 5])
    schedule_str = ", ".join(_DAY_NAMES[d] for d in schedule)
    eq_str = ", ".join(_EQUIPMENT_LABELS.get(e, e) for e in equipment)
    phase_hint = _PHASE_GUIDANCE.get(phase_key, "2 Phasen mit progressiver Steigerung.")

    # Biometric block
    bio_lines = []
    age = profile.get("age")
    weight = profile.get("weight_kg")
    height = profile.get("height_cm")
    gender = profile.get("gender")
    if age:
        regen_hint = " (längere Regenerationszeiten einplanen)" if int(age) >= 45 else ""
        bio_lines.append(f"- Alter: {age} Jahre{regen_hint}")
    if weight and height:
        bmi = round(weight / ((height / 100) ** 2), 1)
        bio_lines.append(f"- Körper: {weight} kg / {height} cm (BMI {bmi})")
    elif weight:
        bio_lines.append(f"- Gewicht: {weight} kg")
    if gender:
        bio_lines.append(f"- Geschlecht: {'männlich' if gender == 'male' else 'weiblich' if gender == 'female' else gender}")
    biometric_block = ("\nBiometrische Daten:\n" + "\n".join(bio_lines)) if bio_lines else ""

    # Specific goal context
    goal_context_lines = []
    target_value = profile.get("target_value")
    target_unit = profile.get("target_unit")
    if specific_goal_text:
        goal_context_lines.append(f"- Spezifisches Ziel: {specific_goal_text}")
    if target_date_str:
        goal_context_lines.append(f"- Zieldatum: {target_date_str[:10]} ({duration_weeks} Wochen bis dahin) → letzte Woche als Tapering/Deload einplanen")
    goal_context = ("\nSpezifisches Ziel:\n" + "\n".join(goal_context_lines)) if goal_context_lines else ""

    # Goal-type specific instructions
    goal_type_hint = ""
    if target_value and target_unit == "kg" and goal in ("weight_loss", "muscle_gain"):
        direction = "Kaloriendefizit (−300–500 kcal)" if goal == "weight_loss" else "Kalorienüberschuss (+300 kcal)"
        goal_type_hint = f"- Ernährungshinweis im Plan: {direction} für Zielgewicht {target_value} kg\n"
    elif target_unit in ("min", "km") and goal == "endurance":
        goal_type_hint = f"- Plan baut gezielt auf das Ausdauerziel hin: {target_value} {target_unit} — progressive Distanz-/Temposteigerung\n"

    prompt = f"""Du bist ein professioneller Fitnesscoach. Erstelle einen vollständigen {duration_weeks}-Wochen Trainingsplan als JSON.

Nutzerprofil:
- Ziel: {_GOAL_LABELS.get(goal, goal)}
- Level: {_LEVEL_LABELS.get(level, level)}
- Trainingstage pro Woche: {days} ({schedule_str})
- Equipment: {eq_str}
- Verletzungen/Einschränkungen: {injuries}{biometric_block}{goal_context}

Regeln:
- Genau {duration_weeks} Wochen, genau {days} Workouts pro Woche
- Immer diese Wochentage verwenden: {", ".join(str(d) for d in schedule)} (1=Mo bis 7=So)
- {phase_hint}
{goal_type_hint}- 4-6 Übungen pro Workout
- Nur Übungen die zum Equipment passen
- Verletzungen berücksichtigen
- Alle Übungsnamen auf Deutsch
- Progressive Overload zwischen Phasen (Sätze/Reps/Pausen explizit anpassen)

WICHTIG – Vollständigkeit:
- Das Array "workouts" MUSS GENAU {duration_weeks * days} Objekte enthalten: {duration_weeks} Wochen x {days} Workouts.
- Gib JEDE Woche von 1 bis {duration_weeks} einzeln und vollständig aus.
- Kürze NICHT ab. Lasse KEINE Woche aus. Verwende KEINE Platzhalter, Kommentare oder Auslassungszeichen.
- Zähle vor der Ausgabe nach: es müssen {duration_weeks * days} workout-Objekte sein.

Gib NUR dieses JSON zurück, kein Markdown, keine Erklärungen:
{{
  "name": "Planname",
  "duration_weeks": {duration_weeks},
  "explanation": "2 Sätze warum dieser Plan für diesen Nutzer passt (auf Deutsch, du-Form)",
  "phases": [
    {{"phase_number": 1, "name": "Phasenname", "desc": "Beschreibung (1-2 Sätze)", "weeks": [1, 2]}}
  ],
  "workouts": [
    {{
      "week_number": 1,
      "day_of_week": {schedule[0]},
      "name": "Workout-Name",
      "phase_number": 1,
      "phase_name": "Phasenname",
      "exercises": [
        {{
          "name": "Übungsname",
          "sets": 3,
          "reps": 12,
          "rest_sec": 60,
          "duration_min": null,
          "description": "Kurzer Ausführungshinweis"
        }}
      ]
    }}
  ]
}}"""

    t_start = time.time()
    try:
        # FIX 14.07.2026: max_output_tokens 8000 -> 32000. Nicht die Ursache des
        # Lazy-LLM-Problems (finish_reason war STOP, nicht MAX_TOKENS), aber bei langen
        # Plaenen (bis 16 Wochen) waeren 8000 Tokens tatsaechlich zu knapp gewesen.
        # Zusaetzlich: Timeout ergaenzt (fehlte hier komplett, anders als in ask_llm).
        model = genai.GenerativeModel(
            MODEL,
            generation_config={"max_output_tokens": 32000, "temperature": 0.5},
        )
        response = model.generate_content(
            [{"role": "user", "parts": [prompt]}],
            request_options={"timeout": 90},
        )
        raw = response.text.strip()

        # Markdown-Fences entfernen
        if raw.startswith("```"):
            lines = raw.split("\n")
            start = 1 if lines[0].strip().startswith("```") else 0
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[start:end]).strip()

        data = json.loads(raw)
        _log_event("plan_gemini_complete", {
            "duration_ms": round((time.time() - t_start) * 1000),
            "goal": goal,
            "weeks": data.get("duration_weeks"),
            "workouts": len(data.get("workouts", [])),
        })
        return data
    except Exception as e:
        _log_event("plan_gemini_error", {"error": str(e), "goal": goal})
        return None




def parse_specific_goal(raw_text: str, main_goal: str) -> dict:
    """Parse free-text specific goal into structured data.

    Returns dict with display_text, type, target_value, target_unit, target_date (ISO string or None).
    Falls back to qualitative/raw-text on any failure.
    """
    fallback = {
        "display_text": raw_text,
        "type": "qualitative",
        "target_value": None,
        "target_unit": None,
        "target_date": None,
    }
    if not _configure() or not raw_text or not raw_text.strip():
        return fallback

    import google.generativeai as genai
    from datetime import datetime as _dt

    today = _dt.utcnow().strftime("%Y-%m-%d")
    prompt = f"""Analysiere dieses Fitnessziel und extrahiere strukturierte Daten.

Fitnessziel: "{raw_text}"
Haupt-Trainingsziel: {main_goal}
Heutiges Datum: {today}

Gib NUR dieses JSON zurück (kein Markdown, keine Erklärungen):
{{
  "display_text": "Bereinigter Zieltext, max 60 Zeichen, auf Deutsch",
  "type": "weight_target",
  "target_value": null,
  "target_unit": null,
  "target_date": null
}}

type muss einer dieser Werte sein:
- weight_target  → Gewichtsziel (z.B. "75 kg", "5 kg abnehmen")
- performance    → Ausdauer/Zeit-Ziel (z.B. "5 km unter 25 Min")
- strength       → Kraft-Ziel (z.B. "100 kg Bankdrücken")
- event          → Event mit Deadline (z.B. "Halbmarathon in 6 Monaten")
- qualitative    → alles andere

Regeln:
- target_value: Zahl oder null
- target_unit: "kg", "min", "km" oder null
- target_date: absolutes ISO-Datum (heute={today}) oder null
- Relative Angaben umrechnen ("in 3 Monaten" → konkretes Datum)
- Bei Unsinn: type="qualitative", display_text=bereinigter Text, rest null"""

    try:
        model = genai.GenerativeModel(
            MODEL,
            generation_config={"max_output_tokens": 150, "temperature": 0.1},
        )
        response = model.generate_content(
            [{"role": "user", "parts": [prompt]}],
            request_options={"timeout": 12},
        )
        raw = response.text.strip()

        if raw.startswith("```"):
            lines = raw.split("\n")
            start = 1 if lines[0].strip().startswith("```") else 0
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[start:end]).strip()

        data = json.loads(raw)
        return {
            "display_text": data.get("display_text") or raw_text,
            "type": data.get("type") or "qualitative",
            "target_value": data.get("target_value"),
            "target_unit": data.get("target_unit"),
            "target_date": data.get("target_date"),
        }
    except Exception as e:
        _log_event("goal_parse_error", {"error": str(e), "raw": raw_text[:80]})
        return fallback


def _log_event(event_type: str, data: dict):
    try:
        LOG_PATH.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH / "events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "type": event_type, **data}) + "\n")
    except Exception:
        pass
