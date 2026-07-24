import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "fitness.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{_DEFAULT_DB}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# WAL-Mode für bessere Parallelität bei SQLite (FastAPI + Rasa greifen gleichzeitig zu)
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

from .models import Base  # noqa — stellt sicher dass alle Modelle registriert sind
