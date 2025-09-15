import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QStatusBar, QColorDialog, QStyleFactory
)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
from ui_controls import ModelPanel
from models import srgb_to_hex, hex_to_srgb, clamp01, rgb_norm_to_ui, srgb_to_hls, srgb_to_cmyk

class ColorLabApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ColorLab — CMYK ↔ RGB ↔ HLS")
        self.setFixedSize(960, 540)

        self.rgb = (1.0, 0.0, 0.0)

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 10, 15, 10)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        root.addLayout(top)

        hex_label = QLabel("HEX:")
        hex_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top.addWidget(hex_label)

        self.hex_edit = QLineEdit()
        self.hex_edit.setFixedWidth(120)
        self.hex_edit.setText(srgb_to_hex(self.rgb))
        self.hex_edit.returnPressed.connect(self._hex_entered)
        self.hex_edit.setToolTip("Введите HEX цвет в формате #RRGGBB")
        top.addWidget(self.hex_edit)

        self.btn_copy_hex = QPushButton("📋 Копировать")
        self.btn_copy_hex.clicked.connect(self._copy_hex)
        self.btn_copy_hex.setToolTip("Скопировать HEX в буфер обмена")
        top.addWidget(self.btn_copy_hex)

        self.btn_pick = QPushButton("🎨 Палитра…")
        self.btn_pick.clicked.connect(self._pick_color)
        self.btn_pick.setToolTip("Выбрать цвет из палитры")
        top.addWidget(self.btn_pick)

        top.addStretch(1)
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red; font-weight: bold;")
        top.addWidget(self.warning_label)

        mid = QHBoxLayout()
        mid.setSpacing(20)
        root.addLayout(mid, stretch=1)

        self.panel_cmyk = ModelPanel("CMYK")
        self.panel_rgb = ModelPanel("RGB")
        self.panel_hls = ModelPanel("HLS")

        mid.addWidget(self.panel_cmyk, 1)
        mid.addWidget(self.panel_rgb, 1)
        mid.addWidget(self.panel_hls, 1)

        preview_col = QVBoxLayout()
        preview_col.setSpacing(10)
        mid.addLayout(preview_col)

        self.preview = QFrame()
        self.preview.setFixedSize(200, 160)
        self.preview.setFrameShape(QFrame.Box)
        self.preview.setStyleSheet(
            "border: 2px solid #333; border-radius: 12px;"
        )
        preview_col.addWidget(self.preview, alignment=Qt.AlignCenter)

        self.hex_big = QLabel(srgb_to_hex(self.rgb))
        self.hex_big.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.hex_big.setAlignment(Qt.AlignCenter)
        preview_col.addWidget(self.hex_big)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        preview_col.addWidget(self.info_label)

        preview_col.addStretch(1)

        self.status = QStatusBar()
        root.addWidget(self.status)

        self.panel_cmyk.anyValueChanged.connect(lambda: self._panel_changed(self.panel_cmyk))
        self.panel_rgb.anyValueChanged.connect(lambda: self._panel_changed(self.panel_rgb))
        self.panel_hls.anyValueChanged.connect(lambda: self._panel_changed(self.panel_hls))

        self.panel_cmyk.modelChanged.connect(lambda: self.panel_cmyk.set_from_srgb(self.rgb))
        self.panel_rgb.modelChanged.connect(lambda: self.panel_rgb.set_from_srgb(self.rgb))
        self.panel_hls.modelChanged.connect(lambda: self.panel_hls.set_from_srgb(self.rgb))

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
        r = clamp01(rgb_norm[0])
        g = clamp01(rgb_norm[1])
        b = clamp01(rgb_norm[2])
        self.rgb = (r, g, b)

        if source is not self.panel_cmyk:
            self.panel_cmyk.set_from_srgb(self.rgb)
        if source is not self.panel_rgb:
            self.panel_rgb.set_from_srgb(self.rgb)
        if source is not self.panel_hls:
            self.panel_hls.set_from_srgb(self.rgb)

        qcol = QColor(int(round(r*255)), int(round(g*255)), int(round(b*255)))
        self.preview.setStyleSheet(
            f"background-color: {qcol.name()}; border: 2px solid #333; border-radius: 12px;"
        )
        self.hex_edit.setText(srgb_to_hex(self.rgb))
        self.hex_big.setText(srgb_to_hex(self.rgb))

        hls = srgb_to_hls(self.rgb)
        cmyk = srgb_to_cmyk(self.rgb)
        self.info_label.setText(
            f"H: {hls[0]:.1f}° | L: {hls[1]:.1f}% | S: {hls[2]:.1f}%\n"
            f"C: {cmyk[0]:.1f}% | M: {cmyk[1]:.1f}% | Y: {cmyk[2]:.1f}% | K: {cmyk[3]:.1f}%"
        )

        self.warning_label.setText("⚠ Clipping (обрезание гаммы)" if clipped else "")

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    w = ColorLabApp()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
