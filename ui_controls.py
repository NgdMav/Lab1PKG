from PySide6.QtWidgets import (
    QWidget, QLabel, QSlider, QDoubleSpinBox, QGridLayout, QVBoxLayout,
    QComboBox
)
from PySide6.QtCore import Qt, Signal
from dataclasses import dataclass
from typing import List
from models import convert_from_srgb, convert_to_srgb

@dataclass
class ChannelSpec:
    name: str
    vmin: float
    vmax: float
    decimals: int
    slider_scale: int

# Specs for the three panels we use
MODEL_SPECS = {
    "RGB": [
        ChannelSpec("R", 0, 255, 0, 1),
        ChannelSpec("G", 0, 255, 0, 1),
        ChannelSpec("B", 0, 255, 0, 1),
    ],
    "CMYK": [
        ChannelSpec("C", 0, 100, 2, 100),
        ChannelSpec("M", 0, 100, 2, 100),
        ChannelSpec("Y", 0, 100, 2, 100),
        ChannelSpec("K", 0, 100, 2, 100),
    ],
    "HLS": [
        ChannelSpec("H", 0, 360, 2, 100),
        ChannelSpec("L", 0, 100, 2, 100),
        ChannelSpec("S", 0, 100, 2, 100),
    ],
}

class ChannelControl(QWidget):
    valueChanged = Signal(float)  # emit single numeric value (for convenience)

    def __init__(self, spec: ChannelSpec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self._block = False

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.label = QLabel(spec.name)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(spec.vmin * spec.slider_scale), int(spec.vmax * spec.slider_scale))
        self.slider.setSingleStep(1)

        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(spec.decimals)
        self.spin.setRange(spec.vmin, spec.vmax)
        self.spin.setSingleStep(1.0 / (spec.slider_scale))
        self.spin.setKeyboardTracking(False)

        layout.addWidget(self.label, 0, 0)
        layout.addWidget(self.slider, 0, 1)
        layout.addWidget(self.spin, 0, 2)

        self.slider.valueChanged.connect(self._on_slider)
        self.spin.valueChanged.connect(self._on_spin)

    def _on_slider(self, v: int):
        if self._block:
            return
        val = v / self.spec.slider_scale
        self._block = True
        try:
            self.spin.setValue(val)
        finally:
            self._block = False
        self.valueChanged.emit(val)

    def _on_spin(self, val: float):
        if self._block:
            return
        sval = int(round(val * self.spec.slider_scale))
        self._block = True
        try:
            self.slider.setValue(sval)
        finally:
            self._block = False
        self.valueChanged.emit(val)

    def setValue(self, val: float):
        self._block = True
        try:
            self.spin.setValue(val)
            self.slider.setValue(int(round(val * self.spec.slider_scale)))
        finally:
            self._block = False

    def value(self) -> float:
        return float(self.spin.value())

class ModelPanel(QWidget):
    anyValueChanged = Signal()
    modelChanged = Signal()

    def __init__(self, initial_model: str, parent=None):
        super().__init__(parent)
        self.current_model = initial_model
        main = QVBoxLayout(self)
        top = QGridLayout()
        main.addLayout(top)
        top.addWidget(QLabel("Модель:"), 0, 0)
        self.combo = QComboBox()
        self.combo.addItems(list(MODEL_SPECS.keys()))
        self.combo.setCurrentText(initial_model)
        self.combo.currentTextChanged.connect(self._rebuild)
        top.addWidget(self.combo, 0, 1)

        self.controls_layout = QVBoxLayout()
        main.addLayout(self.controls_layout)

        self.controls: List[ChannelControl] = []
        self._block = False
        self._rebuild(initial_model)

    def _clear_controls(self):
        while self.controls_layout.count():
            item = self.controls_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.controls.clear()

    def _rebuild(self, model_name: str):
        self.current_model = model_name
        self._clear_controls()
        specs = MODEL_SPECS[model_name]
        for spec in specs:
            cc = ChannelControl(spec)
            cc.valueChanged.connect(self._on_any)
            self.controls_layout.addWidget(cc)
            self.controls.append(cc)
        self.modelChanged.emit()

    def _on_any(self, _v: float):
        if not self._block:
            self.anyValueChanged.emit()

    # API
    def set_from_srgb(self, rgb_norm):
        """Update UI controls according to rgb (normalized) without emitting change."""
        self._block = True
        try:
            vals = convert_from_srgb(self.current_model, rgb_norm)
            for cc, v in zip(self.controls, vals):
                cc.setValue(v)
        finally:
            self._block = False

    def to_srgb(self):
        """Return (rgb_norm, clipped) from current controls."""
        vals = [c.value() for c in self.controls]
        return convert_to_srgb(self.current_model, vals)
