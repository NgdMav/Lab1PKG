import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QStatusBar, QColorDialog, QStyleFactory
)
from PySide6.QtGui import QColor
from ui_controls import ModelPanel
from models import srgb_to_hex, hex_to_srgb, clamp01, rgb_norm_to_ui, srgb_to_hls, srgb_to_cmyk, srgb_to_hls, srgb_to_hex

class ColorLabApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ColorLab — CMYK ↔ RGB ↔ HLS (PySide6)")
        self.setMinimumSize(920, 480)

        # internal color: normalized sRGB tuple
        self.rgb = (1.0, 0.0, 0.0)  # initial red

        root = QVBoxLayout(self)

        # top controls: HEX, buttons, warning
        top = QHBoxLayout()
        root.addLayout(top)
        top.addWidget(QLabel("HEX:"))
        self.hex_edit = QLineEdit()
        self.hex_edit.setFixedWidth(120)
        self.hex_edit.setText(srgb_to_hex(self.rgb))
        self.hex_edit.returnPressed.connect(self._hex_entered)
        top.addWidget(self.hex_edit)

        self.btn_copy_hex = QPushButton("Копировать HEX")
        self.btn_copy_hex.clicked.connect(self._copy_hex)
        top.addWidget(self.btn_copy_hex)

        self.btn_pick = QPushButton("Выбрать из палитры…")
        self.btn_pick.clicked.connect(self._pick_color)
        top.addWidget(self.btn_pick)

        top.addStretch(1)
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #B45309;")  # amber
        top.addWidget(self.warning_label)

        # middle: three panels + preview
        mid = QHBoxLayout()
        root.addLayout(mid, stretch=1)

        self.panel_cmyk = ModelPanel("CMYK")
        self.panel_rgb = ModelPanel("RGB")
        self.panel_hls = ModelPanel("HLS")
        mid.addWidget(self.panel_cmyk, 1)
        mid.addWidget(self.panel_rgb, 1)
        mid.addWidget(self.panel_hls, 1)

        # preview
        preview_col = QVBoxLayout()
        mid.addLayout(preview_col)
        self.preview = QFrame()
        self.preview.setFixedSize(180, 140)
        self.preview.setFrameShape(QFrame.Box)
        preview_col.addWidget(self.preview)
        self.info_label = QLabel("")
        preview_col.addWidget(self.info_label)
        preview_col.addStretch(1)

        # statusbar
        self.status = QStatusBar()
        root.addWidget(self.status)

        # connect signals
        self.panel_cmyk.anyValueChanged.connect(lambda: self._panel_changed(self.panel_cmyk))
        self.panel_rgb.anyValueChanged.connect(lambda: self._panel_changed(self.panel_rgb))
        self.panel_hls.anyValueChanged.connect(lambda: self._panel_changed(self.panel_hls))

        self.panel_cmyk.modelChanged.connect(lambda: self.panel_cmyk.set_from_srgb(self.rgb))
        self.panel_rgb.modelChanged.connect(lambda: self.panel_rgb.set_from_srgb(self.rgb))
        self.panel_hls.modelChanged.connect(lambda: self.panel_hls.set_from_srgb(self.rgb))

        # initial sync
        self._apply_rgb(self.rgb, source=None, clipped=False)

    def _copy_hex(self):
        QApplication.clipboard().setText(self.hex_edit.text())
        self.status.showMessage("HEX скопирован в буфер обмена", 1500)

    def _pick_color(self):
        r_i, g_i, b_i = rgb_norm_to_ui(self.rgb)
        initial = QColor(r_i, g_i, b_i)
        color = QColorDialog.getColor(initial, self, "Выбор цвета (sRGB)")
        if color.isValid():
            rgb = (color.red()/255.0, color.green()/255.0, color.blue()/255.0)
            self._apply_rgb(rgb, source=None, clipped=False)

    def _hex_entered(self):
        txt = self.hex_edit.text().strip()
        try:
            rgb = hex_to_srgb(txt)
        except Exception:
            self.status.showMessage("Некорректный HEX. Формат: #RRGGBB", 2000)
            return
        self._apply_rgb(rgb, source=None, clipped=False)

    def _panel_changed(self, panel):
        rgb_norm, clipped = panel.to_srgb()
        self._apply_rgb(rgb_norm, source=panel, clipped=clipped)

    def _apply_rgb(self, rgb_norm, source, clipped):
        # normalize
        r = clamp01(rgb_norm[0])
        g = clamp01(rgb_norm[1])
        b = clamp01(rgb_norm[2])
        self.rgb = (r, g, b)

        # update other panels
        if source is not self.panel_cmyk:
            self.panel_cmyk.set_from_srgb(self.rgb)
        if source is not self.panel_rgb:
            self.panel_rgb.set_from_srgb(self.rgb)
        if source is not self.panel_hls:
            self.panel_hls.set_from_srgb(self.rgb)

        # preview color
        qcol = QColor(int(round(r*255)), int(round(g*255)), int(round(b*255)))
        self.preview.setStyleSheet(f"background-color: {qcol.name()};")
        self.hex_edit.setText(srgb_to_hex(self.rgb))

        # info: show sample HLS and CMYK
        hls = srgb_to_hls(self.rgb)
        cmyk = srgb_to_cmyk(self.rgb)
        self.info_label.setText(
            f"H: {hls[0]:.1f}°, L: {hls[1]:.1f}%, S: {hls[2]:.1f}%\n"
            f"C: {cmyk[0]:.1f}%, M: {cmyk[1]:.1f}%, Y: {cmyk[2]:.1f}%, K: {cmyk[3]:.1f}%"
        )

        # warning label for clipping (we only get clipped flag from panel->to_srgb)
        self.warning_label.setText("Внимание: произошло обрезание (clipping)" if clipped else "")

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    w = ColorLabApp()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
