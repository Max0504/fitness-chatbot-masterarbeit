# FitCoach — Spezifikation

Technische und fachliche Spezifikation des Prototyps zur Masterarbeit
*„Konzeption und prototypische Umsetzung eines Fitness-Chatbots"*
(Universität Regensburg, Lehrstuhl für Wirtschaftsinformatik).

Dieses Dokument beschreibt **was** gebaut wurde, **wie** es aufgebaut ist und **warum** die zentralen Entscheidungen so getroffen wurden. Anleitung zu Installation und Betrieb: siehe `README.md`.

---

## 1. Zielsetzung

FitCoach ist ein konversationaler Fitness-Coach als Web-Anwendung. Über einen Chat führt das System den Nutzer durch ein kurzes Onboarding, erstellt einen personalisierten und
phasenbasierten Trainingsplan, protokolliert Workouts sowie Lauf-, Rad- und Krafteinheiten und visualisiert Fortschritt und Motivation über Dashboard, Fortschritts- und Ernährungsansichten.

Die Anwendung ist als **Einzelnutzer-Prototyp** konzipiert: kein Login, ein fester Demo-Nutzer
(`id = 1`). Der Fokus liegt auf der Demonstration der konzeptionellen Beiträge der Arbeit, nicht
auf Produktivbetrieb.

**Leitidee:** klare Trennung der Verantwortlichkeiten zwischen einer regelbasierten
Dialogsteuerung (Rasa) und einem großen Sprachmodell (Google Gemini). Rasa sorgt für Struktur,
Determinismus und Datenzugriff; das LLM übernimmt kreative, kontextsensitive und schwer
schematisierbare Antworten.

---

## 2. Technologiestack

| Schicht | Technologie | Version |
|---|---|---|
| Dialogsteuerung / NLU | Rasa Open Source | 3.6.20 (rasa-sdk 3.6.2) |
| Sprachmodell (LLM) | Google Gemini (Free Tier) | `gemini-2.5-flash-lite` |
| Backend-API | FastAPI + Uvicorn | FastAPI ≥ 0.110 |
| ORM / Datenbank | SQLAlchemy + SQLite | 2.x (Backend) / 1.4 (Rasa) |
| Frontend | React + TypeScript + Vite | React 18.3, TS 5.5, Vite 5.4 |
| Styling / Charts | TailwindCSS / Recharts | Tailwind 3.4 |
| Laufzeit | Python / Node.js | Python 3.10.20 / Node ≥ 18 |

Die beiden Python-Umgebungen sind bewusst getrennt (siehe Abschnitt 12, Designentscheidungen).

---

## 3. Systemarchitektur

```
┌───────────────────────────────────────────────────────────┐
│  Browser  (http://localhost:5173)                          │
│  React + TypeScript + TailwindCSS                          │
│  Ansichten: Chat · Plan · Dashboard · Fortschritt ·        │
│             Ernährung · Profil                             │
└───────────┬───────────────────────────┬───────────────────┘
            │                           │
   Chat-Nachrichten              REST-API-Calls
   POST /webhooks/rest/webhook   GET/PATCH /api/...
            │                           │
            ▼                           ▼
┌───────────────────────┐   ┌───────────────────────────────┐
│ Rasa Server  :5005    │   │ FastAPI Backend  :8000        │
│ NLU + Dialogsteuerung │   │ Profil, Plan, Dashboard,      │
│ Intent-Erkennung      │   │ Tracking, Fortschritt         │
└───────────┬───────────┘   └──────────────┬────────────────┘
            │                              │
            ▼                              ▼
┌───────────────────────┐   ┌───────────────────────────────┐
│ Rasa Action Server    │   │ SQLite  data/fitness.db        │
│ :5055                 │──►│ (von beiden Diensten geteilt) │
│ Python-Logik, DB,     │   └───────────────────────────────┘
│ LLM-Aufrufe           │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Google Gemini API      │
│ (Cloud)                │
└───────────────────────┘
```

