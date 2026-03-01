import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "disk_health_monitor"
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "refresh_interval_sec": 60,
    "alert_temp_c": 60,
    "auto_refresh": True,
    "history": {},
}


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)

    if merged.get("theme") not in {"dark", "light"}:
        merged["theme"] = DEFAULT_SETTINGS["theme"]

    try:
        merged["refresh_interval_sec"] = int(merged.get("refresh_interval_sec", 60))
    except Exception:  # noqa: BLE001
        merged["refresh_interval_sec"] = 60
    merged["refresh_interval_sec"] = max(30, min(1800, merged["refresh_interval_sec"]))

    try:
        merged["alert_temp_c"] = int(merged.get("alert_temp_c", 60))
    except Exception:  # noqa: BLE001
        merged["alert_temp_c"] = 60
    merged["alert_temp_c"] = max(30, min(100, merged["alert_temp_c"]))

    merged["auto_refresh"] = bool(merged.get("auto_refresh", True))

    if not isinstance(merged.get("history"), dict):
        merged["history"] = {}

    return merged


def save_settings(data: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
