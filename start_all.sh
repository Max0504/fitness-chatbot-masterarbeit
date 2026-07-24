#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

# .env laden
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Fehler: .env-Datei nicht gefunden. Bitte .env.example kopieren und GEMINI_API_KEY eintragen."
    exit 1
fi

echo "=== Fitness Chatbot Startup ==="
echo ""

# Node-Binary ermitteln: bevorzuge brew-installierten Node falls system-Node zu alt
NODE_BIN="$(command -v node)"
NODE_MAJOR=$("$NODE_BIN" -e "process.stdout.write(String(process.versions.node.split('.')[0]))" 2>/dev/null || echo "0")
if [ "$NODE_MAJOR" -lt 18 ]; then
    for candidate in /usr/local/opt/node@25/bin/node /opt/homebrew/opt/node@25/bin/node /usr/local/bin/node /opt/homebrew/bin/node /usr/local/opt/node/bin/node; do
        if [ -x "$candidate" ]; then
            CAND_MAJOR=$("$candidate" -e "process.stdout.write(String(process.versions.node.split('.')[0]))" 2>/dev/null || echo "0")
            if [ "$CAND_MAJOR" -ge 18 ]; then
                NODE_BIN="$candidate"
                break
            fi
        fi
    done
    if [ "$("$NODE_BIN" -e "process.stdout.write(String(process.versions.node.split('.')[0]))" 2>/dev/null || echo "0")" -lt 18 ]; then
        CELLAR_NODE=$(ls /usr/local/Cellar/node/*/bin/node 2>/dev/null | tail -1)
        [ -x "$CELLAR_NODE" ] && NODE_BIN="$CELLAR_NODE"
    fi
fi
echo "Node: $("$NODE_BIN" --version) ($NODE_BIN)"

# Rasa-Modell: trainieren wenn kein Modell vorhanden oder --retrain übergeben
RASA_MODELS_DIR="rasa/models"
if [ "$1" == "--retrain" ] || [ -z "$(ls -A "$RASA_MODELS_DIR" 2>/dev/null)" ]; then
    echo "Trainiere Rasa-Modell (dauert 1-3 Minuten beim ersten Mal)..."
    "$ROOT/.venv-rasa/bin/rasa" train \
        --domain rasa/domain.yml \
        --data rasa/data \
        --config rasa/config.yml \
        --out "$RASA_MODELS_DIR" \
        --skip-validation
    echo "Rasa-Modell trainiert."
else
    LATEST=$(ls -t "$RASA_MODELS_DIR"/*.tar.gz 2>/dev/null | head -1)
    echo "Bestehendes Modell gefunden: $(basename "$LATEST")"
    echo "(--retrain für Neutraining)"
fi
echo ""

echo "Starte Backend (FastAPI) auf :8000..."
"$ROOT/.venv-backend/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000 &
PID_BACKEND=$!

echo "Starte Rasa Action Server auf :5055..."
(cd rasa && "$ROOT/.venv-rasa/bin/rasa" run actions --port 5055) &
PID_ACTIONS=$!

echo "Warte auf Action Server..."
until curl -s http://localhost:5055/health > /dev/null 2>&1; do sleep 1; done
echo "Action Server bereit."

echo "Starte Rasa Server auf :5005 (neuestes Modell aus $RASA_MODELS_DIR)..."
"$ROOT/.venv-rasa/bin/rasa" run \
    --model "$ROOT/$RASA_MODELS_DIR" \
    --enable-api --cors "*" --port 5005 \
    --endpoints rasa/endpoints.yml &
PID_RASA=$!

echo "Starte Frontend (Vite) auf :5173..."
(cd frontend && "$NODE_BIN" node_modules/.bin/vite) &
PID_FRONTEND=$!

trap "echo ''; echo 'Stoppe alle Services...'; kill $PID_BACKEND $PID_ACTIONS $PID_RASA $PID_FRONTEND 2>/dev/null; exit 0" EXIT INT TERM

echo "Warte auf Backend..."
until curl -s http://localhost:8000/ > /dev/null 2>&1; do sleep 1; done
echo "Backend bereit."

echo "Warte auf Rasa Server (Modell wird geladen)..."
until curl -s http://localhost:5005/version > /dev/null 2>&1; do sleep 1; done
echo "Rasa Server bereit."

echo "Warte auf Frontend..."
until curl -s http://localhost:5173 > /dev/null 2>&1; do sleep 1; done

echo ""
echo "================================================"
echo "  Alles laeuft! Du kannst jetzt starten."
echo ""
echo "  http://localhost:5173"
echo ""
echo "  Stoppen: Strg+C"
echo "================================================"
echo ""
wait
