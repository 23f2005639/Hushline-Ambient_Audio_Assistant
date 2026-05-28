import math
import threading
from typing import Any, Callable

from PySide6.QtCore import (
    QPoint,
    QObject,
    QEasingCurve,
    Property,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .overlay import FloatingIsland
from .settings_window import SettingsWindow


class OverlaySignals(QObject):
    apply_settings = Signal(dict)
    set_state = Signal(str, dict)
    set_media = Signal(dict)
    open_settings = Signal()
    stop = Signal()


class QtOverlayRuntime:
    def __init__(
        self,
        settings: dict[str, Any],
        media_controller,
        on_open_settings: Callable[[], None],
        on_save_settings: Callable[[dict[str, Any]], None],
        on_reset_appearance: Callable[[], dict[str, Any]],
        on_preview_settings: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.app = QApplication.instance() or QApplication([])
        self.media_controller = media_controller
        self.settings = settings
        self.settings_window = None
        self.overlay = FloatingIsland(
            settings=settings,
            on_media_cmd=self.handle_media_cmd,
            on_open_settings=self.open_settings,
        )
        self.on_open_settings = on_open_settings
        self.on_save_settings = on_save_settings
        self.on_reset_appearance = on_reset_appearance
        self.on_preview_settings = on_preview_settings
        self._on_reset_wrapper = self._reset_appearance_on_qt_thread
        self.signals = OverlaySignals()
        self.signals.apply_settings.connect(self.overlay.apply_settings)
        self.signals.set_state.connect(self.overlay.set_state)
        self.signals.set_media.connect(self.overlay.set_media)
        self.signals.open_settings.connect(self._open_settings_on_qt_thread)
        self.signals.stop.connect(self._stop_on_qt_thread)

    def run(self):
        self.overlay.show()
        self.app.exec()

    def stop(self):
        self.signals.stop.emit()

    def _stop_on_qt_thread(self):
        self.overlay.close()
        self.app.quit()

    def apply_settings(self, settings: dict[str, Any]):
        self.settings = settings
        self.signals.apply_settings.emit(settings)
        if self.settings_window:
            self.settings_window.update_settings(settings)

    def set_state(self, state: str, payload: dict[str, Any] | None = None):
        self.signals.set_state.emit(state, payload or {})

    def set_media(self, media: dict[str, Any]):
        self.signals.set_media.emit(media)

    def handle_media_cmd(self, cmd: str):
        def run():
            import asyncio

            if cmd == "toggle":
                asyncio.run(self.media_controller.toggle_media())
            elif cmd == "prev":
                asyncio.run(self.media_controller.previous_media())
            elif cmd == "next":
                asyncio.run(self.media_controller.next_media())

        threading.Thread(target=run, daemon=True).start()

    def open_settings(self):
        self.signals.open_settings.emit()

    def _reset_appearance_on_qt_thread(self) -> dict[str, Any]:
        settings = self.on_reset_appearance()
        self.settings = settings
        self.settings_window = None
        self.signals.apply_settings.emit(settings)
        return settings

    def _open_settings_on_qt_thread(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                self.settings,
                on_save=self.on_save_settings,
                on_reset=self._on_reset_wrapper,
                on_change=self._on_settings_preview,
            )
        else:
            self.settings_window.update_settings(self.settings)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _on_settings_preview(self, settings: dict[str, Any]) -> None:
        # Emit preview apply to update overlay appearance without persisting
        try:
            self.signals.apply_settings.emit(settings)
        except Exception:
            pass
        # also notify runtime (AmbientApp) about preview so non-UI engines update
        if getattr(self, "on_preview_settings", None):
            try:
                self.on_preview_settings(settings)
            except Exception:
                pass
