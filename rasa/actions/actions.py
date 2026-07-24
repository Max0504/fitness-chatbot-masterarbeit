from typing import Any, Text, Dict, List
import os
import random
import threading
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction

from .llm_client import ask_llm
from .db import get_session, DEMO_USER_ID
from .db import User, Profile, TrainingPlan, PlanWorkout, WorkoutLog, PointsHistory, WeightLog, CardioLog, StrengthLog
from .plan_generator import generate_plan
from .plan_status import set_status, get_status


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

EQUIPMENT_MAP = {
    "körpergewicht": "bodyweight", "bodyweight": "bodyweight", "zuhause": "bodyweight",
    "keine geräte": "bodyweight", "ohne geräte": "bodyweight",
    "kurzhantel": "dumbbells", "kurzhanteln": "dumbbells", "hanteln": "dumbbells",
    "dumbbells": "dumbbells", "dumbbell": "dumbbells",
    "langhantel": "barbell", "barbell": "barbell",
    "fitnessstudio": "gym", "gym": "gym", "studio": "gym", "heimstudio": "gym",
    "cardio": "cardio", "laufband": "cardio",
    "fahrrad": "bicycle", "rennrad": "bicycle", "mountainbike": "bicycle",
    "bike": "bicycle", "rad": "bicycle", "fahrradfahren": "bicycle",
}


def _parse_equipment(text: str) -> list:
    text_lower = text.lower()
    found = []
    for keyword, value in EQUIPMENT_MAP.items():
        if keyword in text_lower and value not in found:
            found.append(value)
    return found if found else ["bodyweight"]


def _get_profile_dict(session) -> Dict:
    profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
    if not profile:
        return {}
    return {
        "name": profile.name,
        "goal": profile.goal,
        "fitness_level": profile.fitness_level,
        "days_per_week": profile.days_per_week,
        "equipment": profile.equipment or [],
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "injuries": profile.injuries,
        "specific_goal": profile.specific_goal,
        "target_value": profile.target_value,
        "target_unit": profile.target_unit,
        "target_date": profile.target_date.isoformat() if profile.target_date else None,
    }


def _get_recent_history(tracker: Tracker, n: int = 8) -> List[Dict]:
    history = []
    for event in tracker.events[-30:]:
        if event.get("event") == "user" and event.get("text"):
            history.append({"role": "user", "content": event["text"]})
        elif event.get("event") == "bot" and event.get("text"):
            history.append({"role": "assistant", "content": event["text"]})
    return history[-(n * 2):]


def _compute_streak(logs: list) -> int:
    if not logs:
        return 0
    days = sorted({log.completed_at.date() for log in logs}, reverse=True)
    today = datetime.utcnow().date()
    if (today - days[0]).days > 1:
        return 0
    streak = 1
    for i in range(1, len(days)):
        if (days[i - 1] - days[i]).days == 1:
            streak += 1
        else:
            break
    return streak


def _save_plan_to_db(plan_data: dict, user_id: int = DEMO_USER_ID) -> None:
    """Deactivates old plans and persists a new one. Runs in any thread."""
    session = get_session()
    try:
        session.query(TrainingPlan).filter_by(user_id=user_id, active=True).update({"active": False})
        new_plan = TrainingPlan(
            user_id=user_id,
            name=plan_data["name"],
            goal=plan_data["goal"],
            duration_weeks=plan_data["duration_weeks"],
            phases=plan_data.get("phases", []),
            explanation=plan_data.get("explanation"),
            active=True,
        )
        session.add(new_plan)
        session.flush()
        for w in plan_data["workouts"]:
            session.add(PlanWorkout(
                plan_id=new_plan.id,
                week_number=w["week_number"],
                day_of_week=w["day_of_week"],
                name=w["name"],
                phase_number=w.get("phase_number", 1),
                phase_name=w.get("phase_name", "Phase 1"),
                exercises=w["exercises"],
            ))
        session.commit()
    finally:
        session.close()


def _generate_plan_in_background(profile_dict: dict, user_id: int = DEMO_USER_ID) -> None:
    """Daemon thread: tries Gemini, falls back to algorithmic. Writes status to plan_status.json."""
    set_status("generating")
    try:
        plan_data = None
        use_gemini = os.environ.get("PLAN_USE_GEMINI", "true").lower() == "true"

        if use_gemini:
            try:
                from .llm_client import generate_complete_plan
                from .plan_generator import _validate_gemini_plan, _normalize_gemini_plan, WEEKLY_PROGRESSIONS
                gemini_result = generate_complete_plan(profile_dict)
                if gemini_result:
                    goal = profile_dict.get("goal") or "general_fitness"
                    days = int(profile_dict.get("days_per_week") or 3)
                    expected_weeks = len(WEEKLY_PROGRESSIONS.get(goal, WEEKLY_PROGRESSIONS["general_fitness"]))
                    if _validate_gemini_plan(gemini_result, days, expected_weeks):
                        plan_data = _normalize_gemini_plan(gemini_result, goal, days)
            except Exception as e:
                set_status("generating", f"KI fehlgeschlagen ({e}), verwende Algorithmus…")

        if plan_data is None:
            from .plan_generator import _generate_plan_algorithmic
            plan_data = _generate_plan_algorithmic(profile_dict)

        _save_plan_to_db(plan_data, user_id)
        set_status("ready")
    except Exception as e:
        set_status("error", str(e))


def _start_background_generation(profile_dict: dict) -> None:
    t = threading.Thread(target=_generate_plan_in_background, args=(profile_dict,), daemon=True)
    t.start()


