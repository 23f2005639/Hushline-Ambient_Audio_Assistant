import math

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt


class VoiceBars(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = "idle"
        self.bar_count = 8
        self._phase = 0.0
        self._levels = [0.2] * self.bar_count
        self._accent = QColor("#66e2ff")
        self._profiles = {
            "playback": {"speed": 0.23, "amp": 0.24, "base": 0.22, "cap": 0.62},
            "listening": {"speed": 0.20, "amp": 0.22, "base": 0.21, "cap": 0.58},
            "speaking": {"speed": 0.44, "amp": 0.42, "base": 0.24, "cap": 0.9},
            "paused": {"speed": 0.08, "amp": 0.05, "base": 0.12, "cap": 0.25},
            "away": {"speed": 0.14, "amp": 0.12, "base": 0.16, "cap": 0.38},
            "idle": {"speed": 0.12, "amp": 0.1, "base": 0.15, "cap": 0.36},
        }
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.setMinimumSize(66, 24)

    def set_mode(self, mode: str):
        self.mode = mode

    def set_accent(self, color: str):
        self._accent = QColor(color)
        self.update()

    def _tick(self):
        profile = self._profiles.get(self.mode, self._profiles["idle"])
        self._phase += profile["speed"]
        for i in range(self.bar_count):
            offset = i * 0.58
            wave = (math.sin(self._phase + offset) + 1.0) * 0.5
            harmonic = (math.sin(self._phase * 0.5 + offset * 1.7) + 1.0) * 0.5
            level = profile["base"] + profile["amp"] * (0.72 * wave + 0.28 * harmonic)
            self._levels[i] = max(profile["base"], min(profile["cap"], level))
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._accent)
        if self.mode in ("away", "idle", "playback", "listening"):
            color.setAlpha(180)
        bar_gap = 2
        bar_width = max(3, int((self.width() - (self.bar_count - 1) * bar_gap) / self.bar_count))
        for i in range(self.bar_count):
            level = self._levels[i]
            h = max(4, int(level * (self.height() - 2)))
            x = i * (bar_width + bar_gap)
            y = self.height() - h
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(x, y, bar_width, h, 2, 2)