Backend und Rasa Action Server greifen auf **dieselbe** SQLite-Datenbank zu. Das Frontend
kommuniziert zweigleisig: Chat-Nachrichten gehen an Rasa, alle strukturierten Daten
(Profil, Plan, Statistiken) an die FastAPI-REST-Schnittstelle.

---

## 4. Hybrid-Prinzip: Rasa vs. LLM

Das zentrale Gestaltungsprinzip ist die Aufgabenteilung **„Rasa für Struktur, LLM für
Kreativität"**. Strukturierte Aufgaben brauchen kein Sprachmodell — sie wären damit langsamer,
teurer und weniger zuverlässig. Das LLM kommt nur dort zum Einsatz, wo es echten Mehrwert
liefert.

| Aufgabe | Komponente | Begründung |
|---|---|---|
| Begrüßung, Bestätigungen, Smalltalk | Rasa (Templates) | Konsistenz, kein API-Verbrauch |
| Onboarding-Flow | Rasa (Form / Slot-Filling) | strukturierte Dateneingabe |
| Intent-Erkennung | Rasa (NLU) | deterministisch, < 200 ms |
| Workout loggen, Plan anzeigen, Punkte | Rasa (Custom Actions) | strukturierter DB-Zugriff |
| Übungen erklären | LLM (Gemini) | beliebige Übungen, freie Erklärung |
| Motivation auf Anfrage | LLM (Gemini) | individuelle, abwechslungsreiche Texte |
| Ernährungstipps | LLM (Gemini) | zu vielfältig für feste Templates |
| Trainingsplan generieren | LLM (Gemini) | personalisierter JSON-Plan |
| Plan-Anpassung im Dialog | LLM + Rasa | LLM versteht Wunsch, Rasa setzt ihn um |
| Fallback bei unbekannter Eingabe | LLM (Gemini) | Sicherheitsnetz |

| | Rasa | Gemini |
|---|---|---|
| **Rolle** | Gesprächssteuerung, Abläufe, DB | inhaltliche/freie Antworten |
| **Entscheidet** | welche Action ausgeführt wird | was die Antwort sagt |
| **Latenz** | < 200 ms | ca. 2–30 s |

**Austauschbarkeit des LLM:** Die gesamte LLM-Anbindung ist in einer einzigen Datei gekapselt
(`rasa/actions/llm_client.py`, öffentliche Funktion `ask_llm()`). Ein Wechsel zu einem anderen
Anbieter (z. B. OpenAI, Anthropic) oder einem lokalen Modell (z. B. via Ollama) betrifft nur
diese Datei plus API-Key in `.env`; der übrige Code bleibt unverändert. Über
`PLAN_USE_GEMINI=true/false` lässt sich die Plangenerierung zwischen LLM und einem
algorithmischen Fallback (`plan_generator.py`) umschalten.

---

## 5. Funktionsumfang

