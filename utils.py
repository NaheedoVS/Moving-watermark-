import json
import os
from typing import Dict, Any

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "user_settings.json")

DEFAULTS = {
    "text": "Watermark",
    "color": "white",
    "size": 36,
    "direction": "static",
    "crf": 20,
    "resolution": "original",
    "compress": True
}

def load_settings() -> Dict[str, Any]:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return data
        except Exception:
            return {}
    return {}

def save_settings(data: Dict[str, Any]):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Failed saving settings:", e)

def get_user_settings(user_id: int) -> Dict[str, Any]:
    data = load_settings()
    s = data.get(str(user_id), {}).copy()
    for k, v in DEFAULTS.items():
        s.setdefault(k, v)
    return s

def set_user_settings(user_id: int, settings: Dict[str, Any]):
    data = load_settings()
    data[str(user_id)] = settings
    save_settings(data)
