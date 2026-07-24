# FitCoach — Hybrider Fitness-Chatbot

Prototyp eines konversationalen Fitness-Coaches, entwickelt im Rahmen der Masterarbeit
*„Konzeption und Entwicklung eines Generativen KI-basierten Virtual Coaching Chatbots zur Unterstützung im Fitnesstraining"* (Universität Regensburg,
Lehrstuhl für Wirtschaftsinformatik).

Der Bot führt den Nutzer durch ein Onboarding, erstellt einen personalisierten Trainingsplan, trackt Workouts und Aktivitäten und visualisiert den Fortschritt über ein Dashboard. Technisch kombiniert er **Rasa** (deterministische Gesprächsführung) mit **Google Gemini** (freie, kontextsensitive Antworten), einem **FastAPI**-Backend und einem **React**-Frontend.

> Diese README beschreibt **Installation und Betrieb**. Die fachliche und technische
Spezifikation (Architektur, Funktionsumfang, Datenmodell, Designentscheidungen) steht in **`SPEC.md`**.

---

## Architektur (Kurzüberblick)

```
┌─────────────┐     Webhook      ┌──────────────┐     HTTP      ┌──────────────┐
│   React     │ ───────────────► │  Rasa Server │ ────────────► │ Action Server│
│  Frontend   │                  │   :5005      │               │    :5055     │
│   :5173     │ ◄─────────────── │ NLU + Dialog │               │ Logik + LLM  │
└──────┬──────┘     Antworten    └──────────────┘               └──────┬───────┘
       │                                                                │
       │ REST-API                                        SQLite (geteilt)│
       ▼                                                                ▼
┌─────────────┐ ◄──────────────────────── data/fitness.db ──────────────┘
│  FastAPI    │
│   :8000     │
└─────────────┘
```

**Zwei getrennte Python-Umgebungen** (bewusst getrennt wegen inkompatibler Abhängigkeiten):
- `.venv-backend` — FastAPI, SQLAlchemy 2.x
- `.venv-rasa` — Rasa 3.6, SQLAlchemy 1.4

---

## Voraussetzungen

| Software | Version | Hinweis |
|---|---|---|
| **Python** | **3.10** (strikt) | Rasa 3.6 läuft **nicht** unter 3.11/3.12 |
| **Node.js** | ≥ 18 | für das React-Frontend |
| **Gemini API Key** | — | kostenlos, ohne Kreditkarte: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

Getestet unter macOS mit Python 3.10.20 und Node 18+.

---

## Erstinstallation

Alle Befehle werden im **Projekt-Root** (`fitness-chatbot/`) ausgeführt.

### 1. Umgebungsvariablen anlegen

```bash
cp .env.example .env
```

Anschließend `.env` öffnen und den Gemini API Key eintragen:

```
GEMINI_API_KEY=DEIN_KEY_HIER
```

### 2. Python-Umgebungen einrichten

```bash
# Backend-Umgebung (FastAPI)
python3.10 -m venv .venv-backend
.venv-backend/bin/pip install --upgrade pip
.venv-backend/bin/pip install -r backend/requirements.txt

# Rasa-Umgebung (dauert 3–5 Minuten)
python3.10 -m venv .venv-rasa
.venv-rasa/bin/pip install --upgrade pip
.venv-rasa/bin/pip install -r rasa/requirements.txt
```

### 3. Frontend-Abhängigkeiten installieren

```bash
cd frontend
npm install
cd ..
```

---

## Starten & Stoppen

Der einfachste Weg — ein Skript startet alle vier Dienste:

```bash
./start_all.sh
```

Beim **ersten Start** wird automatisch ein Rasa-Modell trainiert (~2–4 Minuten). Danach im
Browser öffnen:

**→ http://localhost:5173**

```bash
./start_all.sh --retrain   # Starten und Rasa-Modell neu trainieren
                           #  (nach Änderungen an NLU / Stories / Rules)
```

**Stoppen:** `Strg + C` im Terminal (beendet alle Dienste).

Das Skript startet parallel: FastAPI-Backend (8000) · Rasa Action Server (5055) ·
Rasa Server (5005) · Frontend (5173). Ist bereits ein Modell vorhanden, wird das neueste
geladen, statt neu zu trainieren.

> Falls `Permission denied`: einmalig `chmod +x start_all.sh` ausführen.

---

## Dienste einzeln starten (Windows / Linux / Debugging)

`start_all.sh` ist ein Bash-Skript für macOS/Linux. Unter Windows oder zum gezielten Debuggen
lassen sich die Dienste einzeln in je einem eigenen Terminal starten:

```bash
# Backend (FastAPI) — Port 8000
source .venv-backend/bin/activate
uvicorn backend.main:app --reload --port 8000

# Rasa Action Server — Port 5055
cd rasa && source ../.venv-rasa/bin/activate
rasa run actions --port 5055

# Rasa Server — Port 5005
source .venv-rasa/bin/activate
rasa run --model rasa/models --enable-api --cors "*" --port 5005 --endpoints rasa/endpoints.yml

# Frontend (Vite) — Port 5173
cd frontend && npm run dev
```