def _regenerate_future_workouts(session, plan, profile_dict: dict) -> tuple:
    """Ersetzt nur Workouts ab der aktuellen Planwoche — vergangene bleiben erhalten."""
    days_since = (datetime.utcnow() - plan.created_at).days
    current_week = min(days_since // 7 + 1, plan.duration_weeks)

    session.query(PlanWorkout).filter(
        PlanWorkout.plan_id == plan.id,
        PlanWorkout.week_number >= current_week,
    ).delete()
    session.flush()

    plan_data = generate_plan(profile_dict)
    for w in plan_data["workouts"]:
        if w["week_number"] < current_week:
            continue
        session.add(PlanWorkout(
            plan_id=plan.id,
            week_number=w["week_number"],
            day_of_week=w["day_of_week"],
            name=w["name"],
            phase_number=w.get("phase_number", 1),
            phase_name=w.get("phase_name", "Phase 1"),
            exercises=w["exercises"],
        ))

    plan.name = plan_data["name"]
    plan.goal = plan_data["goal"]
    plan.phases = plan_data.get("phases", [])
    plan.duration_weeks = plan_data["duration_weeks"]
    return plan_data, current_week


# ── Strukturierte Actions (kein LLM) ─────────────────────────────────────────

class ActionAskSpecificGoal(Action):
    def name(self) -> Text:
        return "action_ask_specific_goal"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        goal = tracker.get_slot("goal") or "general_fitness"

        if goal == "endurance":
            dispatcher.utter_message(
                text="Welche Art von Ausdauer trainierst du hauptsächlich?",
                buttons=[
                    {"title": "🏃 Laufen", "payload": "Laufen"},
                    {"title": "🚴 Radfahren", "payload": "Radfahren"},
                    {"title": "🏃🚴 Beides / Gemischt", "payload": "Gemischt"},
                    {"title": "🌟 Ausdauer allgemein", "payload": "Ausdauer allgemein"},
                ],
            )
            return []

        questions = {
            "weight_loss":     "Hast du ein Zielgewicht oder eine Deadline? (z.B. '75 kg bis September' oder 'ich will 8 kg abnehmen')",
            "muscle_gain":     "Hast du ein konkretes Aufbau-Ziel? (z.B. '+5 kg Muskelmasse' oder 'definierter Oberkörper')",
            "strength":        "Welche Kraft-Ziele hast du? (z.B. '100 kg Bankdrücken' oder '2× Körpergewicht Kniebeugen')",
            "general_fitness": "Hast du einen besonderen Wunsch? (z.B. 'fitter im Alltag', 'weniger Rückenschmerzen')",
        }
        dispatcher.utter_message(
            text=questions.get(goal, questions["general_fitness"]),
            buttons=[{"title": "Kein spezifisches Ziel", "payload": "/no_specific_goal"}],
        )
        return []


class ActionCheckOnboardingStatus(Action):
    def name(self) -> Text:
        return "action_check_onboarding_status"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session = get_session()
        try:
            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            onboarded = bool(profile and profile.onboarded)
        finally:
            session.close()
        return [SlotSet("onboarded", onboarded)]


class ActionCreateTrainingPlan(Action):
    def name(self) -> Text:
        return "action_create_training_plan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        goal = tracker.get_slot("goal")
        level = tracker.get_slot("fitness_level")
        days = tracker.get_slot("days_per_week")
        user_name = tracker.get_slot("user_name")
        user_equipment_raw = tracker.get_slot("user_equipment") or ""
        user_injuries = tracker.get_slot("user_injuries") or ""
        specific_goal_raw = tracker.get_slot("specific_goal") or ""

        # FIX 14.07.2026: Vorher Substring-Test (`w in user_injuries`), wodurch gueltige
        # Angaben wie "Knieprobleme links, keine tiefen Kniebeugen" wegen des enthaltenen
        # Wortes "keine" komplett verworfen wurden. Jetzt: nur verwerfen, wenn die GESAMTE
        # Eingabe eine Verneinung ist.
        no_injury_words = [
            "keine", "nein", "nichts", "alles gut", "alles in ordnung", "nö", "ne",
            "keine verletzungen", "keine probleme", "keine beschwerden", "nix",
        ]
        _inj_norm = user_injuries.strip().lower().rstrip(".!,")
        injuries_clean = None if (not _inj_norm or _inj_norm in no_injury_words) else user_injuries.strip()
        specific_goal_clean = None if specific_goal_raw.lower() in ("keins", "kein", "") else specific_goal_raw.strip()

        session = get_session()
        try:
            user = session.query(User).filter_by(id=DEMO_USER_ID).first()
            if not user:
                session.add(User(id=DEMO_USER_ID, username="demo_user"))
                session.flush()

            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            if not profile:
                profile = Profile(user_id=DEMO_USER_ID)
                session.add(profile)

            if user_name and not profile.name:
                profile.name = user_name
            if user_equipment_raw.strip():
                profile.equipment = _parse_equipment(user_equipment_raw)
            elif not profile.equipment:
                profile.equipment = ["bodyweight"]

            profile.goal = goal
            profile.fitness_level = level
            profile.days_per_week = int(days) if days else 3
            profile.injuries = injuries_clean
            profile.onboarded = True
            profile.plan_feedback_requested_at = None

            # Spezifisches Ziel strukturiert parsen
            if specific_goal_clean:
                from .llm_client import parse_specific_goal
                parsed = parse_specific_goal(specific_goal_clean, goal or "general_fitness")
                profile.specific_goal = parsed["display_text"]
                profile.target_value = parsed["target_value"]
                profile.target_unit = parsed["target_unit"]
                if parsed["target_date"]:
                    try:
                        profile.target_date = datetime.fromisoformat(parsed["target_date"])
                    except (ValueError, TypeError):
                        profile.target_date = None
                else:
                    profile.target_date = None
            else:
                profile.specific_goal = None
                profile.target_value = None
                profile.target_unit = None
                profile.target_date = None

            session.commit()

            profile_dict = _get_profile_dict(session)
            session.add(PointsHistory(user_id=DEMO_USER_ID, points=50, reason="onboarding"))
            session.commit()
        finally:
            session.close()

        # Prevent double-generation
        if get_status().get("status") == "generating":
            dispatcher.utter_message(
                text="Ein Plan wird gerade erstellt — schau gleich im Reiter 'Trainingsplan' nach!"
            )
            return [SlotSet("onboarded", True)]

        _start_background_generation(profile_dict)

        _GOAL_LABELS_LOCAL = {
            "muscle_gain": "Muskelaufbau", "weight_loss": "Abnehmen",
            "general_fitness": "Allgemeine Fitness", "endurance": "Ausdauer", "strength": "Kraft",
        }
        goal_label = _GOAL_LABELS_LOCAL.get(goal or "", goal or "Training")
        msg = (
            f"Perfekt! Ich erstelle deinen {goal_label}-Plan — "
            f"das dauert eine Minute. Schau im Reiter 'Trainingsplan' nach, "
            f"er erscheint dort sobald er fertig ist."
        )
        if specific_goal_clean:
            msg += f" Dein Ziel '{specific_goal_clean}' hab ich im Blick."
        dispatcher.utter_message(text=msg)
        return [SlotSet("onboarded", True)]


class ActionShowPlan(Action):
    def name(self) -> Text:
        return "action_show_plan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session = get_session()
        try:
            plan = session.query(TrainingPlan).filter_by(user_id=DEMO_USER_ID, active=True).first()
            if not plan:
                dispatcher.utter_message(response="utter_no_active_plan")
                return []
            DAY_LABELS = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}
            workouts = sorted(plan.workouts, key=lambda w: (w.week_number, w.day_of_week))
            lines = [f"Dein Plan: **{plan.name}** ({plan.duration_weeks} Wochen, {len(workouts)} Trainings/Woche)"]
            for w in workouts:
                ex_names = ", ".join(e["name"] for e in (w.exercises or []))
                day_label = DAY_LABELS.get(w.day_of_week, str(w.day_of_week))
                lines.append(f"• {day_label}: **{w.name}** — {ex_names}")
            lines.append("\nDetails im Reiter 'Trainingsplan'.")
            dispatcher.utter_message(text="\n".join(lines))
        finally:
            session.close()
        return []


class ActionShowDashboardSummary(Action):
    def name(self) -> Text:
        return "action_show_dashboard_summary"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session = get_session()
        try:
            total_points = sum(
                p.points for p in session.query(PointsHistory).filter_by(user_id=DEMO_USER_ID).all()
            ) or 0
            level = total_points // 200 + 1
            logs = session.query(WorkoutLog).filter_by(user_id=DEMO_USER_ID)\
                .order_by(WorkoutLog.completed_at.desc()).all()
            streak = _compute_streak(logs)
            since = datetime.utcnow() - timedelta(days=7)
            recent_count = sum(1 for log in logs if log.completed_at >= since)
            dispatcher.utter_message(
                text=f"📊 **Level {level}** mit **{total_points} Punkten** (Streak: {streak} Tage). "
                     f"Letzte 7 Tage: **{recent_count} Workouts**. Mehr Details im Dashboard."
            )
        finally:
            session.close()
        return []


class ActionLogWorkout(Action):
    def name(self) -> Text:
        return "action_log_workout"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session = get_session()
        streak_bonus = 0
        try:
            # Bestehende Logs für Streak-Berechnung laden
            existing_logs = session.query(WorkoutLog).filter_by(user_id=DEMO_USER_ID)\
                .order_by(WorkoutLog.completed_at.desc()).all()
            streak_before = _compute_streak(existing_logs)

            log = WorkoutLog(user_id=DEMO_USER_ID, completed_at=datetime.utcnow())
            session.add(log)
            session.add(PointsHistory(user_id=DEMO_USER_ID, points=20, reason="workout_completed"))

            if streak_before >= 1:
                streak_bonus = 10
                session.add(PointsHistory(user_id=DEMO_USER_ID, points=streak_bonus, reason="streak_bonus"))

            session.commit()
        finally:
            session.close()

        template_id = random.randint(1, 5)
        dispatcher.utter_message(response=f"utter_workout_logged_{template_id}")

        if streak_bonus:
            dispatcher.utter_message(response="utter_streak_bonus")

        dispatcher.utter_message(response="utter_ask_workout_feeling")
        return []


