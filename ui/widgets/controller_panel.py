from typing import Any, Callable

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QSizePolicy,
)

from .signal_chip import SignalChip
from .voice_bars import VoiceBars


class ControllerPanel(QFrame):
    def __init__(self, on_media_cmd: Callable[[str], None], on_open_settings: Callable[[], None]):
        super().__init__()
        self.on_media_cmd = on_media_cmd
        self.on_open_settings = on_open_settings
        self.mode = "idle"
        self.progress_value = 0
        self._panel_alpha = 0.88
        self.setObjectName("controllerFrame")
        self.setFrameShape(QFrame.Shape.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 8)
        outer.setSpacing(7)

        island = QFrame()
        island.setObjectName("island")
        island_row = QHBoxLayout(island)
        island_row.setContentsMargins(10, 8, 10, 8)
        island_row.setSpacing(8)

        self.album_dot = QLabel("▶")
        self.album_dot.setObjectName("albumDot")
        self.album_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_dot.setFixedSize(40, 40)

        copy_col = QVBoxLayout()
        copy_col.setSpacing(0)
        self.title = QLabel("Nothing playing")
        self.title.setObjectName("title")
        self.title.setWordWrap(False)
        self.title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.subtitle = QLabel("Ambient controller ready")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setWordWrap(False)
        self.subtitle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        copy_col.addWidget(self.title)
        copy_col.addWidget(self.subtitle)

        self.voice_bars = VoiceBars()
        island_row.addWidget(self.album_dot)
        island_row.addLayout(copy_col, 1)
        island_row.addWidget(self.voice_bars)
        outer.addWidget(island)

        self.track_row = QHBoxLayout()
        self.track_row.setContentsMargins(0, 0, 0, 0)
        self.track = QLabel("Media idle")
        self.track.setObjectName("track")
        self.track.setWordWrap(False)
        self.track.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.track_row.addWidget(self.track)
        self.track_row.addStretch(1)
        self.track_row.addWidget(self.percent)
        outer.addLayout(self.track_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setObjectName("progressBar")
        outer.addWidget(self.progress)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        prev = QPushButton("⏮")
        play = QPushButton("▶")
        nxt = QPushButton("⏭")
        settings_button = QPushButton("⚙")
        for button in (prev, play, nxt, settings_button):
            button.setObjectName("controlButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        play.setObjectName("primaryButton")
        prev.clicked.connect(lambda: self.on_media_cmd("prev"))
        play.clicked.connect(lambda: self.on_media_cmd("toggle"))
        nxt.clicked.connect(lambda: self.on_media_cmd("next"))
        settings_button.clicked.connect(self.on_open_settings)
        self.play_button = play
        controls.addWidget(prev)
        controls.addWidget(play)
        controls.addWidget(nxt)
        controls.addStretch(1)
        controls.addWidget(settings_button)
        outer.addLayout(controls)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        self.presence_chip = SignalChip("At desk")
        self.voice_chip = SignalChip("Quiet")
        chips.addWidget(self.presence_chip)
        chips.addWidget(self.voice_chip)
        chips.addStretch(1)
        outer.addLayout(chips)
        self.notify_hint = QLabel("Click to open controls")
        self.notify_hint.setObjectName("notifyHint")
        self.notify_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        outer.addWidget(self.notify_hint)

        self.progress_anim = QPropertyAnimation(self, b"animatedProgress")
        self.progress_anim.setDuration(450)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._raw_title = "Nothing playing"
        self._raw_subtitle = "Ambient controller ready"
        self._raw_track = "Media idle"
        self.notify_hint.setVisible(False)

    def get_animated_progress(self) -> float:
        return float(self.progress_value)

    def set_animated_progress(self, value: float):
        self.progress_value = max(0, min(100, int(value)))
        self.progress.setValue(self.progress_value)
        self.percent.setText(f"{self.progress_value}%")

    animatedProgress = Property(float, get_animated_progress, set_animated_progress)

    def set_state_snapshot(self, snapshot: dict[str, Any]):
        self.mode = snapshot["mode"]
        self._raw_title = snapshot["title"]
        self._raw_subtitle = snapshot["note"]
        self._raw_track = snapshot["track"]
        self._update_elided_labels()
        self.presence_chip.set_text(snapshot["presence"])
        self.voice_chip.set_text(snapshot["voice"])
        self.presence_chip.set_variant(snapshot.get("presence_variant", "normal"))
        self.voice_chip.set_variant(snapshot.get("voice_variant", "normal"))
        self.presence_chip.set_attention(snapshot.get("presence_attention", snapshot["presence"] == "Away"))
        self.voice_chip.set_attention(snapshot.get("voice_attention", False))
        self.voice_bars.set_mode(snapshot["mode"])
        icon = "⏸" if snapshot["mode"] in ("paused", "away") else "▶"
        self.album_dot.setText(icon)

    def set_media(self, media: dict[str, Any]):
        title = media.get("title") or "Nothing playing"
        artist = media.get("artist") or "-"
        playing = bool(media.get("playing"))
        progress = int(media.get("progress") or 0)
        self._raw_title = title
        self._raw_subtitle = artist
        self._raw_track = "Media playing" if playing else "Media paused"
        self._update_elided_labels()
        self.play_button.setText("⏸" if playing else "▶")
        self.progress_anim.stop()
        self.progress_anim.setStartValue(self.progress_value)
        self.progress_anim.setEndValue(progress)
        self.progress_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_labels()

    def _update_elided_labels(self):
        self.title.setText(self.title.fontMetrics().elidedText(self._raw_title, Qt.TextElideMode.ElideRight, max(40, self.title.width())))
        self.subtitle.setText(
            self.subtitle.fontMetrics().elidedText(self._raw_subtitle, Qt.TextElideMode.ElideRight, max(40, self.subtitle.width()))
        )
        self.track.setText(self.track.fontMetrics().elidedText(self._raw_track, Qt.TextElideMode.ElideRight, max(40, self.track.width())))

    def apply_style(self, theme: dict[str, Any], accent: str):
        bg = theme.get("background", "#151526")
        surface = theme.get("surface", "#202038")
        text = theme.get("text", "#F4F5FF")
        muted = theme.get("muted", "#AAB6C8")
        self.voice_bars.set_accent(accent)
        self.presence_chip.set_accent(accent)
        self.voice_chip.set_accent(accent)
        self.setStyleSheet(
            f"""
            #controllerFrame {{
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                background: rgba({QColor(bg).red()}, {QColor(bg).green()}, {QColor(bg).blue()}, 204);
            }}
            #island {{
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 999px;
                background: rgba(6, 10, 14, 230);
            }}
            #albumDot {{
                border-radius: 20px;
                color: #071017;
                font-size: 16px;
                font-weight: 700;
                background: {accent};
            }}
            #title {{
                color: {text};
                font-size: 12px;
                font-weight: 700;
            }}
            #subtitle, #track, #percent {{
                color: {muted};
                font-size: 10px;
            }}
            #progressBar {{
                min-height: 5px;
                max-height: 5px;
                border-radius: 2px;
                background: rgba(255, 255, 255, 0.10);
            }}
            #progressBar::chunk {{
                border-radius: 2px;
                background: {accent};
            }}
            #signalChip {{
                border: 1px solid rgba(255, 255, 255, 0.11);
                border-radius: 7px;
                background: rgba({QColor(surface).red()}, {QColor(surface).green()}, {QColor(surface).blue()}, 148);
            }}
            #chipText {{
                color: {text};
                font-size: 10px;
            }}
            QPushButton {{
                border: 1px solid rgba(255,255,255,0.08);
                background: transparent;
                color: {muted};
                min-width: 26px;
                min-height: 26px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.10);
                color: {text};
            }}
            #primaryButton {{
                color: {accent};
                font-size: 14px;
                font-weight: 700;
            }}
            #notifyHint {{
                color: {muted};
                font-size: 10px;
                padding-right: 2px;
            }}
            """
        )
