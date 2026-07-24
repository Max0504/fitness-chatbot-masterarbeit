"""
Ernährungsempfehlungen via Gemini, aufgeteilt in drei separat refreshbare Sektionen:
  - static (goal_note, general_tips): einmalig pro Ziel/Plan
  - meals: separat neu generierbar
  - nutrients (key_nutrients, avoid): separat neu generierbar
"""
import os
import json
import time
import warnings
from pathlib import Path
from typing import Optional

CACHE_FILE = Path(__file__).parent.parent / "data" / "nutrition_advice.json"

GOAL_LABELS = {
    "weight_loss": "Abnehmen",
    "muscle_gain": "Muskelaufbau",
    "general_fitness": "Allgemeine Fitness",
    "endurance": "Ausdauer",
    "strength": "Kraft",
}


def _load_cache() -> Optional[dict]:
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return None


def _save_cache(data: dict) -> None:
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _get_model():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nicht gesetzt")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    return genai.GenerativeModel(os.environ.get("LLM_MODEL", "gemini-2.0-flash-lite"))


def _build_context(profile: dict) -> str:
    goal = profile.get("goal") or "general_fitness"
    goal_label = GOAL_LABELS.get(goal, goal)
    lines = [f"Ziel: {goal_label}"]
    if profile.get("specific_goal"):
        lines.append(f"Spezifisches Ziel: {profile['specific_goal']}")
    if profile.get("weight_kg"):
        lines.append(f"Körpergewicht: {profile['weight_kg']} kg")
    if profile.get("injuries"):
        lines.append(f"Einschränkungen: {profile['injuries']}")
    return "\n".join(lines)


def _parse_json(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _call_all(profile: dict) -> dict:
    model = _get_model()
    context = _build_context(profile)
    prompt = f"""Du bist ein Ernährungsberater. Erstelle auf Basis des folgenden Nutzerprofils personalisierte Ernährungsempfehlungen auf Deutsch.

Nutzerprofil:
{context}

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in diesem exakten Format (kein Markdown, kein Text davor/danach):
{{
  "goal_note": "Ein prägnanter Satz der die Ernährungsstrategie für dieses Ziel erklärt",
  "general_tips": ["Allgemeiner Tipp 1", "Allgemeiner Tipp 2", "Allgemeiner Tipp 3"],
  "meals": [
    {{"meal_type": "Frühstück", "name": "Name des Gerichts", "desc": "Kurze Beschreibung mit Zutaten", "approx_kcal": 400}},
    {{"meal_type": "Mittagessen", "name": "Name des Gerichts", "desc": "Kurze Beschreibung mit Zutaten", "approx_kcal": 650}},
    {{"meal_type": "Abendessen", "name": "Name des Gerichts", "desc": "Kurze Beschreibung mit Zutaten", "approx_kcal": 550}},
    {{"meal_type": "Snack", "name": "Name des Snacks", "desc": "Kurze Beschreibung", "approx_kcal": 200}}
  ],
  "key_nutrients": ["Spezifischer Nährstoff 1 mit konkretem Grund", "Spezifischer Nährstoff 2 mit konkretem Grund", "Spezifischer Nährstoff 3 mit konkretem Grund"],
  "avoid": ["Lebensmittel 1 mit Grund", "Lebensmittel 2 mit Grund", "Lebensmittel 3 mit Grund"]
}}"""
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.7, "max_output_tokens": 1200},
        request_options={"timeout": 50},
    )
    return _parse_json(response.text)