# ── LLM-Actions ──────────────────────────────────────────────────────────────

class ActionExplainExercise(Action):
    def name(self) -> Text:
        return "action_explain_exercise"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        user_msg = tracker.latest_message.get("text", "")
        answer = ask_llm(
            user_message=user_msg,
            system_extra=(
                "Der User möchte eine Übung erklärt haben. Erkläre sie klar und präzise: "
                "Ausführung, trainierte Muskeln, 1-2 Technik-Tipps. Max. 5 Sätze. "
                "Wenn unklar welche Übung gemeint ist, frag kurz nach."
            ),
            max_tokens=400,
        )
        dispatcher.utter_message(text=answer)
        return []


class ActionMotivate(Action):
    def name(self) -> Text:
        return "action_motivate"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session = get_session()
        try:
            total_points = sum(
                p.points for p in session.query(PointsHistory).filter_by(user_id=DEMO_USER_ID).all()
            ) or 0

            # Streak über alle 3 Log-Typen berechnen
            today = datetime.utcnow().date()
            workout_dates = {l.completed_at.date() for l in session.query(WorkoutLog).filter_by(user_id=DEMO_USER_ID).all()}
            cardio_dates = {l.logged_at.date() for l in session.query(CardioLog).filter_by(user_id=DEMO_USER_ID).all()}
            strength_dates = {l.logged_at.date() for l in session.query(StrengthLog).filter_by(user_id=DEMO_USER_ID).all()}
            all_dates = sorted(workout_dates | cardio_dates | strength_dates, reverse=True)

            streak = 0
            if all_dates and (today - all_dates[0]).days <= 1:
                streak = 1
                for i in range(1, len(all_dates)):
                    if (all_dates[i - 1] - all_dates[i]).days == 1:
                        streak += 1
                    else:
                        break
        finally:
            session.close()

        # Template-Gruppe nach Streak-Level wählen, 30% Chance auf generisches Template
        if random.random() < 0.3:
            pool = [f"utter_motivate_generic_{i}" for i in range(1, 6)]
        elif streak >= 15:
            pool = [f"utter_motivate_high_{i}" for i in range(1, 6)]
        elif streak >= 4:
            pool = [f"utter_motivate_mid_{i}" for i in range(1, 6)]
        else:
            pool = [f"utter_motivate_low_{i}" for i in range(1, 6)]

        dispatcher.utter_message(
            response=random.choice(pool),
            streak_days=streak,
            total_points=total_points,
        )
        return []


class ActionNutritionAdvice(Action):
    def name(self) -> Text:
        return "action_nutrition_advice"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        user_msg = tracker.latest_message.get("text", "Gib mir einen Ernährungstipp.")
        session = get_session()
        try:
            profile = _get_profile_dict(session)
        finally:
            session.close()

        system_extra = (
            "Du bist im Modus 'Ernährungsberatung'. "
            "Gib praktische, konkrete Tipps. Keine medizinische Beratung. "
            "Wenn der User Ziele wie Abnehmen oder Muskelaufbau hat, beziehe das mit ein. "
            "Konkrete Lebensmittel-Beispiele sind willkommen, aber keine rigiden Pläne."
        )
        history = _get_recent_history(tracker)
        # Letzten User-Turn aus History entfernen (wird als user_message übergeben)
        if history and history[-1]["role"] == "user":
            history = history[:-1]

        answer = ask_llm(
            user_message=user_msg,
            system_extra=system_extra,
            user_context={k: v for k, v in profile.items() if v is not None},
            history=history,
            max_tokens=500,
        )
        dispatcher.utter_message(text=answer)
        return []


class ActionModifyPlan(Action):
    def name(self) -> Text:
        return "action_modify_plan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        import re
        user_msg = tracker.latest_message.get("text", "")

        # Guard: wenn es eine Frage ist (endet auf "?" oder beginnt mit Fragewort), nicht als
        # Plananpassung behandeln — stattdessen LLM-Antwort geben.
        _question_starts = ("was ", "wie ", "warum ", "wann ", "welche ", "welcher ",
                            "erkläre ", "erklär ", "bedeutet ", "was ist ", "wieso ")
        _is_question = (
            user_msg.strip().endswith("?")
            or any(user_msg.lower().strip().startswith(q) for q in _question_starts)
        )
        if _is_question:
            session = get_session()
            try:
                profile = _get_profile_dict(session)
            finally:
                session.close()
            answer = ask_llm(
                user_message=user_msg,
                system_extra=(
                    "Du bist ein Fitness-Coach. Beantworte die Frage des Nutzers direkt und präzise. "
                    "Max. 4 Sätze."
                ),
                user_context={k: v for k, v in profile.items() if v is not None},
                max_tokens=400,
            )
            dispatcher.utter_message(text=answer)
            return []

        # Extract number and goal entities directly from the latest message (not slots,
        # since slot conditions restrict filling to the form context)
        entity_days = None
        entity_goal = None
        entity_direction = None  # FIX 14.07.2026: Richtung aus dem Button-Payload
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "number" and entity_days is None:
                try:
                    entity_days = int(float(e.get("value", 0)))
                except (ValueError, TypeError):
                    pass
            elif e.get("entity") == "goal" and entity_goal is None:
                entity_goal = e.get("value")
            elif e.get("entity") == "modify_direction" and entity_direction is None:
                entity_direction = (e.get("value") or "").strip().lower()

        # Regex fallback: catch plain digits 1-7 if DIET missed the entity
        if entity_days is None:
            m = re.search(r'\b([1-7])\b', user_msg)
            if m:
                entity_days = int(m.group(1))

        session = get_session()
        try:
            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            if not profile:
                dispatcher.utter_message(text="Du hast noch keinen Plan. Sag 'Ich will loslegen' um zu starten.")
                return []

            changed = False
            _LEVELS = ["beginner", "intermediate", "advanced"]

            def _shift_level(direction: str):
                """Verschiebt das Fitnesslevel. Gibt True zurueck, wenn sich wirklich
                etwas geaendert hat. FIX 14.07.2026: Vorher wurde changed=True auch dann
                gesetzt, wenn das Level bereits am Rand lag (z. B. 'beginner' + EASIER),
                sodass der Bot faelschlich eine Anpassung meldete, die nicht stattfand."""
                cur = profile.fitness_level if profile.fitness_level in _LEVELS else "intermediate"
                idx = _LEVELS.index(cur)
                new_idx = max(0, idx - 1) if direction == "easier" else min(2, idx + 1)
                if new_idx == idx:
                    return False
                profile.fitness_level = _LEVELS[new_idx]
                return True

            def _edge_msg(direction: str) -> str:
                if direction == "easier":
                    return ("Du bist bereits auf der niedrigsten Stufe — leichter kann ich den Plan "
                            "nicht machen. Möchtest du stattdessen weniger Trainingstage? "
                            "Sag mir einfach eine Zahl (z. B. „2“).")
                return ("Du bist bereits auf der höchsten Stufe — viel schwerer geht nicht mehr. "
                        "Möchtest du stattdessen mehr Trainingstage? "
                        "Sag mir einfach eine Zahl (z. B. „5“).")

            if entity_days is not None and 1 <= entity_days <= 7:
                profile.days_per_week = entity_days
                changed = True
            elif entity_direction in ("easier", "harder"):
                # FIX 14.07.2026: Die Feedback-Buttons senden die Richtung jetzt im Payload mit.
                # Vorher sendeten ALLE Buttons denselben Payload "/modify_plan", sodass das LLM
                # aus dem blossen String "/modify_plan" die Absicht raten musste -> [NEED_INFO]
                # -> Rueckfrage statt Anpassung. Jetzt ist kein LLM-Aufruf mehr noetig.
                if not _shift_level(entity_direction):
                    dispatcher.utter_message(text=_edge_msg(entity_direction))
                    return []
                changed = True
            elif entity_goal:
                # Ziel geändert → Profil updaten und Mini-Onboarding für Tage + spez. Ziel starten
                profile.goal = entity_goal
                profile.specific_goal = None
                session.commit()
                return [
                    SlotSet("goal", entity_goal),
                    SlotSet("days_per_week", None),
                    SlotSet("specific_goal", None),
                    FollowupAction("onboarding_form"),
                ]
            else:
                # Use LLM only for EASIER / HARDER / REGEN which can't be parsed simply
                system_extra = (
                    "Modus: Plan-Anpassung. Erkenne was geändert werden soll. "
                    "Antworte ausschließlich mit einem dieser Codes, ohne weiteren Text davor: "
                    "[EASIER] wenn der Plan leichter sein soll, "
                    "[HARDER] wenn er schwerer sein soll, "
                    "[REGEN] wenn ein komplett neuer Plan gewünscht wird, "
                    "[NEED_INFO] wenn unklar ist was geändert werden soll. "
                    "Nach dem Code ein freundlicher kurzer Satz auf Deutsch."
                )
                answer = ask_llm(
                    user_message=user_msg,
                    system_extra=system_extra,
                    user_context={
                        "aktuelles_ziel": profile.goal,
                        "level": profile.fitness_level,
                        "tage_pro_woche": profile.days_per_week,
                    },
                    max_tokens=150,
                )
                code_match = re.search(r'\[(EASIER|HARDER|REGEN|NEED_INFO)\]', answer)
                clean_answer = answer
                if code_match:
                    code = code_match.group(1)
                    clean_answer = answer.replace(code_match.group(0), "").strip()
                    # FIX 14.07.2026: nutzt jetzt _shift_level() -> meldet keinen Erfolg mehr,
                    # wenn das Level bereits am Rand liegt und sich gar nichts aendern kann.
                    if code in ("EASIER", "HARDER"):
                        _dir = "easier" if code == "EASIER" else "harder"
                        if not _shift_level(_dir):
                            dispatcher.utter_message(text=_edge_msg(_dir))
                            return []
                        changed = True
                    elif code == "REGEN":
                        changed = True

                if not changed:
                    dispatcher.utter_message(text=clean_answer or answer)
                    return []

            if changed:
                session.commit()
                profile_dict = _get_profile_dict(session)
        finally:
            session.close()

        if changed:
            if get_status().get("status") == "generating":
                dispatcher.utter_message(
                    text="Ein Plan wird gerade erstellt — schau gleich im Reiter 'Trainingsplan' nach!"
                )
            else:
                _start_background_generation(profile_dict)
                dispatcher.utter_message(
                    text="Ich passe deinen Plan an — dauert eine Minute. "
                         "Du findest ihn im Reiter 'Trainingsplan' sobald er fertig ist."
                )

        return []


