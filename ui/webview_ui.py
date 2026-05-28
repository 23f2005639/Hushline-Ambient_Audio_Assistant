import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import webview

from ui.settings_store import SettingsStore


class WebviewApi:
    def __init__(self, runtime: "WebviewUI"):
        self.runtime = runtime

    def island_ready(self):
        self.runtime.sync_island()
        return True

    def settings_ready(self):
        self.runtime.sync_settings()
        return True

    def media_cmd(self, cmd: str):
        self.runtime.handle_media_cmd(cmd)
        return True

    def open_settings(self):
        self.runtime.open_settings()
        return True

    def save_settings(self, settings: dict[str, Any]):
        saved = self.runtime.save_settings(settings)
        return saved

    def reset_appearance(self):
        return self.runtime.reset_appearance()

    def close_settings(self):
        self.runtime.close_settings()
        return True

    def set_island_mode(self, mode: str):
        self.runtime.set_island_mode(mode)
        return True


class WebviewUI:
    """Owns pywebview windows and the JS/Python bridge."""

    def __init__(
        self,
        settings_store: SettingsStore,
        media_controller,
        on_settings_changed: Callable[[dict[str, Any]], None],
        on_recalibrate: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self.settings_store = settings_store
        self.settings = settings_store.settings
        self.media_controller = media_controller
        self.on_settings_changed = on_settings_changed
        self.on_recalibrate = on_recalibrate
        self.on_quit = on_quit

        self.api = WebviewApi(self)
        self.island_window = None
        self.settings_window = None
        self.tray = None
        self.current_state = "idle"
        self.current_payload: dict[str, Any] = {}
        self._media_polling = False
        self._island_ready = False
        self._island_mode = "dot"

    @property
    def index_url(self) -> str:
        dist = Path(__file__).resolve().parent / "frontend" / "dist" / "index.html"
        if not dist.exists():
            raise RuntimeError(
                "Frontend build missing. Run npm.cmd install and npm.cmd run build in ui/frontend."
            )
        return dist.as_uri()

    def attach_tray(self, tray) -> None:
        self.tray = tray

    def start(self) -> None:
        self.island_window = webview.create_window(
            "Ambient Island",
            f"{self.index_url}#island",
            js_api=self.api,
            width=34,
            height=34,
            x=0,
            y=0,
            resizable=False,
            frameless=True,
            transparent=True,
            easy_drag=True,
            on_top=True,
            shadow=False,
            background_color="#000000",
            text_select=False,
        )
        webview.start(self._on_webview_started, debug=False)

    def _on_webview_started(self) -> None:
        self.apply_settings()
        self.set_state("listening")
        self._start_media_polling()

    def set_state(self, state: str, payload: dict[str, Any] | None = None) -> None:
        self.current_state = state
        self.current_payload = payload or {}
        if self.tray:
            self.tray.set_state(state)
        self._eval_island("window.AmbientUI?.setState", state, self.current_payload)

    def notify(self, title: str, body: str, state: str | None = None) -> None:
        payload = {"notification": {"title": title, "body": body}}
        self.set_state(state or self.current_state, payload)

    def sync_island(self) -> None:
        self._island_ready = True
        self.apply_settings()
        self.set_state(self.current_state, self.current_payload)
        self.push_media_info()

    def sync_settings(self) -> None:
        self._eval_settings("window.AmbientSettings?.applySettings", self.settings)

    def apply_settings(self) -> None:
        self._position_island()
        self._eval_island("window.AmbientUI?.applySettings", self.settings)
        self._eval_settings("window.AmbientSettings?.applySettings", self.settings)

    def save_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        self.settings = self.settings_store.save(settings)
        self.on_settings_changed(self.settings)
        self.apply_settings()
        if self.tray:
            self.tray.set_state(self.current_state)
        return self.settings

    def reset_appearance(self) -> dict[str, Any]:
        self.settings = self.settings_store.reset_appearance()
        self.on_settings_changed(self.settings)
        self.apply_settings()
        if self.tray:
            self.tray.set_state(self.current_state)
        return self.settings

    def toggle_island(self) -> None:
        next_settings = dict(self.settings)
        next_settings["show_island"] = not bool(self.settings.get("show_island", True))
        self.save_settings(next_settings)

    def set_island_mode(self, mode: str) -> None:
        sizes = {
            "hidden": (1, 1),
            "dot": (34, 34),
            "notify": (230, 58),
            "expanded": (320, 152),
        }
        width, height = sizes.get(mode, sizes["dot"])
        self._island_mode = mode
        if not self.island_window:
            return
        try:
            self.island_window.resize(width, height)
            self._position_island(width, height)
        except Exception as exc:
            print(f"Island resize error: {exc}")

    def open_settings(self) -> None:
        if self.settings_window:
            try:
                self.settings_window.show()
                return
            except Exception:
                self.settings_window = None
        self.settings_window = webview.create_window(
            "Ambient Settings",
            f"{self.index_url}#settings",
            js_api=self.api,
            width=760,
            height=720,
            resizable=True,
            min_size=(640, 580),
            on_top=False,
            text_select=False,
        )

    def close_settings(self) -> None:
        if not self.settings_window:
            return
        try:
            self.settings_window.hide()
        except Exception:
            pass

    def handle_media_cmd(self, cmd: str) -> None:
        def run():
            try:
                if cmd == "toggle":
                    asyncio.run(self.media_controller.toggle_media())
                elif cmd == "prev":
                    asyncio.run(self.media_controller.previous_media())
                elif cmd == "next":
                    asyncio.run(self.media_controller.next_media())
            finally:
                self.push_media_info()

        threading.Thread(target=run, daemon=True).start()

    def push_media_info(self) -> None:
        if not self._island_ready:
            return
        try:
            info = asyncio.run(self.media_controller.get_media_info())
        except Exception:
            info = {
                "title": "Nothing playing",
                "artist": "-",
                "playing": False,
                "progress": 0,
            }
        self._eval_island("window.AmbientUI?.setMedia", info)

    def quit(self) -> None:
        self.on_quit()
        try:
            for window in list(webview.windows):
                window.destroy()
        except Exception:
            pass

    def _start_media_polling(self) -> None:
        if self._media_polling:
            return
        self._media_polling = True

        def loop():
            while self._media_polling:
                self.push_media_info()
                time.sleep(2)

        threading.Thread(target=loop, daemon=True).start()

    def _position_island(self, width: int | None = None, height: int | None = None) -> None:
        if not self.island_window:
            return
        position = self.settings.get("island_position", "top-center")
        try:
            screen = webview.screens[0]
            width = width or self.island_window.width
            height = height or self.island_window.height
            margin = 18
            x = int((screen.width - width) / 2)
            y = margin
            if position == "top-left":
                x = margin
            elif position == "top-right":
                x = screen.width - width - margin
            elif position == "bottom-right":
                x = screen.width - width - margin
                y = screen.height - height - 72
            elif position == "bottom-left":
                x = margin
                y = screen.height - height - 72
            elif position == "bottom-center":
                y = screen.height - height - 72
            self.island_window.move(x, y)
        except Exception:
            pass

    def _eval_island(self, function_name: str, *args) -> None:
        self._eval(self.island_window, function_name, *args)

    def _eval_settings(self, function_name: str, *args) -> None:
        self._eval(self.settings_window, function_name, *args)

    def _eval(self, window, function_name: str, *args) -> None:
        if not window:
            return
        encoded = ", ".join(json.dumps(arg) for arg in args)
        try:
            window.evaluate_js(f"{function_name}({encoded})")
        except Exception as exc:
            print(f"UI bridge error in {function_name}: {exc}")
