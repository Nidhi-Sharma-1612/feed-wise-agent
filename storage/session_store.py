import json
from pathlib import Path
from datetime import datetime

_STORE_PATH = Path(__file__).parent.parent / "output" / "session_state.json"


def _load() -> dict:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    _STORE_PATH.parent.mkdir(exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def save_run_result(result: dict) -> None:
    data = _load()
    runs = data.get("runs", [])
    runs.append({**result, "saved_at": datetime.utcnow().isoformat()})
    data["runs"] = runs[-10:]  # keep last 10 runs
    data["last_run"] = runs[-1]
    _save(data)


def get_last_run() -> dict:
    return _load().get("last_run", {})


def get_all_runs() -> list:
    return _load().get("runs", [])


def clear_session() -> None:
    if _STORE_PATH.exists():
        _STORE_PATH.unlink()
