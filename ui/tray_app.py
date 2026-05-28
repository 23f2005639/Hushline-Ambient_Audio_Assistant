import threading
from typing import Callable

import pystray
from PIL import Image, ImageDraw


class TrayApp:
    """Native system tray host for Ambient."""

    STATE_SUBTITLE = {
        "idle": "Idle",
        "listening": "Listening - will pause on speech",
        "speaking": "Speech detected - pausing music",
        "paused": "Music paused - waiting for silence",
        "calibrating": "Calibrating ambient noise",
        "error": "Needs attention",
    }

    def __init__(
        self,
        on_open_settings: Callable[[], None],
        on_toggle_island: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_recalibrate: Callable[[], None],
        on_quit: Callable[[], None],
        get_color: Callable[[str], str],
    ):
        self.on_open_settings = on_open_settings
        self.on_toggle_island = on_toggle_island
        self.on_toggle_pause = on_toggle_pause
        self.on_recalibrate = on_recalibrate
        self.on_quit_cb = on_quit
        self.get_color = get_color

        self.current_state = "idle"
        self.paused = False
        self.icon = None
        self._lock = threading.RLock()

    def _make_icon_image(self, color: str) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=color)
        draw.ellipse([18, 18, 46, 46], fill=(0, 0, 0, 0))
        return img

    def set_state(self, state: str) -> None:
        with self._lock:
            self.current_state = state
            if not self.icon:
                return
            display_state = "paused" if self.paused else state
            color = self.get_color(display_state)
            self.icon.icon = self._make_icon_image(color)
            self.icon.title = f"Ambient - {display_state.capitalize()}"
            self.icon.menu = self._make_menu()

    def _make_menu(self) -> pystray.Menu:
        state = "paused" if self.paused else self.current_state
        subtitle = self.STATE_SUBTITLE.get(state, state.capitalize())
        pause_label = "Resume" if self.paused else "Pause"
        return pystray.Menu(
            pystray.MenuItem(f"* {state.capitalize()}", None, enabled=False),
            pystray.MenuItem(subtitle, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Settings", self._open_settings),
            pystray.MenuItem("Show / Hide Island", self._toggle_island),
            pystray.MenuItem(pause_label, self._toggle_pause),
            pystray.MenuItem("Recalibrate", self._on_recalibrate),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _open_settings(self, icon=None, item=None) -> None:
        self.on_open_settings()

    def _toggle_island(self, icon=None, item=None) -> None:
        self.on_toggle_island()

    def _toggle_pause(self, icon=None, item=None) -> None:
        self.on_toggle_pause()

    def _on_recalibrate(self, icon=None, item=None) -> None:
        self.on_recalibrate()

    def _on_quit(self, icon=None, item=None) -> None:
        self.stop()
        self.on_quit_cb()

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self.paused = paused
            if not self.icon:
                return
            self.icon.menu = self._make_menu()
            self.set_state(self.current_state)

    def stop(self) -> None:
        if self.icon:
            self.icon.stop()

    def run(self) -> None:
        self.icon = pystray.Icon(
            name="ambient",
            icon=self._make_icon_image(self.get_color("idle")),
            title="Ambient - Idle",
            menu=self._make_menu(),
        )
        self.icon.run()