def _call_meals(profile: dict) -> list:
    model = _get_model()
    context = _build_context(profile)
    prompt = f"""Du bist ein Ernährungsberater. Schlage 4 neue, abwechslungsreiche Beispiel-Mahlzeiten für dieses Nutzerprofil vor. Die Vorschläge sollen sich von typischen Standardmahlzeiten unterscheiden.

Nutzerprofil:
{context}

Antworte AUSSCHLIESSLICH mit einem JSON-Array (kein Markdown, kein Text davor/danach):
[
  {{"meal_type": "Frühstück", "name": "Name des Gerichts", "desc": "Kurze Beschreibung mit Zutaten", "approx_kcal": 400}},
  {{"meal_type": "Mittagessen", "name": "Name des Gerichts", "desc": "Kurze Beschreibung mit Zutaten", "approx_kcal": 650}},
  {{"meal_type": "Abendessen", "name": "Name des Gerichts", "desc": "Kurze Beschreibung mit Zutaten", "approx_kcal": 550}},
  {{"meal_type": "Snack", "name": "Name des Snacks", "desc": "Kurze Beschreibung", "approx_kcal": 200}}
]"""
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.9, "max_output_tokens": 800},
        request_options={"timeout": 50},
    )
    return _parse_json(response.text)


def _call_nutrients(profile: dict) -> dict:
    model = _get_model()
    context = _build_context(profile)
    prompt = f"""Du bist ein Ernährungsberater. Gib spezifische, neue Nährstoff- und Vermeidungsempfehlungen für dieses Nutzerprofil. Sei konkret und abwechslungsreich.

Nutzerprofil:
{context}

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (kein Markdown, kein Text davor/danach):
{{
  "key_nutrients": ["Spezifischer Nährstoff 1 mit konkretem Grund", "Spezifischer Nährstoff 2 mit konkretem Grund", "Spezifischer Nährstoff 3 mit konkretem Grund"],
  "avoid": ["Lebensmittel 1 mit Grund", "Lebensmittel 2 mit Grund", "Lebensmittel 3 mit Grund"]
}}"""
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.8, "max_output_tokens": 500},
        request_options={"timeout": 50},
    )
    return _parse_json(response.text)


def _assemble(cache: dict) -> dict:
    static = cache.get("static", {})
    nutrients = cache.get("nutrients", {})
    return {
        "goal_note": static.get("goal_note", ""),
        "general_tips": static.get("general_tips", []),
        "meals": cache.get("meals", []),
        "key_nutrients": nutrients.get("key_nutrients", []),
        "avoid": nutrients.get("avoid", []),
    }


def get_nutrition_advice(profile: dict) -> dict:
    """Returns cached or freshly generated advice (all sections)."""
    goal = profile.get("goal") or "general_fitness"
    specific_goal = profile.get("specific_goal")

    cached = _load_cache()
    if (
        cached
        and cached.get("goal") == goal
        and cached.get("specific_goal") == specific_goal
        and cached.get("static")
        and cached.get("meals")
        and cached.get("nutrients")
    ):
        return _assemble(cached)

    data = _call_all(profile)
    cache = {
        "goal": goal,
        "specific_goal": specific_goal,
        "static": {"goal_note": data["goal_note"], "general_tips": data["general_tips"]},
        "meals": data["meals"],
        "nutrients": {"key_nutrients": data["key_nutrients"], "avoid": data["avoid"]},
        "ts": time.time(),
    }
    _save_cache(cache)
    return _assemble(cache)


def refresh_meals(profile: dict) -> dict:
    """Regenerates only the meals section, keeps static and nutrients."""
    goal = profile.get("goal") or "general_fitness"
    specific_goal = profile.get("specific_goal")

    cached = _load_cache() or {}
    meals = _call_meals(profile)
    cached.update({"goal": goal, "specific_goal": specific_goal, "meals": meals, "ts": time.time()})
    _save_cache(cached)
    return _assemble(cached)


def refresh_nutrients(profile: dict) -> dict:
    """Regenerates only key_nutrients and avoid, keeps static and meals."""
    goal = profile.get("goal") or "general_fitness"
    specific_goal = profile.get("specific_goal")

    cached = _load_cache() or {}
    nutrients = _call_nutrients(profile)
    cached.update({"goal": goal, "specific_goal": specific_goal, "nutrients": nutrients, "ts": time.time()})
    _save_cache(cached)
    return _assemble(cached)
