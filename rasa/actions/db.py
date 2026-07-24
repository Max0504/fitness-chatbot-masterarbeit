import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Modelle aus dem backend-Modul importieren — gemeinsame Quelle der Wahrheit
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
from models import Base, User, Profile, TrainingPlan, PlanWorkout, WorkoutLog, PointsHistory, WeightLog, CardioLog, StrengthLog  # noqa

# Absoluter Pfad berechnet aus __file__ — ignoriert relative DATABASE_URL aus .env,
# da der Action Server aus rasa/ gestartet wird und relative Pfade dort landen würden.
_ABS_DB = Path(__file__).parent.parent.parent / "data" / "fitness.db"
_env_db = os.environ.get("DATABASE_URL", "")
# Nur absolute SQLite-URLs akzeptieren (4 Slashes = absoluter Pfad auf Unix)
if _env_db.startswith("sqlite:////"):
    DATABASE_URL = _env_db
else:
    DATABASE_URL = f"sqlite:///{_ABS_DB}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    return SessionLocal()


# Tabellen anlegen falls noch nicht vorhanden (idempotent)
Base.metadata.create_all(bind=engine)

DEMO_USER_ID = 1
