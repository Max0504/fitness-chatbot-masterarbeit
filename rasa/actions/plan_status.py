"""Plan-generation status via a JSON file in data/."""
import json
import time
from pathlib import Path

_STATUS_FILE = Path(__file__).parent.parent.parent / "data" / "plan_status.json"


def set_status(status: str, error: str = "") -> None:
    try:
        _STATUS_FILE.write_text(
            json.dumps({"status": status, "error": error, "ts": time.time()})
        )
    except Exception:
        pass


def get_status() -> dict:
    try:
        return json.loads(_STATUS_FILE.read_text())
    except Exception:
        return {"status": "idle", "error": "", "ts": 0}
