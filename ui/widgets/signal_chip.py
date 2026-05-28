from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class SignalChip(QFrame):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("signalChip")
        self._accent = QColor("#66e2ff")
        self._attention = False
        self._variant = "normal"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 3, 7, 3)
        layout.setSpacing(5)
        self.dot = QLabel("●")
        self.dot.setObjectName("chipDot")
        self.text = QLabel(label)
        self.text.setObjectName("chipText")
        layout.addWidget(self.dot)
        layout.addWidget(self.text)
        self._refresh_style()

    def set_text(self, text: str):
        self.text.setText(text)

    def set_accent(self, color: str):
        self._accent = QColor(color)
        self._refresh_style()

    def set_attention(self, value: bool):
        self._attention = value
        self._refresh_style()

    def set_variant(self, variant: str):
        self._variant = variant
        self._refresh_style()

    def _refresh_style(self):
        dot_palette = {
            "normal": self._accent.name(),
            "away": "#9CE870",
            "error": "#FF5C7A",
            "calibrating-silence": "#FFD166",
            "calibrating-speech": "#66E2FF",
        }
        dot_color = dot_palette.get(self._variant, self._accent.name())
        text_color = self._accent.name() if self._attention else ""
        weight = "600" if self._attention else "500"
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 9px;")
        self.text.setStyleSheet(f"color: {text_color}; font-weight: {weight};")
