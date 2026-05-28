from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QSizePolicy


class NotificationCard(QFrame):
    """Compact notification surface separate from the full media controller."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("notificationCard")
        self._style = "tiny_chip"
        self._raw_title = ""
        self._raw_subtitle = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.tiny_row = QWidget()
        tiny_layout = QHBoxLayout(self.tiny_row)
        tiny_layout.setContentsMargins(8, 0, 8, 0)
        tiny_layout.setSpacing(6)
        self.tiny_dot = QLabel("●")
        self.tiny_dot.setObjectName("notifyDot")
        self.tiny_dot.setFixedWidth(10)
        self.tiny_title = QLabel("")
        self.tiny_title.setObjectName("notifyTitle")
        self.tiny_title.setWordWrap(False)
        self.tiny_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tiny_layout.addWidget(self.tiny_dot)
        tiny_layout.addWidget(self.tiny_title, 1)

        self.compact_block = QWidget()
        compact_layout = QVBoxLayout(self.compact_block)
        compact_layout.setContentsMargins(10, 4, 10, 4)
        compact_layout.setSpacing(1)
        self.compact_title = QLabel("")
        self.compact_title.setObjectName("notifyTitle")
        self.compact_title.setWordWrap(False)
        self.compact_subtitle = QLabel("")
        self.compact_subtitle.setObjectName("notifySubtitle")
        self.compact_subtitle.setWordWrap(False)
        compact_layout.addWidget(self.compact_title)
        compact_layout.addWidget(self.compact_subtitle)

        root.addWidget(self.tiny_row)
        root.addWidget(self.compact_block)

    def set_style(self, style: str):
        self._style = style
        self.tiny_row.setVisible(style == "tiny_chip")
        self.compact_block.setVisible(style == "compact_two_line")

    def set_content(self, title: str, subtitle: str, accent: str):
        self._raw_title = title
        self._raw_subtitle = subtitle
        self.tiny_dot.setStyleSheet(f"color: {accent}; font-size: 8px;")
        self._refresh_text()

    def apply_theme(self, theme: dict[str, Any], accent: str):
        bg = theme.get("background", "#161A25")
        text = theme.get("text", "#F4F5FF")
        muted = theme.get("muted", "#A7B1C3")
        radius = 10 if self._style == "compact_two_line" else 8
        self.setStyleSheet(
            f"""
            #notificationCard {{
                border: 1px solid rgba({QColor(accent).red()}, {QColor(accent).green()}, {QColor(accent).blue()}, 90);
                border-radius: {radius}px;
                background: rgba({QColor(bg).red()}, {QColor(bg).green()}, {QColor(bg).blue()}, 145);
            }}
            #notifyTitle {{
                color: {text};
                font-size: 10px;
                font-weight: 600;
            }}
            #notifySubtitle {{
                color: {muted};
                font-size: 9px;
            }}
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_text()

    def _refresh_text(self):
        width = max(80, self.width() - 28)
        if self._style == "tiny_chip":
            self.tiny_title.setText(
                self.tiny_title.fontMetrics().elidedText(self._raw_title, Qt.TextElideMode.ElideRight, width)
            )
        elif self._style == "compact_two_line":
            self.compact_title.setText(
                self.compact_title.fontMetrics().elidedText(self._raw_title, Qt.TextElideMode.ElideRight, width)
            )
            self.compact_subtitle.setText(
                self.compact_subtitle.fontMetrics().elidedText(
                    self._raw_subtitle, Qt.TextElideMode.ElideRight, width
                )
            )