class ActionSwapExercise(Action):
    def name(self) -> Text:
        return "action_swap_exercise"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        import difflib

        exercise_name = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "exercise_name":
                exercise_name = e.get("value", "").strip()
                break
        if not exercise_name:
            exercise_name = tracker.latest_message.get("text", "")

        session = get_session()
        try:
            profile_dict = _get_profile_dict(session)
            plan = session.query(TrainingPlan).filter_by(user_id=DEMO_USER_ID, active=True).first()
            if not plan:
                dispatcher.utter_message(text="Du hast noch keinen aktiven Trainingsplan.")
                return []

            workouts = session.query(PlanWorkout).filter_by(plan_id=plan.id).all()
            all_exercises_in_plan = [ex for pw in workouts for ex in (pw.exercises or [])]
            names = [ex["name"] for ex in all_exercises_in_plan]

            # Übung per Name suchen (direkt, dann fuzzy)
            target_name = None
            for n in names:
                if exercise_name.lower() in n.lower() or n.lower() in exercise_name.lower():
                    target_name = n
                    break
            if not target_name:
                matches = difflib.get_close_matches(exercise_name, names, n=1, cutoff=0.5)
                target_name = matches[0] if matches else None

            if not target_name:
                dispatcher.utter_message(
                    text=f"Ich konnte '{exercise_name}' in deinem Plan nicht finden. "
                         f"Nenn mir den genauen Übungsnamen wie er im Plan steht."
                )
                return []

            # LLM schlägt eine Alternativübung vor
            equipment = profile_dict.get("equipment") or ["bodyweight"]
            eq_str = ", ".join(equipment)
            alt_name = ask_llm(
                user_message=f"Nenn mir eine einzige Alternativübung für '{target_name}'.",
                system_extra=(
                    f"Antworte NUR mit dem deutschen Übungsnamen, ohne Erklärung oder Satzzeichen. "
                    f"Die Alternative muss dieselben Muskelgruppen trainieren und zu diesem Equipment passen: {eq_str}."
                ),
                max_tokens=20,
            ).strip().strip('"').strip("'").rstrip(".")

            # In allen Workouts per Name ersetzen
            for pw in workouts:
                if not any(e["name"] == target_name for e in (pw.exercises or [])):
                    continue
                pw.exercises = [
                    {**e, "exercise_id": None, "name": alt_name} if e["name"] == target_name else e
                    for e in pw.exercises
                ]

            session.commit()
            dispatcher.utter_message(
                text=f"✓ **{target_name}** wurde durch **{alt_name}** ersetzt — im gesamten Plan angepasst."
            )
        finally:
            session.close()
        return []


class ActionRequestPlan(Action):
    """Handles 'request_plan' intent for both new and returning users.

    New users → starts onboarding form.
    Returning users → creates a fresh plan from existing profile without re-asking anything.
    """
    def name(self) -> Text:
        return "action_request_plan"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        _GOAL_LABELS_LOCAL = {
            "muscle_gain": "Muskelaufbau", "weight_loss": "Abnehmen",
            "general_fitness": "Allgemeine Fitness", "endurance": "Ausdauer", "strength": "Kraft",
        }
        session = get_session()
        try:
            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            if not profile or not profile.onboarded:
                return [FollowupAction("onboarding_form")]

            # Extract goal entity from current message and update profile if present
            entities = tracker.latest_message.get("entities", [])
            goal_entity = next((e["value"] for e in entities if e["entity"] == "goal"), None)
            if goal_entity and goal_entity != profile.goal:
                profile.goal = goal_entity
                session.commit()

            profile_dict = _get_profile_dict(session)
            name_str = f", {profile.name}" if profile.name else ""
            goal_label = _GOAL_LABELS_LOCAL.get(profile.goal or "", "Training")
        finally:
            session.close()

        if get_status().get("status") == "generating":
            dispatcher.utter_message(
                text=f"Ich erstelle gerade schon einen Plan{name_str} — schau im Reiter 'Trainingsplan' nach!"
            )
            return []

        _start_background_generation(profile_dict)
        dispatcher.utter_message(
            text=f"Ich erstelle dir einen frischen {goal_label}-Plan{name_str} — "
                 f"das dauert eine Minute. Schau im Reiter 'Trainingsplan' nach wenn er fertig ist."
        )
        return []


