"""
Level-System und Badge-Definitionen.
Zentrale Stelle für alle Gamification-Logik.
"""

# ── Level-System ──────────────────────────────────────────────────────────────
LEVELS = [
    {"name": "Rookie",       "min_points": 0,    "icon": "🌱"},
    {"name": "Amateur",      "min_points": 100,  "icon": "💪"},
    {"name": "Fitness-Fan",  "min_points": 300,  "icon": "🔥"},
    {"name": "Athlet",       "min_points": 600,  "icon": "⚡"},
    {"name": "Pro",          "min_points": 1000, "icon": "🏆"},
    {"name": "Elite",        "min_points": 1500, "icon": "👑"},
]


def get_level(total_points: int) -> dict:
    """Gibt das aktuelle Level zurück und wie viele Punkte bis zum nächsten."""
    current = LEVELS[0]
    next_level = None
    for i, lvl in enumerate(LEVELS):
        if total_points >= lvl["min_points"]:
            current = lvl
            next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    points_to_next = (next_level["min_points"] - total_points) if next_level else 0
    return {
        "name": current["name"],
        "icon": current["icon"],
        "points_to_next": points_to_next,
        "next_level_name": next_level["name"] if next_level else None,
    }


# ── Badge-Definitionen ────────────────────────────────────────────────────────
BADGES = {
    # Workout-Meilensteine
    "first_workout":      {"title": "Erster Schritt",      "desc": "Erstes Workout abgeschlossen",          "icon": "🎯"},
    "workouts_5":         {"title": "Auf Kurs",             "desc": "5 Workouts abgeschlossen",              "icon": "⭐"},
    "workouts_10":        {"title": "Zweistellig",          "desc": "10 Workouts abgeschlossen",             "icon": "🔟"},
    "workouts_25":        {"title": "Seriös dabei",         "desc": "25 Workouts abgeschlossen",             "icon": "🥉"},
    "workouts_50":        {"title": "Halbhundert",          "desc": "50 Workouts abgeschlossen",             "icon": "🥈"},
    "workouts_100":       {"title": "Jahrhundert",          "desc": "100 Workouts abgeschlossen",            "icon": "🥇"},

    # Streak-Badges
    "streak_3":           {"title": "3 Tage am Stück",     "desc": "3 Tage hintereinander trainiert",       "icon": "🔥"},
    "streak_7":           {"title": "Woche durch",         "desc": "7 Tage hintereinander trainiert",       "icon": "🔥🔥"},
    "streak_14":          {"title": "Zwei Wochen",         "desc": "14 Tage hintereinander trainiert",      "icon": "🔥🔥🔥"},
    "streak_30":          {"title": "Unaufhaltbar",        "desc": "30 Tage hintereinander trainiert",      "icon": "💎"},

    # Plan & Ziel
    "plan_started":       {"title": "Planmäßig",           "desc": "Ersten Trainingsplan erstellt",         "icon": "📋"},
    "plan_completed":     {"title": "Durchgehalten",       "desc": "Gesamten Trainingsplan abgeschlossen",  "icon": "🏁"},

    # Bonus-Badges
    "early_bird":         {"title": "Frühaufsteher",       "desc": "Workout vor 8 Uhr morgens",             "icon": "🌅"},
    "weekend_warrior":    {"title": "Weekend Warrior",     "desc": "Workout am Wochenende absolviert",      "icon": "⚔️"},
    "consistency_4w":     {"title": "Beständig",           "desc": "4 Wochen lang mind. 3× trainiert",      "icon": "📅"},
    "pb_set":             {"title": "Persönliche Bestzeit","desc": "Neue persönliche Bestleistung gesetzt",  "icon": "📈"},
}


# ── Punkte-Vergabe ────────────────────────────────────────────────────────────
POINTS = {
    "workout_completed": 20,
    "streak_bonus":      10,   # pro Tag Streak
    "onboarding":        50,
    "badge_earned":      5,
}


def check_badges(total_workouts: int, streak: int, existing_badge_keys: set) -> list[str]:
    """Gibt Liste neuer Badge-Keys zurück die der Nutzer jetzt verdient hat."""
    new_badges = []

    workout_milestones = {1: "first_workout", 5: "workouts_5", 10: "workouts_10",
                          25: "workouts_25", 50: "workouts_50", 100: "workouts_100"}
    for count, key in workout_milestones.items():
        if total_workouts >= count and key not in existing_badge_keys:
            new_badges.append(key)

    streak_milestones = {3: "streak_3", 7: "streak_7", 14: "streak_14", 30: "streak_30"}
    for days, key in streak_milestones.items():
        if streak >= days and key not in existing_badge_keys:
            new_badges.append(key)

    return new_badges
