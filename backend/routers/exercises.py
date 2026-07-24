import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

EXERCISES_PATH = Path(__file__).parent.parent.parent / "data" / "exercises.json"
_cache: list | None = None


def _load() -> list:
    global _cache
    if _cache is None:
        with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


@router.get("")
def get_exercises():
    return _load()