_GREET_NEW = [
    "👋 Hi! Ich bin dein persönlicher FitCoach. Sag 'Los geht's' und wir starten deinen ersten Trainingsplan.",
    "Hey! 💪 Bereit loszulegen? Sag 'Plan erstellen' und wir fangen an.",
    "Hallo! Ich bin dein FitCoach. Sag 'Ich will trainieren' und wir legen los. 🏋️",
]
_GREET_HAS_PLAN_NO_WORKOUT = [
    "Hey{name}! Dein Trainingsplan wartet auf dich — Zeit für die erste Einheit! 💪",
    "Hi{name}! Alles ist vorbereitet. Schau was heute ansteht und leg los! 🏋️",
    "Hey{name}! Der Plan steht, jetzt fehlt nur noch das Training. Auf geht's! 🔥",
]
_GREET_TODAY = [
    "Hey{name}! Heute schon trainiert — stark! 💪",
    "Super gemacht{name}! Heute warst du schon aktiv. 🔥",
    "Respekt{name}! Heute schon eine Einheit abgehakt.",
]
_GREET_RECENT = [
    "Hey{name}! Wie läuft's? Bereit für das nächste Workout? 💪",
    "Moin{name}! Die letzte Einheit liegt hinter dir — ready für mehr?",
    "Hi{name}! Alles fit? Dein nächstes Workout wartet. 🏋️",
]
_GREET_FEW_DAYS = [
    "Hey{name}! Ein paar Tage pausiert — kein Problem. Wieder durchstarten? 💪",
    "Hi{name}! Kurze Pause war gut — jetzt aber wieder ran! 🔥",
    "Hey{name}! Schön dass du wieder da bist. Bereit für das nächste Workout?",
]
_GREET_LONG = [
    "Hey{name}! Schön, dass du wieder da bist. Lass uns weitermachen! 💪",
    "Hi{name}! Lange nicht gesehen — aber jetzt bist du wieder hier. Auf geht's! 🏋️",
    "Willkommen zurück{name}! Jetzt wieder zurück auf Kurs. 🔥",
]


class ActionSmartGreet(Action):
    def name(self) -> Text:
        return "action_smart_greet"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session = get_session()
        try:
            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            if not profile or not profile.onboarded:
                dispatcher.utter_message(text=random.choice(_GREET_NEW))
                return []

            plan = session.query(TrainingPlan).filter_by(user_id=DEMO_USER_ID, active=True).first()
            logs = (
                session.query(WorkoutLog)
                .filter_by(user_id=DEMO_USER_ID)
                .order_by(WorkoutLog.completed_at.desc())
                .all()
            )

            name_part = f" {profile.name}" if profile.name else ""
            days_since: int | None = None
            if logs:
                days_since = (datetime.utcnow() - logs[0].completed_at).days

            # ── Begrüßungstext ────────────────────────────────────────────────
            if days_since is None:
                # Noch kein Workout geloggt
                if plan:
                    greeting = random.choice(_GREET_HAS_PLAN_NO_WORKOUT).format(name=name_part)
                else:
                    greeting = random.choice(_GREET_NEW)
            elif days_since == 0:
                greeting = random.choice(_GREET_TODAY).format(name=name_part)
            elif days_since <= 2:
                greeting = random.choice(_GREET_RECENT).format(name=name_part)
            elif days_since <= 5:
                greeting = random.choice(_GREET_FEW_DAYS).format(name=name_part)
            else:
                greeting = random.choice(_GREET_LONG).format(name=name_part)

            # ── Buttons für die Begrüßung ─────────────────────────────────────
            if days_since == 0:
                # Heute bereits trainiert → nur Workout-Feedback, keine Ablenkung
                dispatcher.utter_message(text=greeting)
                dispatcher.utter_message(
                    text="Wie war das Workout heute?",
                    buttons=[
                        {"title": "💪 Genau richtig", "payload": "/workout_felt_right"},
                        {"title": "😅 Sehr anstrengend", "payload": "/workout_felt_hard"},
                        {"title": "😄 Zu leicht", "payload": "/workout_felt_easy"},
                    ],
                )
            elif days_since is None:
                # Noch kein Workout → zum Start motivieren
                buttons = []
                if plan:
                    buttons.append({"title": "📋 Trainingsplan ansehen", "payload": "/show_plan"})
                dispatcher.utter_message(text=greeting, buttons=buttons)
            elif days_since <= 2:
                dispatcher.utter_message(
                    text=greeting,
                    buttons=[
                        {"title": "📋 Zum Training", "payload": "/show_plan"},
                        {"title": "😴 Brauche noch Erholung", "payload": "/checkin_need_rest"},
                    ],
                )
            elif days_since <= 5:
                dispatcher.utter_message(
                    text=greeting,
                    buttons=[
                        {"title": "🚀 Heute wieder starten", "payload": "/show_plan"},
                        {"title": "Alles gut, danke", "payload": "/checkin_doing_well"},
                    ],
                )
            else:
                dispatcher.utter_message(
                    text=greeting,
                    buttons=[
                        {"title": "🚀 Direkt loslegen", "payload": "/show_plan"},
                    ],
                )

            # ── Übertraining-Erkennung ────────────────────────────────────────
            from datetime import date
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            workout_count = (
                session.query(WorkoutLog)
                .filter(WorkoutLog.user_id == DEMO_USER_ID, WorkoutLog.completed_at >= seven_days_ago)
                .count()
            )
            cardio_count = (
                session.query(CardioLog)
                .filter(CardioLog.user_id == DEMO_USER_ID, CardioLog.logged_at >= seven_days_ago)
                .count()
            )
            strength_count = (
                session.query(StrengthLog)
                .filter(StrengthLog.user_id == DEMO_USER_ID, StrengthLog.logged_at >= seven_days_ago)
                .count()
            )
            total_sessions = workout_count + cardio_count + strength_count
            if total_sessions > 6:
                dispatcher.utter_message(
                    text=f"Übrigens: Du hast diese Woche schon {total_sessions}× trainiert — ein Ruhetag tut dem Körper gut. 💤"
                )

            # ── Genau EINE Follow-up-Frage pro Begrüßung ─────────────────────
            # Priorität: Plan-Feedback (2 Wo.) → Wellbeing → Gewicht
            today = datetime.utcnow().date()

            plan_feedback_sent = False
            if plan and days_since not in (None, 0):
                plan_age_days = (datetime.utcnow() - plan.created_at).days
                last_feedback = profile.plan_feedback_requested_at
                feedback_due = (
                    plan_age_days >= 14
                    and (last_feedback is None or (today - last_feedback).days >= 14)
                )
                if feedback_due:
                    profile.plan_feedback_requested_at = today
                    session.commit()
                    dispatcher.utter_message(response="utter_ask_plan_feedback_2weeks")
                    plan_feedback_sent = True

            last_checked = profile.wellbeing_last_checked
            if not plan_feedback_sent and last_checked != today and days_since != 0:
                dispatcher.utter_message(response="utter_ask_wellbeing")
            elif not plan_feedback_sent and days_since != 0 and profile.goal in ("weight_loss", "muscle_gain"):
                last_weight = (
                    session.query(WeightLog)
                    .filter_by(user_id=DEMO_USER_ID)
                    .order_by(WeightLog.logged_at.desc())
                    .first()
                )
                ask_weight = (
                    last_weight is None
                    or (datetime.utcnow() - last_weight.logged_at).days > 7
                )
                if ask_weight:
                    dispatcher.utter_message(
                        text="Hast du dich kürzlich gewogen? Gib dein aktuelles Gewicht ein (z.B. '75 kg').",
                        buttons=[{"title": "Überspringen", "payload": "/deny"}],
                    )
        finally:
            session.close()
        return []


