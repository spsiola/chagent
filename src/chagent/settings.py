import os
import json
from pydantic import BaseModel

SETTINGS_FILE = "data/settings.json"

class AppSettings(BaseModel):
    theme: str = "dark" # "light", "dark", "system"
    timezone: str = "UTC"
    safe_mode: bool = True
    allowed_roots: list[str] = ["./"]

def load_settings() -> AppSettings:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppSettings(**data)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return AppSettings()
    return AppSettings()

def save_settings(settings: AppSettings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