### 5.1 Onboarding
Beim ersten Start führt Rasa den Nutzer per Form durch die Abfrage von Name, Trainingsziel
(Muskelaufbau, Abnehmen, Ausdauer, Allgemeine Fitness, Kraft), Fitnesslevel, Trainingstagen pro
Woche, Equipment, Verletzungen/Einschränkungen und einem optionalen spezifischen Ziel (Freitext,
z. B. „10 km in 3 Monaten"). Der Abschluss bringt 50 Bonuspunkte und startet automatisch die
Plangenerierung. Kein LLM beteiligt.

### 5.2 Trainingsplan-Generierung
Gemini erzeugt einen personalisierten Plan als strukturiertes JSON. Berücksichtigt werden Ziel,
Fitnesslevel, Equipment, Verletzungen, biometrische Daten (Alter, Gewicht, Größe, BMI,
Geschlecht) sowie ein optionales Zieldatum, aus dem sich eine dynamische Planlänge (ca. 2–16
Wochen) mit progressiver Phasenstruktur und ggf. Tapering-Woche ableitet. Der Plan enthält
Planname, Zielbeschreibung, mehrere Phasen (Name, Beschreibung, Wochenbereich), Workouts pro
Woche (Tag, Übungen, Sätze, Wiederholungen, Pausen) und eine Coach-Erklärung. Die Generierung
läuft **asynchron im Hintergrund**; das Frontend pollt den Status alle 3 Sekunden.

### 5.3 Plan-Ansicht & Übungstausch
Die Plan-Ansicht zeigt Phasen-Auswahl, Wochen-Tabs (aktuelle Woche vorausgewählt) und
Workout-Karten je Trainingstag mit aufklappbaren Übungen. Pro Übung gibt es einen Swap-Button:
Gemini wählt anhand von Equipment, Ziel und Muskelgruppe eine Alternative und ersetzt die Übung
konsistent im gesamten Plan.

### 5.4 Tracking
Plan-Workouts werden per Button abgeschlossen (Log, Punkte, Badge- und Level-Prüfung).
Zusätzlich lassen sich Aktivitäten direkt im Chat protokollieren:
- **Laufen:** Distanz → Dauer → Lauftyp → Intensität; Pace/Geschwindigkeit werden berechnet.
- **Radfahren:** Distanz → Dauer → Intensität.
- **Krafttraining (frei):** Übung → Gewicht & Wiederholungen → Sätze → Intensität; mehrere
  Übungen nacheinander möglich.
- **Gewicht:** wird gespeichert und im Fortschritts-Graph angezeigt.

Cardio-Eingaben werden sowohl als „5 km" als auch „5km" erkannt; bei unklarer Klassifikation
extrahiert ein Fallback die Zahl direkt aus dem Text.

### 5.5 Gamification
Punkte, Level und Badges motivieren zur regelmäßigen Nutzung (Regeln siehe Abschnitt 11). Neue
Badges und Level-Ups erscheinen als Popup direkt nach dem Workout; erst nach Bestätigung
wechselt die App in den Chat und fragt nach dem Trainingsgefühl, worauf der Plan optional
angepasst wird.

### 5.6 Dashboard & Fortschritt
Das Dashboard zeigt Gesamtpunkte und Level (mit Fortschrittsbalken), aktuellen Streak, Anzahl
Workouts, Gesamtkilometer, verdiente Badges, die letzten Aktivitäten sowie Lauf-Statistiken
(Ø-Pace, Bestzeit, Pace-Trend). Die Fortschritts-Ansicht visualisiert Gewichts- und
Cardio-Verlauf als Liniendiagramme. Beide aktualisieren sich automatisch, wenn im Chat eine
Aktivität eingetragen oder im Profil das Gewicht geändert wird.

### 5.7 Ernährung
Die Ernährungs-Ansicht zeigt tagesaktuelle, LLM-generierte Tipps auf Basis von Profil und Ziel
(täglich variierend über einen Datums-Hash), sichtbar sobald ein aktiver Plan existiert.
Alternativ beantwortet Gemini Ernährungsfragen kontextsensitiv im Chat.

### 5.8 Proaktive Interaktionen
Die Begrüßung ist kontextabhängig (`action_smart_greet`): Je nach Trainingshistorie fällt sie
unterschiedlich aus, und der Bot stößt bei Bedarf proaktive Checks an — Plan-Feedback nach
14 Tagen, gelegentlicher Wellbeing-Check und, bei Abnehm-/Muskelaufbau-Zielen, eine wöchentliche
Gewichtsabfrage. Die Antworten lösen automatisch passende Plan-Anpassungen aus.

### 5.9 Wissen: Übungserklärung & Motivation
Fragen wie „Was ist ein Burpee?" oder „Motivier mich" lösen einen LLM-Aufruf aus. Gemini
antwortet unter Einbezug von Profil, Trainingshistorie, Streak und Ziel.

---

## 6. Rasa-Komponenten

### 6.1 Intents (45)
Die NLU erkennt 45 Intents, gruppiert nach Funktion:

- **Grundlegendes:** `greet`, `goodbye`, `affirm`, `deny`, `thank`, `bot_capabilities`, `chitchat`
- **Onboarding:** `start_onboarding`, `inform_name`, `inform_goal`, `inform_fitness_level`,
  `inform_days_per_week`, `inform_equipment`, `inform_injuries`, `no_specific_goal`
- **Planung:** `request_plan`, `show_plan`, `modify_plan`, `change_goal`, `swap_exercise`
- **Tracking / Dashboard:** `log_workout`, `inform_weight`, `show_dashboard`
- **Cardio-Dialog:** `log_running`, `log_cycling`, `provide_distance`, `provide_duration`,
  `provide_running_type`, `provide_subjective_intensity`, `provide_activity_date`
- **Kraft-Dialog:** `log_strength`, `provide_exercise_name`, `provide_weight_reps`,
  `provide_strength_sets`, `confirm_more_exercises`, `deny_more_exercises`
- **Feedback / Check-in:** `workout_felt_easy`, `workout_felt_right`, `workout_felt_hard`,
  `checkin_doing_well`, `checkin_need_rest`, `update_wellbeing`
- **Wissen:** `ask_nutrition`, `ask_exercise_info`, `ask_motivation`

### 6.2 NLU-Pipeline & Policies
Sprache: Deutsch. Pipeline: `WhitespaceTokenizer` → `RegexFeaturizer` →
`LexicalSyntacticFeaturizer` → `CountVectorsFeaturizer` (Wort- und Zeichen-n-Gramme, char_wb
1–4) → `DIETClassifier` (100 Epochen) → `EntitySynonymMapper` → `ResponseSelector` →
`FallbackClassifier` (Schwelle 0.5, Ambiguitätsschwelle 0.1).
Policies: `MemoizationPolicy`, `RulePolicy` (Core-Fallback-Schwelle 0.4, Fallback-Action
`action_default_fallback_llm`), `TEDPolicy` (max_history 5, 100 Epochen).

### 6.3 Slots (Auszug)
Der wichtigste steuernde Slot ist `onboarded` (bool): Er unterscheidet Erstnutzer von
Rückkehrern und bestimmt, ob eine Plan-Anfrage ins Onboarding oder direkt in die Generierung
führt. Weitere Slots (`goal`, `fitness_level`, `days_per_week`, `user_equipment`,
`user_injuries`, `specific_goal`, `user_name`) halten die Profildaten während des Dialogs.

### 6.4 Custom Actions (28)
Die Geschäftslogik liegt in `rasa/actions/actions.py`.

| Action | Funktion |
|---|---|
| `action_smart_greet` | kontextuelle Begrüßung, proaktive Checks |
| `action_check_onboarding_status` | Onboarding-Status prüfen |
| `action_ask_specific_goal` | spezifisches Ziel abfragen |
| `action_create_training_plan` | Plan nach LLM-Generierung in DB schreiben |
| `action_request_plan` | Plan-Anfrage verarbeiten, Ziel extrahieren |
| `action_show_plan` | aktuellen Plan als Text ausgeben |
| `action_modify_plan` | Plan-Anpassung (LLM) + DB-Update |
| `action_swap_exercise` | Übungstausch (LLM) |
| `action_log_workout` | Workout-Log, Punkte, Badge-/Level-Prüfung |
| `action_log_weight` | Gewicht speichern |
| `action_start_running_log` / `action_start_cycling_log` | Cardio-Dialog starten |
| `action_handle_cardio_distance` / `_duration` / `action_handle_running_type` / `action_handle_intensity` | Cardio-Eingaben verarbeiten |
| `action_save_cardio_log` | Cardio-Eintrag speichern |
| `action_start_strength_log` | Kraft-Dialog starten |
| `action_handle_exercise_name` / `action_handle_weight_reps` / `action_handle_strength_intensity` | Kraft-Eingaben verarbeiten |
| `action_save_strength_log` | Krafteintrag speichern |
| `action_save_wellbeing` | Wohlbefinden speichern |
| `action_show_dashboard_summary` | Dashboard-Zusammenfassung im Chat |
| `action_explain_exercise` | Übungserklärung (LLM) |
| `action_motivate` | Motivationstext (LLM) |
| `action_nutrition_advice` | Ernährungstipp (LLM) |
| `action_default_fallback_llm` | unbekannte Eingaben per LLM beantworten |

Unterstützende Module: `llm_client.py` (LLM-Kapselung), `plan_generator.py` (algorithmischer
Plan-Fallback), `plan_status.py` (geteilte Statusdatei für die Hintergrundgenerierung),
`db.py` (DB-Zugriff im Rasa-Kontext).

---

## 7. Datenmodell

SQLite (`data/fitness.db`), via SQLAlchemy-ORM. Die Tabellen werden beim Start automatisch
angelegt (kein Migrationswerkzeug). Backend und Rasa teilen sich dieselben Modelle
(`backend/models.py`).

| Tabelle | Inhalt |
|---|---|
| `users` | Demo-Nutzer (`id = 1`) |
| `profiles` | Profil- und Zieldaten |
| `training_plans` | aktive und frühere Pläne (Phasen als JSON) |
| `plan_workouts` | einzelne Workout-Einheiten (Übungen als JSON) |
| `workout_logs` | abgeschlossene Plan-Workouts (mit RPE, Stimmung) |
| `cardio_logs` | Lauf-/Radeinträge (Distanz, Dauer, Pace, Typ) |
| `strength_logs` | freie Krafteinheiten (Übung, Gewicht, Wiederholungen) |
| `weight_logs` | Gewichtsverlauf |
| `performance_logs` | Leistungsdaten (z. B. 5-km-Zeit, Max-Wiederholungen) |
| `points_history` | alle Punkte-Ereignisse |
| `badges` | verdiente Abzeichen (mit `seen`-Flag) |

---

## 8. REST-API (FastAPI)

Acht Router unter dem Präfix `/api`:

| Router | Präfix | Zweck |
|---|---|---|
| profile | `/api/profile` | Profil laden (`GET`) / aktualisieren (`PATCH`, löst bei Gewichtsänderung einen Weight-Log aus) |
| plan | `/api/plan` | aktiven Plan laden, Generierungsstatus abfragen |
| workouts | `/api/workouts` | Workout eintragen (liefert Punkte, Badges, Level-Up), Verlauf |
| dashboard | `/api/dashboard` | Punkte, Level, Streak, Badge-Anzahl |
| activity | `/api/activity` | letzte Aktivitäten, Cardio- und Kraft-Statistiken |
| progress | `/api/progress` | Gewichts-, Cardio- und Leistungsverlauf |
| nutrition | `/api/nutrition` | tagesaktuelle Ernährungstipps (LLM) |
| exercises | `/api/exercises` | Übungskatalog |

---

## 9. Frontend

React + TypeScript (Vite). Ansichten unter `frontend/src/components/`:
Chat, Dashboard, Plan, Progress, Profile, Nutrition, Tutorial sowie die Rahmen-Komponenten
Layout, Sidebar und Toast. API-Aufrufe sind zentral gebündelt (`src/api/`); Typen in
`src/types/`.

**Cross-Component-Kommunikation** über Custom Events (statt tiefem Prop-Durchreichen):

| Event | Auslöser | Reaktion |
|---|---|---|
| `activity_logged` | Chat nach passender Bot-Antwort | Dashboard / Aktivitäten / Cardio-Statistik neu laden |
| `workout_completed` | Workout-Karte nach Popup-Bestätigung | Wechsel in den Chat, automatische Rückfrage zum Gefühl |
| `weight_updated` | Profil nach Speichern | Fortschritts-Graph neu laden |

---

## 10. LLM-Anbindung, Konfiguration & Logging

Die gesamte LLM-Logik ist in `rasa/actions/llm_client.py` isoliert (öffentliche Funktion
`ask_llm()`), was Provider-Wechsel auf eine Datei begrenzt. Konfiguration über `.env`:

| Variable | Bedeutung |
|---|---|
| `GEMINI_API_KEY` | API-Schlüssel (Google AI Studio, Free Tier) |
| `LLM_MODEL` | verwendetes Modell, Standard `models/gemini-2.5-flash-lite` |
| `DATABASE_URL` | SQLite-Pfad, Standard `sqlite:///./data/fitness.db` |
| `PLAN_USE_GEMINI` | Plangenerierung per LLM (`true`) oder algorithmisch (`false`) |

Jeder LLM-Aufruf wird in `data/logs/events.jsonl` protokolliert (Zeitstempel, Dauer in ms,
Ausgabe-Token, Modus). Daraus lassen sich für die Evaluation u. a. Antwortzeiten (Rasa-only vs.
LLM-Actions), Fallback-Rate, Token-Verbrauch je Aufgabentyp und Plangenerierungszeit ableiten.


---

## 11. Gamification-Regeln

**Punkte:** Onboarding-Abschluss +50 · Workout +20 · Streak-Bonus +10 (pro Streak-Tag) ·
Badge +5.

**Level (6 Stufen, nach Gesamtpunkten):**

| Level | ab Punkten | Icon |
|---|---|---|
| Rookie | 0 | 🌱 |
| Amateur | 100 | 💪 |
| Fitness-Fan | 300 | 🔥 |
| Athlet | 600 | ⚡ |
| Pro | 1000 | 🏆 |
| Elite | 1500 | 👑 |

**Badges (16):** sechs Workout-Meilensteine (1, 5, 10, 25, 50, 100 Workouts), vier
Streak-Meilensteine (3, 7, 14, 30 Tage), zwei Plan-Badges (Plan erstellt, Plan vollständig
abgeschlossen) sowie vier Bonus-Badges (Frühaufsteher vor 8 Uhr, Weekend Warrior,
4 Wochen Beständigkeit, persönliche Bestleistung).

---

## 12. Designentscheidungen

**Rasa 3.6 (Open Source):** letzte stabile Open-Source-Version vor dem kommerziellen Rasa Pro;
läuft lokal ohne Cloud-Abhängigkeit und ist mit Python 3.10 kompatibel.

**Gemini Free Tier:** kostenlos und ohne Kreditkarte nutzbar (Ratelimit ausreichend für
Entwicklung und Testsessions); über `LLM_MODEL` austauschbar.

**SQLite:** keine Infrastruktur nötig, für einen Einzelnutzer-Prototyp ausreichend; Tabellen
werden beim Start automatisch angelegt.

**Kein Login:** Authentifizierung würde die Komplexität erhöhen, ohne wissenschaftlichen
Mehrwert für die Demonstration zu liefern.

**Zwei Python-Umgebungen:** Rasa 3.6 hat strenge, teils ältere Abhängigkeiten (u. a. TensorFlow,
SQLAlchemy 1.4), die mit dem modernen FastAPI-Stack (SQLAlchemy 2.x) kollidieren. Die strikte
Trennung in `.venv-rasa` und `.venv-backend` verhindert Konflikte.

**Asynchrone Plangenerierung:** Ein vollständiger Plan-Aufruf dauert 10–30 Sekunden; er läuft in
einem Hintergrund-Thread, während das Frontend den Status pollt und einen Ladeindikator zeigt.

**Hybrides Routing:** LLM-Aufrufe nur dort, wo Kreativität und Kontext gefragt sind — nicht für
strukturierte, deterministische Abläufe. Das reduziert Latenz, Kosten und Fehleranfälligkeit.