class ActionLogWeight(Action):
    def name(self) -> Text:
        return "action_log_weight"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        import re
        # Gewichtswert aus Entity oder Freitext extrahieren
        weight = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "weight_value":
                try:
                    weight = float(e.get("value", 0))
                except (ValueError, TypeError):
                    pass
                break

        if weight is None:
            m = re.search(r"\b(\d{2,3}(?:[.,]\d{1,2})?)\b", tracker.latest_message.get("text", ""))
            if m:
                try:
                    weight = float(m.group(1).replace(",", "."))
                except ValueError:
                    pass

        if weight is None or weight < 20 or weight > 300:
            dispatcher.utter_message(text="Das konnte ich nicht als Gewicht erkennen. Versuch es mit z.B. '75 kg'.")
            return []

        session = get_session()
        try:
            session.add(WeightLog(user_id=DEMO_USER_ID, weight_kg=weight))
            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            if profile:
                profile.weight_kg = weight
            session.commit()
        finally:
            session.close()

        dispatcher.utter_message(
            text=f"✅ {weight} kg eingetragen! Du kannst deinen Verlauf im Fortschritt-Tab verfolgen."
        )
        return []


class ActionDefaultFallbackLLM(Action):
    def name(self) -> Text:
        return "action_default_fallback_llm"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        user_msg = tracker.latest_message.get("text", "")
        session = get_session()
        try:
            profile = _get_profile_dict(session)

            # Plan-Kontext für den Coach aufbauen
            plan = session.query(TrainingPlan).filter_by(user_id=DEMO_USER_ID, active=True).first()
            plan_context = ""
            if plan:
                logs = session.query(WorkoutLog).filter_by(user_id=DEMO_USER_ID).all()
                streak = _compute_streak(logs)
                days_since = (datetime.utcnow() - plan.created_at).days
                current_week = min(days_since // 7 + 1, plan.duration_weeks)
                phases = plan.phases or []
                current_phase = next(
                    (p for p in phases if current_week in p.get("weeks", [])), None
                )
                phase_name = current_phase["name"] if current_phase else ""
                plan_context = (
                    f"Aktiver Plan: {plan.name}, "
                    f"Woche {current_week}/{plan.duration_weeks}"
                    + (f", Phase: {phase_name}" if phase_name else "")
                    + f", Streak: {streak} Tage"
                )
        finally:
            session.close()

        history = _get_recent_history(tracker, n=12)
        if history and history[-1]["role"] == "user":
            history = history[:-1]

        system_extra = (
            "Du bist der persönliche Fitness-Coach des Nutzers — rund um die Uhr erreichbar. "
            "Du kennst seinen Plan, sein Ziel und seinen Fortschritt. "
            "Antworte wie ein echter Coach: direkt, motivierend, konkret, auf Augenhöhe. "
            "Du kannst über alles sprechen: Training, Ernährung, Schlaf, Regeneration, Motivation. "
            "Wenn der Nutzer Planänderungen will, erkläre kurz wie (z.B. 'Sag mir einfach was du ändern möchtest'). "
            "Antworte niemals mit 'Ich habe das nicht verstanden' — formuliere stattdessen eine hilfreiche Antwort oder stelle eine Rückfrage."
        )
        if plan_context:
            system_extra += f"\n\nAktueller Status: {plan_context}"

        user_context = {k: v for k, v in profile.items() if v is not None}

        answer = ask_llm(
            user_message=user_msg,
            system_extra=system_extra,
            user_context=user_context,
            history=history,
            max_tokens=600,
        )
        dispatcher.utter_message(text=answer)
        return []


# ── Cardio-Tracking Actions ───────────────────────────────────────────────────

def _extract_number_from_text(text: str) -> float | None:
    import re
    m = re.search(r"\b(\d+(?:[.,]\d+)?)\b", text or "")
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def _extract_duration_from_text(text: str) -> float | None:
    import re
    text_lower = (text or "").lower()
    if "anderthalb" in text_lower:
        return 90.0
    m_h = re.search(r"(\d+(?:[.,]\d+)?)\s*stunde", text_lower)
    if m_h:
        return float(m_h.group(1).replace(",", ".")) * 60
    if "halbe stunde" in text_lower:
        return 30.0
    m_min = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:min|minute|minuten)", text_lower)
    if m_min:
        return float(m_min.group(1).replace(",", "."))
    return _extract_number_from_text(text)


class ActionStartRunningLog(Action):
    def name(self) -> Text:
        return "action_start_running_log"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        # Check if distance was already mentioned in the initial message
        distance = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "distance":
                try:
                    distance = float(str(e.get("value", "")).replace(",", "."))
                except (ValueError, TypeError):
                    pass

        events = [
            SlotSet("cardio_activity_type", "running"),
            SlotSet("awaiting_cardio_distance", True),
            SlotSet("awaiting_cardio_duration", False),
            SlotSet("awaiting_running_type", False),
            SlotSet("awaiting_intensity", False),
            # Strength-Slots zurücksetzen um Slot-Pollution zu vermeiden
            SlotSet("awaiting_strength_exercise", False),
            SlotSet("awaiting_strength_weight", False),
            SlotSet("awaiting_strength_intensity", False),
            SlotSet("strength_log_session", []),
        ]

        if distance is not None:
            events += [
                SlotSet("distance_km", distance),
                SlotSet("awaiting_cardio_distance", False),
                SlotSet("awaiting_cardio_duration", True),
            ]
            dispatcher.utter_message(template="utter_ask_cardio_duration")
        else:
            dispatcher.utter_message(template="utter_ask_distance")

        return events


class ActionStartCyclingLog(Action):
    def name(self) -> Text:
        return "action_start_cycling_log"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        distance = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "distance":
                try:
                    distance = float(str(e.get("value", "")).replace(",", "."))
                except (ValueError, TypeError):
                    pass

        events = [
            SlotSet("cardio_activity_type", "cycling"),
            SlotSet("awaiting_cardio_distance", True),
            SlotSet("awaiting_cardio_duration", False),
            SlotSet("awaiting_running_type", False),
            SlotSet("awaiting_intensity", False),
            # Strength-Slots zurücksetzen um Slot-Pollution zu vermeiden
            SlotSet("awaiting_strength_exercise", False),
            SlotSet("awaiting_strength_weight", False),
            SlotSet("awaiting_strength_intensity", False),
            SlotSet("strength_log_session", []),
        ]

        if distance is not None:
            events += [
                SlotSet("distance_km", distance),
                SlotSet("awaiting_cardio_distance", False),
                SlotSet("awaiting_cardio_duration", True),
            ]
            dispatcher.utter_message(template="utter_ask_cardio_duration")
        else:
            dispatcher.utter_message(template="utter_ask_cycling_distance")

        return events


class ActionHandleCardioDistance(Action):
    def name(self) -> Text:
        return "action_handle_cardio_distance"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        distance = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "distance":
                try:
                    distance = float(str(e.get("value", "")).replace(",", "."))
                except (ValueError, TypeError):
                    pass

        if distance is None:
            distance = _extract_number_from_text(tracker.latest_message.get("text", ""))

        if distance is None:
            dispatcher.utter_message(text="Das hab ich nicht verstanden. Wie viele Kilometer waren es? (z.B. '8 km')")
            return []

        dispatcher.utter_message(template="utter_ask_cardio_duration")
        return [
            SlotSet("distance_km", distance),
            SlotSet("awaiting_cardio_distance", False),
            SlotSet("awaiting_cardio_duration", True),
        ]


