import json
import threading
from pathlib import Path
from typing import Any, Callable

import webview


class SettingsApi:
    def __init__(
        self,
        get_settings: Callable[[], dict[str, Any]],
        save_settings: Callable[[dict[str, Any]], dict[str, Any]],
        reset_appearance: Callable[[], dict[str, Any]],
        on_quit: Callable[[], None],
    ):
        self.get_settings = get_settings
        self.save_settings_cb = save_settings
        self.reset_appearance_cb = reset_appearance
        self.on_quit = on_quit
        self.window = None

    def settings_ready(self):
        if self.window:
            self.window.evaluate_js(
                f"window.AmbientSettings?.applySettings({json.dumps(self.get_settings())})"
            )
        return True

    def save_settings(self, settings: dict[str, Any]):
        return self.save_settings_cb(settings)

    def reset_appearance(self):
        return self.reset_appearance_cb()

    def close_settings(self):
        if self.window:
            self.window.hide()
        return True

    def quit_app(self):
        self.on_quit()
        return True


class SettingsWebview:
    def __init__(
        self,
        get_settings: Callable[[], dict[str, Any]],
        save_settings: Callable[[dict[str, Any]], dict[str, Any]],
        reset_appearance: Callable[[], dict[str, Any]],
        on_quit: Callable[[], None],
    ):
        self.api = SettingsApi(get_settings, save_settings, reset_appearance, on_quit)
        self.started = False
        self._lock = threading.Lock()

    @property
    def index_url(self) -> str:
        dist = Path(__file__).resolve().parent / "frontend" / "dist" / "index.html"
        return f"{dist.as_uri()}#settings"

    def open(self):
        with self._lock:
            if self.started and self.api.window:
                self.api.window.show()
                return
            self.api.window = webview.create_window(
                "Ambient Settings",
                self.index_url,
                js_api=self.api,
                width=760,
                height=720,
                resizable=True,
                min_size=(640, 580),
                text_select=False,
            )
            self.started = True
        webview.start(debug=False)

    def close(self):
        with self._lock:
            window = self.api.window
        if not window:
            return
        try:
            window.destroy()
        except Exception:
            try:
                window.hide()
            except Exception:
                pass
