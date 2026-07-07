from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsWindow(QWidget):
    def __init__(
        self,
        settings: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
        on_reset: Callable[[], dict[str, Any]],
        on_change: Callable[[dict[str, Any]], None] | None = None,
    ):
        super().__init__()
        self.settings = dict(settings)
        self.on_save = on_save
        self.on_reset = on_reset
        self.on_change = on_change
        self.controls: dict[str, Any] = {}
        self.color_inputs: dict[str, QLineEdit] = {}

        self.setWindowTitle("Hushline Settings")
        self.resize(720, 680)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        title = QLabel("Hushline Settings")
        title.setObjectName("settingsTitle")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setVerticalSpacing(12)

        self.controls["speech_trigger"] = self._spin(1, 15, int(settings["speech_trigger"]))
        self.controls["silence_trigger"] = self._spin(10, 80, int(settings["silence_trigger"]))
        self.controls["resume_delay"] = self._double_spin(0.1, 10.0, float(settings["resume_delay"]), 2, 0.1)
        self.controls["vad_aggressiveness"] = self._spin(0, 3, int(settings["vad_aggressiveness"]))
        self.controls["show_island"] = self._check(settings.get("show_island", True))
        self.controls["state_notifications_enabled"] = self._check(settings.get("state_notifications_enabled", True))
        self.controls["notify_when_circle_off"] = self._check(
            settings.get("notify_when_circle_off", False)
        )
        self.controls["click_to_open_controller"] = self._check(settings.get("click_to_open_controller", True))
        self.controls["collapse_ms"] = self._spin(1000, 12000, int(settings.get("collapse_ms", 4000)))
        self.controls["notify_collapse_ms"] = self._spin(800, 10000, int(settings.get("notify_collapse_ms", 2800)))
        self.controls["island_position"] = self._combo(
            [
                "top-left",
                "top-center",
                "top-right",
                "bottom-left",
                "bottom-center",
                "bottom-right",
                "left-middle",
                "right-middle",
            ],
            settings.get("island_position", "top-center"),
        )
        self.controls["notification_style"] = self._combo(
            ["tiny_chip", "compact_two_line", "icon_only_pulse"],
            settings.get("notification_style", "tiny_chip"),
        )

        labels = {
            "speech_trigger": "Sensitivity",
            "silence_trigger": "Silence tolerance",
            "resume_delay": "Resume delay",
            "vad_aggressiveness": "VAD strictness",
            "show_island": "Show hollow circle",
            "state_notifications_enabled": "Enable state notifications",
            "notify_when_circle_off": "Allow notifications when circle is OFF",
            "click_to_open_controller": "Circle click opens media controller",
            "collapse_ms": "Collapse duration",
            "notify_collapse_ms": "Notification duration",
            "island_position": "Island position",
            "notification_style": "Notification style",
        }
        for key, label in labels.items():
            form.addRow(label, self.controls[key])

        form.addRow(self._section_label("State colors"))
        for state, value in settings.get("state_colors", {}).items():
            edit = self._line(value)
            self.color_inputs[f"state_colors.{state}"] = edit
            form.addRow(state.capitalize(), edit)

        form.addRow(self._section_label("Controller colors"))
        for key, value in settings.get("controller_theme", {}).items():
            edit = self._line(value)
            self.color_inputs[f"controller_theme.{key}"] = edit
            form.addRow(key.capitalize(), edit)

        self._connect_change_signals()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        reset = QPushButton("Reset Appearance")
        save = QPushButton("Save")
        close = QPushButton("Close")
        reset.clicked.connect(self._reset)
        save.clicked.connect(self._save)
        close.clicked.connect(self.hide)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        buttons.addWidget(close)
        buttons.addWidget(save)
        outer.addLayout(buttons)

        self.setStyleSheet(
            """
            QWidget { background: #10141d; color: #f4f5ff; font-family: Segoe UI; }
            #settingsTitle { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
            QLineEdit, QSpinBox, QComboBox {
                background: #171d2a; border: 1px solid #35405a;
                border-radius: 6px; min-height: 28px; padding: 3px 8px;
            }
            QPushButton {
                background: #20283a; border: 1px solid #35405a;
                border-radius: 7px; padding: 8px 14px;
            }
            QPushButton:hover { background: #2b354d; }
            QScrollArea { border: none; }
            """
        )

    def update_settings(self, settings: dict[str, Any]):
        self.settings = dict(settings)
        for key, control in self.controls.items():
            if key not in settings:
                continue
            value = settings[key]
            control.blockSignals(True)
            try:
                if isinstance(control, QSpinBox):
                    control.setValue(int(value))
                elif isinstance(control, QCheckBox):
                    control.setChecked(bool(value))
                elif isinstance(control, QComboBox):
                    text = str(value)
                    index = control.findText(text)
                    if index >= 0:
                        control.setCurrentIndex(index)
                elif isinstance(control, QDoubleSpinBox):
                    control.setValue(float(value))
                elif isinstance(control, QLineEdit):
                    control.setText(str(value))
            finally:
                control.blockSignals(False)
        for key, edit in self.color_inputs.items():
            group, name = key.split(".", 1)
            edit.blockSignals(True)
            try:
                if group == "state_colors":
                    edit.setText(str(settings.get("state_colors", {}).get(name, "")))
                else:
                    edit.setText(str(settings.get("controller_theme", {}).get(name, "")))
            finally:
                edit.blockSignals(False)

    def _spin(self, mn: int, mx: int, value: int):
        spin = QSpinBox()
        spin.setRange(mn, mx)
        spin.setValue(value)
        return spin

    def _double_spin(self, mn: float, mx: float, value: float, decimals: int = 2, step: float = 0.1):
        spin = QDoubleSpinBox()
        spin.setRange(mn, mx)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setValue(value)
        return spin

    def _line(self, value: str):
        edit = QLineEdit(value)
        return edit

    def _check(self, value: bool):
        check = QCheckBox()
        check.setChecked(bool(value))
        return check

    def _combo(self, options: list[str], value: str):
        combo = QComboBox()
        combo.addItems(options)
        combo.setCurrentText(value)
        return combo

    def _section_label(self, text: str):
        label = QLabel(text)
        label.setStyleSheet("font-size: 15px; font-weight: 700; margin-top: 14px;")
        return label

    def _connect_change_signals(self):
        for control in list(self.controls.values()):
            if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                control.valueChanged.connect(self._on_control_changed)
            elif isinstance(control, QCheckBox):
                control.toggled.connect(self._on_control_changed)
            elif isinstance(control, QComboBox):
                control.currentTextChanged.connect(self._on_control_changed)
            elif isinstance(control, QLineEdit):
                control.textChanged.connect(self._on_control_changed)
        for edit in list(self.color_inputs.values()):
            edit.textChanged.connect(self._on_control_changed)

    def _save(self):
        next_settings = self._collect_current_settings()
        self.settings = next_settings
        self.on_save(next_settings)

    def _reset(self):
        settings = self.on_reset()
        self.hide()
        self.deleteLater()

    def _collect_current_settings(self) -> dict[str, Any]:
        next_settings = dict(self.settings)
        for key, control in self.controls.items():
            if isinstance(control, QSpinBox):
                next_settings[key] = control.value()
            elif isinstance(control, QDoubleSpinBox):
                next_settings[key] = float(control.value())
            elif isinstance(control, QCheckBox):
                next_settings[key] = control.isChecked()
            elif isinstance(control, QComboBox):
                next_settings[key] = control.currentText()
            elif isinstance(control, QLineEdit):
                text = control.text().strip()
                try:
                    next_settings[key] = float(text)
                except ValueError:
                    next_settings[key] = self.settings.get(key, text)
        state_colors = dict(next_settings.get("state_colors", {}))
        controller_theme = dict(next_settings.get("controller_theme", {}))
        for key, edit in self.color_inputs.items():
            group, name = key.split(".", 1)
            if group == "state_colors":
                state_colors[name] = edit.text()
            else:
                controller_theme[name] = edit.text()
        next_settings["state_colors"] = state_colors
        next_settings["controller_theme"] = controller_theme
        return next_settings

    def _on_control_changed(self, *_args):
        draft = self._collect_current_settings()
        if self.on_change:
            try:
                self.on_change(draft)
            except Exception:
                pass
