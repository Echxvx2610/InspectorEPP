"""
Ajustes del Sistema — layout minimalista.
"""

import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QSlider, QSpinBox, QCheckBox,
    QGridLayout
)

from src.ui.icons import icon_save
from src.ui.ui_helpers import set_role, tint_icon, Toast

class SettingsView(QWidget):
    settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_path = "config/settings.json"
        self.current_settings = self._defaults()
        self.toast = Toast(self)
        self._init_ui()
        self._load_settings()

    def _defaults(self):
        return {
            "default_camera": "0",
            "confidence_threshold": 0.50,
            "grace_period_frames": 10,
            "tts_enabled": True,
            "tts_cooldown_seconds": 4,
            "arduino_relay_enabled": False,
            "arduino_port": "COM3",
        }

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(16)

        # — Detección —
        card1 = QFrame()
        card1.setProperty("class", "card")
        card1.setMaximumWidth(760)
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(16, 16, 16, 16)
        c1.setSpacing(10)

        c1.addWidget(self._section_label("Detección"))

        g1 = QGridLayout()
        g1.setSpacing(8)
        g1.setColumnMinimumWidth(0, 220)
        g1.setColumnStretch(1, 1)
        g1.addWidget(set_role(QLabel("Fuente de video"), "field"), 0, 0)
        self.txt_cam = QLineEdit()
        self.txt_cam.setPlaceholderText("0  o  rtsp://...")
        g1.addWidget(self.txt_cam, 0, 1)

        g1.addWidget(set_role(QLabel("Umbral de confianza"), "field"), 1, 0)
        sl = QHBoxLayout()
        self.slider_conf = QSlider(Qt.Horizontal)
        self.slider_conf.setRange(20, 95)
        self.slider_conf.setValue(50)
        self.lbl_conf = QLabel("0.50")
        set_role(self.lbl_conf, "value-sm")
        self.lbl_conf.setMinimumWidth(32)
        self.slider_conf.valueChanged.connect(
            lambda v: self.lbl_conf.setText(f"{v / 100:.2f}")
        )
        sl.addWidget(self.slider_conf)
        sl.addWidget(self.lbl_conf)
        g1.addLayout(sl, 1, 1)
        c1.addLayout(g1)
        main.addWidget(card1)

        # — Temporalidad —
        card2 = QFrame()
        card2.setProperty("class", "card")
        card2.setMaximumWidth(760)
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(16, 16, 16, 16)
        c2.setSpacing(10)

        c2.addWidget(self._section_label("Temporalidad"))

        g2 = QGridLayout()
        g2.setSpacing(8)
        g2.setColumnMinimumWidth(0, 220)
        g2.setColumnStretch(1, 1)
        g2.addWidget(set_role(QLabel("Frames para confirmar violación"), "field"), 0, 0)
        self.spin_grace = QSpinBox()
        self.spin_grace.setRange(1, 60)
        self.spin_grace.setValue(10)
        self.spin_grace.setSuffix(" frames")
        self.spin_grace.setMaximumWidth(140)
        g2.addWidget(self.spin_grace, 0, 1)
        c2.addLayout(g2)
        main.addWidget(card2)

        # — Alertas —
        card3 = QFrame()
        card3.setProperty("class", "card")
        card3.setMaximumWidth(760)
        c3 = QVBoxLayout(card3)
        c3.setContentsMargins(16, 16, 16, 16)
        c3.setSpacing(10)

        c3.addWidget(self._section_label("Alertas y hardware"))

        self.chk_tts = QCheckBox("Síntesis de voz")
        self.chk_tts.setChecked(True)
        c3.addWidget(self.chk_tts)

        g3 = QGridLayout()
        g3.setSpacing(8)
        g3.setColumnMinimumWidth(0, 220)
        g3.setColumnStretch(1, 1)
        g3.addWidget(set_role(QLabel("Cooldown voz"), "field"), 0, 0)
        self.spin_cd = QSpinBox()
        self.spin_cd.setRange(1, 30)
        self.spin_cd.setValue(4)
        self.spin_cd.setSuffix(" s")
        self.spin_cd.setMaximumWidth(140)
        g3.addWidget(self.spin_cd, 0, 1)

        self.chk_relay = QCheckBox("Relé serial (Arduino)")
        g3.addWidget(self.chk_relay, 1, 0, 1, 2)

        g3.addWidget(set_role(QLabel("Puerto serial"), "field"), 2, 0)
        self.txt_port = QLineEdit()
        self.txt_port.setPlaceholderText("COM3  o  /dev/ttyUSB0")
        self.txt_port.setMaximumWidth(200)
        g3.addWidget(self.txt_port, 2, 1)
        c3.addLayout(g3)
        main.addWidget(card3)

        main.addStretch()

        btn_save = QPushButton("Guardar ajustes")
        btn_save.setIcon(tint_icon(icon_save(), "#ffffff"))
        btn_save.setProperty("class", "btn-primary")
        btn_save.clicked.connect(self._save_settings)
        foot = QHBoxLayout()
        foot.addStretch()
        foot.addWidget(btn_save)
        main.addLayout(foot)

    def _section_label(self, text):
        lbl = QLabel(text)
        set_role(lbl, "section")
        return lbl

    def _load_settings(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.current_settings = json.load(f)
            except Exception:
                pass
        s = self.current_settings
        self.txt_cam.setText(str(s.get("default_camera", "0")))
        v = int(s.get("confidence_threshold", 0.50) * 100)
        self.slider_conf.setValue(v)
        self.lbl_conf.setText(f"{v / 100:.2f}")
        self.spin_grace.setValue(s.get("grace_period_frames", 10))
        self.chk_tts.setChecked(s.get("tts_enabled", True))
        self.spin_cd.setValue(s.get("tts_cooldown_seconds", 4))
        self.chk_relay.setChecked(s.get("arduino_relay_enabled", False))
        self.txt_port.setText(s.get("arduino_port", "COM3"))

    def _save_settings(self):
        new = {
            "default_camera": self.txt_cam.text().strip() or "0",
            "confidence_threshold": self.slider_conf.value() / 100.0,
            "grace_period_frames": self.spin_grace.value(),
            "tts_enabled": self.chk_tts.isChecked(),
            "tts_cooldown_seconds": self.spin_cd.value(),
            "arduino_relay_enabled": self.chk_relay.isChecked(),
            "arduino_port": self.txt_port.text().strip() or "COM3",
        }
        self.current_settings = new
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(new, f, indent=2)
            self.toast.show_message("Ajustes guardados")
            self.settings_changed.emit(new)
        except Exception as e:
            self.toast.show_message("No se pudo guardar", "bad")
