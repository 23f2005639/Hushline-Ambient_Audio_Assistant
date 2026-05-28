import copy
import json
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).resolve().parent.parent / "ambient_settings.json"


DEFAULT_SETTINGS: dict[str, Any] = {
    "speech_trigger": 5,
    "silence_trigger": 40,
    "resume_delay": 0.5,
    "vad_aggressiveness": 2,
    "show_island": True,
    "state_notifications_enabled": True,
    "notify_when_circle_off": False,
    "click_to_open_controller": True,
    "notification_style": "icon_only_pulse",
    "collapse_ms": 4000,
    "notify_collapse_ms": 2800,
    "island_position": "top-center",
    "state_colors": {
        "idle": "#95A5A6",
        "listening": "#66E2FF",
        "speaking": "#FF8D7D",
        "paused": "#FF8D7D",
        "calibrating": "#FFD166",
        "error": "#FF5C7A",
    },
    "controller_theme": {
        "accent": "#66E2FF",
        "background": "#161A25",
        "surface": "#1D2332",
        "text": "#F4F5FF",
        "muted": "#A7B1C3",
    },
}


def _merge_defaults(value: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    for key, item in value.items():
        if isinstance(item, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_defaults(item, merged[key])
        else:
            merged[key] = item
    return merged


class SettingsStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.settings = self.load()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return copy.deepcopy(DEFAULT_SETTINGS)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return copy.deepcopy(DEFAULT_SETTINGS)
        if not isinstance(raw, dict):
            return copy.deepcopy(DEFAULT_SETTINGS)
        return _merge_defaults(raw, DEFAULT_SETTINGS)

    def save(self, settings: dict[str, Any]) -> dict[str, Any]:
        self.settings = _merge_defaults(settings, DEFAULT_SETTINGS)
        self.path.write_text(
            json.dumps(self.settings, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return self.settings

    def reset_appearance(self) -> dict[str, Any]:
        for key in (
            "show_island",
            "state_notifications_enabled",
            "notify_when_circle_off",
            "click_to_open_controller",
            "notification_style",
            "collapse_ms",
            "notify_collapse_ms",
            "island_position",
            "state_colors",
            "controller_theme",
        ):
            self.settings[key] = copy.deepcopy(DEFAULT_SETTINGS[key])
        return self.save(self.settings)

    def update(self, updates: dict[str, Any]) -> dict[str, Any]:
        merged = _merge_defaults(updates, self.settings)
        return self.save(merged)