class ActionHandleCardioDuration(Action):
    def name(self) -> Text:
        return "action_handle_cardio_duration"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        duration = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "duration_min":
                try:
                    duration = float(str(e.get("value", "")).replace(",", "."))
                except (ValueError, TypeError):
                    pass

        if duration is None:
            duration = _extract_duration_from_text(tracker.latest_message.get("text", ""))

        if duration is None:
            dispatcher.utter_message(text="Wie lange hast du gebraucht? (z.B. '45 Minuten')")
            return []

        activity = tracker.get_slot("cardio_activity_type") or "running"
        events = [
            SlotSet("cardio_duration_min", duration),
            SlotSet("awaiting_cardio_duration", False),
        ]

        if activity == "running":
            events.append(SlotSet("awaiting_running_type", True))
            dispatcher.utter_message(template="utter_ask_running_type")
        else:
            events.append(SlotSet("awaiting_intensity", True))
            dispatcher.utter_message(template="utter_ask_subjective_intensity")

        return events


class ActionHandleRunningType(Action):
    def name(self) -> Text:
        return "action_handle_running_type"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        running_type = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "running_type":
                running_type = e.get("value")

        dispatcher.utter_message(template="utter_ask_subjective_intensity")
        return [
            SlotSet("cardio_running_type", running_type),
            SlotSet("awaiting_running_type", False),
            SlotSet("awaiting_intensity", True),
        ]


class ActionHandleIntensity(Action):
    def name(self) -> Text:
        return "action_handle_intensity"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        intensity = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "subjective_intensity":
                intensity = e.get("value")

        if intensity is None:
            text = (tracker.latest_message.get("text", "") or "").lower()
            if any(w in text for w in ["leicht", "easy", "locker", "einfach"]):
                intensity = "leicht"
            elif any(w in text for w in ["schwer", "hart", "anstrengend", "heavy", "hard"]):
                intensity = "schwer"
            else:
                intensity = "mittel"

        return [
            SlotSet("subjective_intensity", intensity),
            SlotSet("awaiting_intensity", False),
            FollowupAction("action_save_cardio_log"),
        ]


class ActionSaveCardioLog(Action):
    def name(self) -> Text:
        return "action_save_cardio_log"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        activity = tracker.get_slot("cardio_activity_type") or "running"
        distance = tracker.get_slot("distance_km")
        duration = tracker.get_slot("cardio_duration_min")
        running_type = tracker.get_slot("cardio_running_type")
        intensity = tracker.get_slot("subjective_intensity")

        pace = None
        speed = None
        if distance and duration and distance > 0 and duration > 0:
            pace = round(duration / distance, 2)
            speed = round(distance / (duration / 60), 2)

        session = get_session()
        try:
            log = CardioLog(
                user_id=DEMO_USER_ID,
                activity_type=activity,
                distance_km=distance,
                duration_min=duration,
                pace_min_per_km=pace,
                speed_kmh=speed,
                running_type=running_type,
                subjective_intensity=intensity,
            )
            session.add(log)
            session.add(PointsHistory(user_id=DEMO_USER_ID, points=15, reason="cardio_log"))
            session.commit()

            # Vergleich mit letzten 3 Einträgen desselben Typs
            prev = (
                session.query(CardioLog)
                .filter_by(user_id=DEMO_USER_ID, activity_type=activity)
                .order_by(CardioLog.logged_at.desc())
                .offset(1).limit(3).all()
            )
        finally:
            session.close()

        # Feedback aufbauen
        activity_label = "Lauf" if activity == "running" else "Radtour"
        parts = []
        if distance:
            parts.append(f"{distance} km")
        if duration:
            parts.append(f"{int(duration)} min")
        if pace and activity == "running":
            pace_min = int(pace)
            pace_sec = int((pace - pace_min) * 60)
            parts.append(f"{pace_min}:{pace_sec:02d} min/km")
        elif speed and activity == "cycling":
            parts.append(f"{speed:.1f} km/h")

        summary = " · ".join(parts)
        msg = f"✅ {activity_label} eingetragen! {summary} (+15 Punkte)"

        if prev and pace:
            prev_paces = [p.pace_min_per_km for p in prev if p.pace_min_per_km]
            if prev_paces:
                avg_prev = sum(prev_paces) / len(prev_paces)
                if pace < avg_prev * 0.97:
                    msg += "\n🔥 Dein bestes Tempo bisher — stark!"
                elif pace < avg_prev:
                    msg += "\n📈 Etwas schneller als dein Durchschnitt."
                elif pace > avg_prev * 1.05:
                    if running_type in ("locker", None) or intensity == "leicht":
                        msg += "\n👍 Lockere Einheit — Erholung ist auch Training."
                    else:
                        msg += "\n💪 Nicht dein schnellstes, aber du warst dabei!"

        if intensity == "schwer" and running_type == "locker":
            msg += "\n⚠️ Für einen lockeren Lauf war das schon ganz schön intensiv — gönn dir morgen Pause."

        dispatcher.utter_message(text=msg)

        return [
            SlotSet("cardio_activity_type", None),
            SlotSet("distance_km", None),
            SlotSet("cardio_duration_min", None),
            SlotSet("cardio_running_type", None),
            SlotSet("subjective_intensity", None),
            SlotSet("awaiting_cardio_distance", False),
            SlotSet("awaiting_cardio_duration", False),
            SlotSet("awaiting_running_type", False),
            SlotSet("awaiting_intensity", False),
        ]


# ── Krafttraining-Tracking ────────────────────────────────────────────────────

import re as _re


def _parse_weight_reps_sets(text: str):
    """Extrahiert weight_kg, reps, sets aus Freitext in verschiedenen Formaten.

    Unterstützte Formate:
      "3x10 mit 60kg"  →  sets=3, reps=10, weight_kg=60
      "60kg 3 mal 10"  →  weight_kg=60, sets=3, reps=10
      "10 Wiederholungen" (kein Gewicht) → reps=10, rest=None
    """
    text = text.lower()

    weight = None
    reps = None
    sets = None

    # Gewicht: "60 kg", "60kg", "60 kilo"
    m = _re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo)', text)
    if m:
        weight = float(m.group(1).replace(',', '.'))

    # Format "3x10" oder "3×10" oder "3 x 10"
    m = _re.search(r'(\d+)\s*[x×]\s*(\d+)', text)
    if m:
        sets = int(m.group(1))
        reps = int(m.group(2))

    if reps is None:
        # "3 mal 10" oder "3 sätze 10"
        m = _re.search(r'(\d+)\s*(?:mal|sätze?|sets?|durchgänge?)\s+(\d+)', text)
        if m:
            sets = int(m.group(1))
            reps = int(m.group(2))

    if reps is None:
        # "10 wiederholungen" oder "10 reps"
        m = _re.search(r'(\d+)\s*(?:wiederholungen?|reps?|wdh)', text)
        if m:
            reps = int(m.group(1))

    if sets is None:
        # "3 sätze" solo
        m = _re.search(r'(\d+)\s*(?:sätze?|sets?|durchgänge?)', text)
        if m:
            sets = int(m.group(1))

    return weight, reps, sets


class ActionStartStrengthLog(Action):
    def name(self) -> Text:
        return "action_start_strength_log"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        # Prüfen ob in der ersten Nachricht bereits eine Übung genannt wurde
        exercise = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "strength_exercise":
                exercise = e.get("value", "").strip()
                break

        if exercise:
            dispatcher.utter_message(
                text=f"Alright, {exercise} — wie viel Gewicht und wie viele Wiederholungen? "
                     f"(z.B. '60 kg, 3×10')"
            )
            return [
                SlotSet("strength_exercise_name", exercise),
                SlotSet("strength_log_session", []),
                SlotSet("awaiting_strength_exercise", False),
                SlotSet("awaiting_strength_weight", True),
            ]

        dispatcher.utter_message(response="utter_ask_exercise_name")
        return [
            SlotSet("strength_log_session", []),
            SlotSet("awaiting_strength_exercise", True),
            SlotSet("awaiting_strength_weight", False),
            SlotSet("awaiting_strength_reps_sets", False),
            SlotSet("awaiting_strength_intensity", False),
            # Cardio-Slots zurücksetzen um Slot-Pollution zu vermeiden
            SlotSet("awaiting_cardio_distance", False),
            SlotSet("awaiting_cardio_duration", False),
            SlotSet("awaiting_running_type", False),
            SlotSet("awaiting_intensity", False),
            SlotSet("cardio_activity_type", None),
        ]