Unter **Windows** statt `.venv-backend/bin/...` jeweils `.venv-backend\Scripts\...` verwenden.

---

## Häufige Befehle

### Rasa-Modell neu trainieren

```bash
source .venv-rasa/bin/activate
rasa train --domain rasa/domain.yml --data rasa/data --config rasa/config.yml \
  --out rasa/models --skip-validation
```

Trainierte Modelle liegen als `.tar.gz` in `rasa/models/`. Nur das neueste behalten:

```bash
ls -t rasa/models/*.tar.gz | tail -n +2 | xargs rm -f
```

### Datenbank zurücksetzen (Nutzer-Reset)

Löscht alle Nutzerdaten (Profil, Plan, Workouts, Punkte, Badges); die Tabellenstruktur bleibt.
Beim nächsten Backend-Start wird automatisch ein leerer Demo-Nutzer angelegt.

```bash
sqlite3 data/fitness.db "
DELETE FROM workout_logs; DELETE FROM cardio_logs; DELETE FROM strength_logs;
DELETE FROM points_history; DELETE FROM badges; DELETE FROM weight_logs;
DELETE FROM performance_logs; DELETE FROM plan_workouts; DELETE FROM training_plans;
DELETE FROM profiles; DELETE FROM users;"
```

Gesprächsverlauf von Rasa ebenfalls zurücksetzen:

```bash
rm -f data/rasa_tracker.db
echo '{"status":"idle","error":"","ts":0}' > data/plan_status.json
```

### Logs & laufende Dienste

```bash
tail -f data/logs/events.jsonl              # LLM-Calls, Plangenerierung, Fehler
lsof -i :8000 -i :5005 -i :5055 -i :5173    # Prüfen, was läuft
lsof -ti :8000 :5005 :5055 :5173 | xargs kill -9   # Alle Ports freigeben
```

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| `python3.10: command not found` | Pfad prüfen (`which python3.10`); auf Apple-Silicon ggf. `/opt/homebrew/bin/python3.10` verwenden. Installation: `brew install python@3.10` |
| `Permission denied` bei `start_all.sh` | `chmod +x start_all.sh` |
| `Port already in use` | `lsof -ti :8000 :5005 :5055 :5173 \| xargs kill -9`, dann neu starten |
| `.env-Datei nicht gefunden` | `cp .env.example .env` und `GEMINI_API_KEY` eintragen |
| Rasa-Training schlägt fehl | `./start_all.sh --retrain` erneut ausführen; Logs unter `data/logs/` prüfen |
| Frontend leer / keine Antworten | Prüfen, ob alle vier Dienste laufen (`lsof -i :8000 -i :5005 -i :5055 -i :5173`) |

---

## Projektstruktur

```
fitness-chatbot/
├── backend/                  # FastAPI-Backend (venv: .venv-backend)
│   ├── main.py               # App-Einstieg, Router-Registrierung, DB-Init
│   ├── models.py             # SQLAlchemy-ORM (11 Tabellen, geteilt mit Rasa)
│   ├── database.py           # DB-Verbindung / Session
│   ├── schemas.py            # Pydantic-Schemas
│   ├── gamification.py       # Level-, Punkte- und Badge-Definitionen
│   ├── nutrition_generator.py# Ernährungstipps (LLM)
│   ├── seed.py               # Demo-Daten
│   └── routers/              # 8 API-Router (profile, plan, workouts, dashboard,
│                             #   activity, progress, nutrition, exercises)
├── rasa/                     # Rasa-Projekt (venv: .venv-rasa)
│   ├── domain.yml            # Intents, Slots, Responses, Actions
│   ├── config.yml            # NLU-Pipeline & Policies
│   ├── endpoints.yml         # Action-Server-Anbindung
│   ├── data/                 # nlu.yml, stories.yml, rules.yml
│   ├── actions/              # actions.py (28 Custom Actions), llm_client.py,
│   │                         #   plan_generator.py, plan_status.py, db.py
│   └── models/               # trainierte Rasa-Modelle (.tar.gz)
├── frontend/                 # React + TypeScript + Vite
│   └── src/
│       ├── components/       # Chat, Dashboard, Plan, Progress, Profile,
│       │                     #   Nutrition, Tutorial, Layout, Sidebar, Toast
│       ├── api/              # zentrale Backend-/Rasa-Aufrufe
│       ├── hooks/  lib/  types/
├── data/
│   ├── fitness.db            # SQLite (Nutzer, Plan, Logs, Badges)
│   ├── exercises.json        # Übungskatalog
│   ├── plan_status.json      # Status der Hintergrund-Plangenerierung
│   └── logs/events.jsonl     # Logging aller LLM-Calls
├── start_all.sh              # Ein-Befehl-Start aller Dienste
├── .env                      # spezifizierte Umgebungsvariablen (API)
├── .env.example              # Vorlage für Umgebungsvariablen (API)
├── README.md                 # diese Datei
└── SPEC.md                   # Spezifikation (Architektur, Konzept, Datenmodell)
```

---

## Ports

| Dienst | Port |
|---|---|
| Frontend (Vite) | 5173 |
| FastAPI-Backend | 8000 |
| Rasa Server | 5005 |
| Rasa Action Server | 5055 |
