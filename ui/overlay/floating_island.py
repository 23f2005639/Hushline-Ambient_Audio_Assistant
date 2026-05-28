import math
from typing import Any, Callable

from PySide6.QtCore import QPoint, QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

from ..widgets import ControllerPanel, NotificationCard


class FloatingIsland(QWidget):
    """Native transparent overlay for the hollow circle and Hushline controller."""

    def __init__(
        self,
        settings: dict[str, Any],
        on_media_cmd: Callable[[str], None],
        on_open_settings: Callable[[], None],
    ):
        super().__init__()
        self.settings = settings
        self.on_media_cmd = on_media_cmd
        self.on_open_settings = on_open_settings
        self.state = "idle"
        self.payload: dict[str, Any] = {}
        self.media = {
            "title": "Nothing playing",
            "artist": "-",
            "playing": False,
            "progress": 0,
        }
        self.mode = "dot"
        self.drag_offset = None
        self.drag_start = QPoint()
        self.drag_window_start = QPoint()
        self.dragging = False
        self.user_interacting = False
        self._pulse_phase = 0.0
        self._position_overridden = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.panel = ControllerPanel(on_media_cmd=self.on_media_cmd, on_open_settings=self.on_open_settings)
        self.notify_card = NotificationCard(self.container)
        layout.addWidget(self.panel)
        layout.addWidget(self.notify_card)
        self.notify_card.hide()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(190)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self.collapse)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(90)
        self.pulse_timer.timeout.connect(self._tick_pulse)
        self.pulse_timer.start()

        self.apply_settings(settings)
        self.set_mode("dot")

    def apply_settings(self, settings: dict[str, Any]):
        prev_position = self.settings.get("island_position")
        self.settings = settings
        if settings.get("island_position") != prev_position:
            self._position_overridden = False
        self._apply_style()
        self._refresh_visibility()
        if self.isVisible() and self.mode != "hidden":
            self.set_mode(self.mode)

    def set_state(self, state: str, payload: dict[str, Any] | None = None):
        self.state = state
        self.payload = payload or {}
        self._apply_style()
        self._refresh_visibility()

    def set_media(self, media: dict[str, Any]):
        self.media = media
        self.panel.set_media(media)

    def collapse(self):
        if self.user_interacting:
            return
        if self.mode in ("notify", "expanded"):
            self.payload = {}
        self._refresh_visibility(force_mode="dot")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.user_interacting = True
            self.collapse_timer.stop()
            self.drag_start = event.globalPosition().toPoint()
            self.drag_window_start = self.frameGeometry().topLeft()
            self.dragging = False

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.drag_start
            if not self.dragging and delta.manhattanLength() > 6:
                self.dragging = True
            if self.dragging:
                self.move(self.drag_window_start + delta)
                self._position_overridden = True

    def mouseReleaseEvent(self, event):
        del event
        was_dragging = self.dragging
        self.dragging = False
        if not was_dragging:
            self._handle_click_action()
        else:
            self._snap_to_nearest_anchor()
        if self.mode in ("notify", "expanded"):
            timeout = self.settings.get("notify_collapse_ms", 2800) if self.mode == "notify" else self.settings.get("collapse_ms", 4000)
            self.collapse_timer.start(int(timeout))

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.mode != "dot":
            return
        color = QColor(self._state_color())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._should_pulse_dot():
            pulse_alpha = int(70 + 35 * ((math.sin(self._pulse_phase) + 1.0) * 0.5))
            pulse = QColor(color)
            pulse.setAlpha(max(25, min(180, pulse_alpha)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(pulse)
            painter.drawEllipse(4, 4, self.width() - 8, self.height() - 8)
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(8, 8, self.width() - 16, self.height() - 16)

    def set_mode(self, mode: str):
        old_mode = self.mode
        self.mode = mode
        notify_style = self.settings.get("notification_style", "tiny_chip")
        notify_w, notify_h = self._notify_size_for_style(notify_style)
        sizes = {
            "hidden": (1, 1),
            "dot": (34, 34),
            "notify": (notify_w, notify_h),
            "expanded": (334, 172),
        }
        width, height = sizes[mode]
        panel_visible = mode == "expanded"
        notify_visible = mode == "notify"
        self.panel.setVisible(panel_visible)
        self.notify_card.setVisible(notify_visible)
        self.container.setVisible(panel_visible or notify_visible)
        if notify_visible and not panel_visible:
            self.container.setStyleSheet("background: transparent; border: none;")
        elif panel_visible:
            theme = self.settings.get("controller_theme", {})
            bg = theme.get("background", "#151526")
            state = self._state_color()
            self.container.setStyleSheet(
                f"""
                #container {{
                    background: rgba({QColor(bg).red()}, {QColor(bg).green()}, {QColor(bg).blue()}, 176);
                    border: 1px solid rgba({QColor(state).red()}, {QColor(state).green()}, {QColor(state).blue()}, 170);
                    border-radius: 13px;
                }}
                """
            )
        if notify_visible:
            snapshot = self._snapshot()
            accent = self._state_color()
            self.notify_card.set_style(notify_style)
            self.notify_card.set_content(snapshot["title"], snapshot["note"], accent)
            theme = self.settings.get("controller_theme", {})
            self.notify_card.apply_theme(theme, accent)
        if mode in ("notify", "expanded"):
            timeout = self.settings.get("notify_collapse_ms", 2800) if mode == "notify" else self.settings.get("collapse_ms", 4000)
            self.collapse_timer.start(int(timeout))
        else:
            self.collapse_timer.stop()

        if self._position_overridden and mode != "hidden":
            target = QRect(self.x(), self.y(), width, height)
        else:
            target = self._target_rect_for_mode(mode, old_mode, width, height)
        self.anim.stop()
        self.anim.setDuration(140 if mode == "notify" else 190)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target)
        self.anim.start()
        self.resize(width, height)
        self.container.setGeometry(0, 0, width, height)
        if not self._position_overridden:
            self._reposition_for_mode(mode, width, height)
        self._update_hit_mask(mode)
        self._update_cursor(mode)
        self.update()

    def _refresh_visibility(self):
        self._refresh_visibility(force_mode=None)

    def _refresh_visibility(self, force_mode: str | None = None):
        show_island = bool(self.settings.get("show_island", True))
        notifications_enabled = bool(self.settings.get("state_notifications_enabled", True))
        notify_when_circle_off = bool(self.settings.get("notify_when_circle_off", False))
        has_notification_payload = bool(self.payload.get("notification"))

        if show_island:
            can_notify = notifications_enabled
        else:
            can_notify = notifications_enabled and notify_when_circle_off

        has_notification = has_notification_payload and can_notify
        if not show_island and not notify_when_circle_off:
            visible = self.mode == "expanded"
        else:
            visible = show_island or has_notification or self.mode == "expanded"

        if not visible:
            self.hide()
            self.set_mode("hidden")
            return
        self.show()
        if force_mode == "dot":
            if show_island:
                self.set_mode("dot")
            elif has_notification:
                self.set_mode("notify")
            else:
                self.set_mode("hidden")
            return
        if self.mode == "expanded":
            return
        if has_notification:
            if self.settings.get("notification_style", "tiny_chip") == "icon_only_pulse":
                self.set_mode("dot")
            else:
                self.set_mode("notify")
        elif show_island:
            self.set_mode("dot")
        else:
            self.set_mode("hidden")

    def _apply_style(self):
        theme = self.settings.get("controller_theme", {})
        bg = theme.get("background", "#151526")
        state = self._state_color()
        self.setStyleSheet(
            f"""
            #container {{
                background: rgba({QColor(bg).red()}, {QColor(bg).green()}, {QColor(bg).blue()}, 176);
                border: 1px solid rgba({QColor(state).red()}, {QColor(state).green()}, {QColor(state).blue()}, 170);
                border-radius: 13px;
            }}
            """
        )
        self.panel.apply_style(theme, state)
        self.panel.set_state_snapshot(self._snapshot())
        notify_style = self.settings.get("notification_style", "tiny_chip")
        snapshot = self._snapshot()
        self.notify_card.set_style(notify_style)
        self.notify_card.set_content(snapshot["title"], snapshot["note"], state)
        self.notify_card.apply_theme(theme, state)

    def _state_color(self) -> str:
        mapped = self._map_state()
        palette = {
            "playback": "#66E2FF",
            "speaking": "#FF7F73",
            "paused": "#FF7F73",
            "away": "#9CE870",
            "calibrating-silence": "#FFD166",
            "calibrating-speech": "#66E2FF",
            "error": "#FF5C7A",
            "idle": "#95A5A6",
        }
        override = self.settings.get("state_colors", {})
        return override.get(self.state, palette.get(mapped, palette["idle"]))

    def _map_state(self) -> str:
        if self.state == "listening":
            return "playback"
        if self.state == "speaking":
            return "speaking"
        if self.state == "paused":
            return "paused"
        if self.state == "absent":
            return "away"
        if self.state == "error":
            return "error"
        if self.state == "calibrating":
            note = (self.payload or {}).get("notification", {}).get("title", "").lower()
            if "speak" in note:
                return "calibrating-speech"
            return "calibrating-silence"
        return "idle"

    def _snapshot(self) -> dict[str, Any]:
        mapped = self._map_state()
        note = (self.payload or {}).get("notification", {})
        title = note.get("title") or {
            "playback": "Playback running",
            "speaking": "Voice detected",
            "paused": "Media paused",
            "away": "Presence changed",
            "error": "Runtime issue",
            "calibrating-silence": "Calibration: stay silent",
            "calibrating-speech": "Calibration: speak now",
            "idle": "Ambient ready",
        }.get(mapped, "Ambient ready")
        subtitle = note.get("body") or {
            "playback": "Playback riding your focus",
            "speaking": "Conversation opened nearby",
            "paused": "Resume after quiet",
            "away": "Desk audio stays put",
            "error": "Check microphone or media session",
            "calibrating-silence": "Measuring room noise",
            "calibrating-speech": "Speak normally for input floor",
            "idle": "Listening for context",
        }.get(mapped, "Listening for context")
        presence = "Away" if mapped == "away" else "At desk"
        presence_variant = "away" if mapped == "away" else "normal"
        voice = {
            "speaking": "Speaking",
            "paused": "Listening",
            "playback": "Quiet",
            "calibrating-silence": "Calib: Silent",
            "calibrating-speech": "Calib: Speak",
            "away": "Idle",
            "error": "Error",
            "idle": "Idle",
        }.get(mapped, "Idle")
        voice_variant = {
            "calibrating-silence": "calibrating-silence",
            "calibrating-speech": "calibrating-speech",
            "error": "error",
        }.get(mapped, "normal")
        voice_attention = mapped in ("calibrating-silence", "calibrating-speech", "error")
        if mapped.startswith("calibrating-"):
            presence = "Calibrating"
            presence_variant = "normal"
        track = self.media.get("title") or "Media idle"
        if mapped.startswith("calibrating-"):
            mode = "playback"
        else:
            mode = mapped
        return {
            "mode": mode,
            "title": title,
            "note": subtitle,
            "presence": presence,
            "presence_variant": presence_variant,
            "presence_attention": mapped == "away",
            "voice": voice,
            "voice_variant": voice_variant,
            "voice_attention": voice_attention,
            "track": track,
        }

    def _reposition(self, width: int | None = None, height: int | None = None):
        self._reposition_for_mode(self.mode, width, height)

    def _reposition_for_mode(self, mode: str, width: int | None = None, height: int | None = None):
        if self._position_overridden and mode != "hidden":
            return
        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        width = width or self.width()
        height = height or self.height()
        x, y = self._anchor_xy(self.settings.get("island_position", "top-center"), width, height, available)
        x, y = self._clamp_to_screen(x, y, width, height, available)
        self.move(x, y)

    def _update_hit_mask(self, mode: str):
        if mode == "dot":
            self.setMask(QRegion(0, 0, self.width(), self.height(), QRegion.RegionType.Ellipse))
        else:
            self.clearMask()

    def _update_cursor(self, mode: str):
        if mode == "dot" and self.settings.get("click_to_open_controller", True):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif mode in ("notify", "expanded"):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    def _target_rect_for_mode(self, mode: str, old_mode: str, width: int, height: int) -> QRect:
        if mode == "hidden":
            return QRect(self.x(), self.y(), width, height)
        screen = QApplication.primaryScreen()
        if not screen:
            return QRect(self.x(), self.y(), width, height)
        available = screen.availableGeometry()
        if mode == "notify" and old_mode == "dot" and self.settings.get("show_island", True):
            dot_w, dot_h = 34, 34
            dot_x, dot_y = self._anchor_xy(self.settings.get("island_position", "top-center"), dot_w, dot_h, available)
            cx = dot_x + int(dot_w / 2)
            cy = dot_y + int(dot_h / 2)
            x = cx - int(width / 2)
            y = cy - int(height / 2)
            x, y = self._clamp_to_screen(x, y, width, height, available)
            return QRect(x, y, width, height)
        x, y = self._anchor_xy(self.settings.get("island_position", "top-center"), width, height, available)
        x, y = self._clamp_to_screen(x, y, width, height, available)
        return QRect(x, y, width, height)

    def _handle_click_action(self):
        if self.mode == "notify":
            self.set_mode("expanded")
            return
        if self.mode == "dot" and self.settings.get("click_to_open_controller", True):
            self.set_mode("expanded")

    def _notify_size_for_style(self, style: str) -> tuple[int, int]:
        if style == "compact_two_line":
            return (260, 64)
        if style == "icon_only_pulse":
            return (34, 34)
        return (220, 42)

    def _should_pulse_dot(self) -> bool:
        if self.mode != "dot":
            return False
        if not bool(self.payload.get("notification")):
            return False
        return self.settings.get("notification_style", "tiny_chip") == "icon_only_pulse"

    def _tick_pulse(self):
        self._pulse_phase += 0.32
        if self._should_pulse_dot():
            self.update()

    def _anchor_xy(self, position: str, width: int, height: int, available) -> tuple[int, int]:
        margin = 18
        valid = {
            "top-left",
            "top-center",
            "top-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
            "left-middle",
            "right-middle",
        }
        position = position if position in valid else "top-center"
        x = available.x() + int((available.width() - width) / 2)
        y = available.y() + margin
        if position == "top-left":
            x = available.x() + margin
            y = available.y() + margin
        elif position == "top-right":
            x = available.right() - width - margin
            y = available.y() + margin
        elif position == "bottom-left":
            x = available.x() + margin
            y = available.bottom() - height - margin
        elif position == "bottom-center":
            x = available.x() + int((available.width() - width) / 2)
            y = available.bottom() - height - margin
        elif position == "bottom-right":
            x = available.right() - width - margin
            y = available.bottom() - height - margin
        elif position == "left-middle":
            x = available.x() + margin
            y = available.y() + int((available.height() - height) / 2)
        elif position == "right-middle":
            x = available.right() - width - margin
            y = available.y() + int((available.height() - height) / 2)
        return x, y

    def _clamp_to_screen(self, x: int, y: int, width: int, height: int, available) -> tuple[int, int]:
        max_x = available.right() - width
        max_y = available.bottom() - height
        x = max(available.x(), min(x, max_x))
        y = max(available.y(), min(y, max_y))
        return x, y

    def _snap_to_nearest_anchor(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        cx = self.x() + int(self.width() / 2)
        cy = self.y() + int(self.height() / 2)
        positions = (
            "top-left",
            "top-center",
            "top-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
            "left-middle",
            "right-middle",
        )
        nearest = "top-center"
        nearest_dist = None
        for pos in positions:
            ax, ay = self._anchor_xy(pos, self.width(), self.height(), available)
            acx = ax + int(self.width() / 2)
            acy = ay + int(self.height() / 2)
            dist = (cx - acx) ** 2 + (cy - acy) ** 2
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist
                nearest = pos
        self.settings["island_position"] = nearest
        self._position_overridden = False
        self.set_mode(self.mode)