class ActionHandleExerciseName(Action):
    def name(self) -> Text:
        return "action_handle_exercise_name"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        exercise = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "strength_exercise":
                exercise = e.get("value", "").strip()
                break
        if not exercise:
            exercise = tracker.latest_message.get("text", "").strip()

        if not exercise:
            dispatcher.utter_message(response="utter_ask_exercise_name")
            return []

        dispatcher.utter_message(response="utter_ask_weight_reps")
        return [
            SlotSet("strength_exercise_name", exercise),
            SlotSet("awaiting_strength_exercise", False),
            SlotSet("awaiting_strength_weight", True),
        ]


class ActionHandleWeightReps(Action):
    def name(self) -> Text:
        return "action_handle_weight_reps"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        text = tracker.latest_message.get("text", "")
        weight, reps, sets = _parse_weight_reps_sets(text)

        # Fallback auf Slot-Entities falls Regex nichts findet
        if weight is None:
            for e in tracker.latest_message.get("entities", []):
                if e.get("entity") == "weight_kg":
                    try:
                        weight = float(str(e.get("value", "")).replace(',', '.'))
                    except (ValueError, TypeError):
                        pass
        if reps is None:
            for e in tracker.latest_message.get("entities", []):
                if e.get("entity") == "reps":
                    try:
                        reps = int(e.get("value", 0))
                    except (ValueError, TypeError):
                        pass
        if sets is None:
            for e in tracker.latest_message.get("entities", []):
                if e.get("entity") == "sets":
                    try:
                        sets = int(e.get("value", 0))
                    except (ValueError, TypeError):
                        pass

        if reps is None and weight is None:
            dispatcher.utter_message(
                text="Ich hab das nicht ganz verstanden. Sag es so: '60 kg, 3×10' oder '3 Sätze à 8 Reps'."
            )
            return []

        dispatcher.utter_message(response="utter_ask_subjective_intensity")
        return [
            SlotSet("strength_weight_kg", weight),
            SlotSet("strength_reps", reps),
            SlotSet("strength_sets", sets),
            SlotSet("awaiting_strength_weight", False),
            SlotSet("awaiting_strength_intensity", True),
        ]


class ActionHandleStrengthIntensity(Action):
    def name(self) -> Text:
        return "action_handle_strength_intensity"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        intensity = None
        for e in tracker.latest_message.get("entities", []):
            if e.get("entity") == "subjective_intensity":
                intensity = e.get("value", "").strip().lower()
                break
        if not intensity:
            txt = tracker.latest_message.get("text", "").lower()
            if any(w in txt for w in ("leicht", "easy", "locker")):
                intensity = "leicht"
            elif any(w in txt for w in ("schwer", "hart", "anstrengend", "intensiv")):
                intensity = "schwer"
            else:
                intensity = "mittel"

        # Aktuelle Übung in die Session-Liste aufnehmen
        exercise = tracker.get_slot("strength_exercise_name") or "Unbekannte Übung"
        weight = tracker.get_slot("strength_weight_kg")
        reps = tracker.get_slot("strength_reps")
        sets = tracker.get_slot("strength_sets")

        session_log = list(tracker.get_slot("strength_log_session") or [])
        session_log.append({
            "exercise": exercise,
            "weight_kg": weight,
            "reps": int(reps) if reps else None,
            "sets": int(sets) if sets else None,
            "subjective_intensity": intensity,
        })

        dispatcher.utter_message(response="utter_ask_more_exercises")
        return [
            SlotSet("strength_log_session", session_log),
            SlotSet("subjective_intensity", intensity),
            SlotSet("awaiting_strength_intensity", False),
            SlotSet("awaiting_strength_exercise", True),
            SlotSet("strength_exercise_name", None),
            SlotSet("strength_weight_kg", None),
            SlotSet("strength_reps", None),
            SlotSet("strength_sets", None),
        ]


class ActionSaveStrengthLog(Action):
    def name(self) -> Text:
        return "action_save_strength_log"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        session_log = tracker.get_slot("strength_log_session") or []

        if not session_log:
            dispatcher.utter_message(text="Keine Übungen zum Speichern — starte einfach neu wenn du bereit bist.")
            return []

        session = get_session()
        try:
            for entry in session_log:
                session.add(StrengthLog(
                    user_id=DEMO_USER_ID,
                    logged_at=datetime.utcnow(),
                    exercise=entry["exercise"],
                    weight_kg=entry.get("weight_kg"),
                    reps=entry.get("reps"),
                    sets=entry.get("sets"),
                    subjective_intensity=entry.get("subjective_intensity"),
                ))
            session.add(PointsHistory(user_id=DEMO_USER_ID, points=10 * len(session_log), reason="strength_log"))
            session.commit()
        finally:
            session.close()

        points = 10 * len(session_log)
        lines = []
        for e in session_log:
            parts = []
            if e.get("sets") and e.get("reps"):
                parts.append(f"{e['sets']}×{e['reps']}")
            elif e.get("reps"):
                parts.append(f"{e['reps']} Reps")
            if e.get("weight_kg"):
                parts.append(f"{e['weight_kg']} kg")
            desc = " · ".join(parts)
            lines.append(f"• {e['exercise']}" + (f" ({desc})" if desc else ""))

        summary = "\n".join(lines)
        dispatcher.utter_message(
            text=f"💪 Krafteinheit gespeichert! (+{points} Punkte)\n\n{summary}"
        )

        return [
            SlotSet("strength_log_session", []),
            SlotSet("strength_exercise_name", None),
            SlotSet("strength_weight_kg", None),
            SlotSet("strength_reps", None),
            SlotSet("strength_sets", None),
            SlotSet("subjective_intensity", None),
            SlotSet("awaiting_strength_exercise", False),
            SlotSet("awaiting_strength_weight", False),
            SlotSet("awaiting_strength_reps_sets", False),
            SlotSet("awaiting_strength_intensity", False),
        ]


# ── Daily Check-in / Wellbeing ────────────────────────────────────────────────

class ActionSaveWellbeing(Action):
    def name(self) -> Text:
        return "action_save_wellbeing"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict) -> List:
        feeling = tracker.get_slot("wellbeing") or ""

        # Normalisierung (Button-Payload-Werte + Freitext)
        feeling_lower = feeling.lower().strip()
        if any(w in feeling_lower for w in ("gut", "super", "top", "prima", "toll", "great")):
            category = "gut"
        elif any(w in feeling_lower for w in ("ok", "okay", "ganz", "so lala", "mittel")):
            category = "ok"
        elif any(w in feeling_lower for w in ("müde", "erschöpft", "k.o.", "schlapp", "tired")):
            category = "müde"
        elif any(w in feeling_lower for w in ("schlecht", "nicht gut", "mies", "krank", "bad")):
            category = "schlecht"
        else:
            category = "ok"

        response_map = {
            "gut":      "utter_wellbeing_good",
            "ok":       "utter_wellbeing_ok",
            "müde":     "utter_wellbeing_tired",
            "schlecht": "utter_wellbeing_bad",
        }
        dispatcher.utter_message(response=response_map[category])

        # wellbeing_last_checked auf heute setzen
        from datetime import date
        session = get_session()
        try:
            profile = session.query(Profile).filter_by(user_id=DEMO_USER_ID).first()
            if profile:
                profile.wellbeing_last_checked = date.today()
                session.commit()
        finally:
            session.close()

        return [SlotSet("wellbeing", None)]
