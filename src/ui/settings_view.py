"""
Ajustes del Sistema — PyQt-Fluent-Widgets.
Reestructurado con el patrón nativo de qfluentwidgets: SettingCardGroup + SettingCards.
"""

import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QLabel

from qfluentwidgets import (
    ScrollArea, SettingCardGroup, SettingCard, PushSettingCard,
    SwitchSettingCard, Slider, SpinBox, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, SubtitleLabel
)

from src import paths

SETTINGS_PATH = str(paths.SETTINGS_PATH)  # absoluta: ver src/paths.py


class _InputMixin:
    """Añade un widget de entrada al lado derecho de una SettingCard."""

    def _add_widget(self, widget):
        self.hBoxLayout.insertWidget(1, widget, 0, Qt.AlignRight)
        widget.setFixedWidth(220)


class ConfidenceCard(SettingCard, _InputMixin):
    """Umbral de confianza con Slider Fluent.

    No usamos RangeSettingCard porque exige un ConfigItem de qconfig;
    con un Slider dentro de una SettingCard el resultado es el mismo
    y no requiere el sistema de configuración de qfluentwidgets.
    """

    def __init__(self, config, parent=None):
        super().__init__(FIF.SPEED_HIGH, "Umbral de confianza",
                         "Confianza mínima del detector YOLO", parent=parent)
        self.config = config

        self.slider = Slider(Qt.Horizontal, self)
        self.slider.setRange(20, 95)
        self.slider.setValue(int(config.get("confidence_threshold", 0.50) * 100))
        self.slider.setMinimumWidth(160)

        self.value_lbl = QLabel(f"{self.slider.value() / 100:.2f}", self)
        self.value_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.value_lbl.setMinimumWidth(36)

        row = QWidget(self)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self.slider)
        lay.addWidget(self.value_lbl)
        self._add_widget(row)

        self.slider.valueChanged.connect(
            lambda v: self.value_lbl.setText(f"{v / 100:.2f}")
        )

    def value(self):
        return self.slider.value() / 100.0


class CameraCard(SettingCard, _InputMixin):
    """Fuente de video (índice, RTSP o ruta de archivo)."""

    def __init__(self, config, parent=None):
        super().__init__(FIF.VIDEO, "Fuente de video",
                         "Índice (0, 1...) o URL RTSP", parent=parent)
        self.config = config
        self.edit = LineEdit(self)
        self.edit.setPlaceholderText("0  o  rtsp://...")
        self._add_widget(self.edit)
        self.edit.setText(str(config.get("default_camera", "0")))

    def value(self):
        return self.edit.text().strip() or "0"


class PortCard(SettingCard, _InputMixin):
    """Puerto serial del Arduino."""

    def __init__(self, config, parent=None):
        super().__init__(FIF.SYNC, "Puerto serial",
                         "COM3 en Windows, /dev/ttyUSB0 en Linux", parent=parent)
        self.config = config
        self.edit = LineEdit(self)
        self.edit.setPlaceholderText("COM3  o  /dev/ttyUSB0")
        self._add_widget(self.edit)
        self.edit.setText(config.get("arduino_port", "COM3"))

    def value(self):
        return self.edit.text().strip() or "COM3"


class GraceSpinCard(SettingCard, _InputMixin):
    """Frames para confirmar violación (anti-parpadeo)."""

    def __init__(self, config, parent=None):
        super().__init__(FIF.STOP_WATCH, "Frames para confirmar violación",
                         "Filtro temporal: frames consecutivos antes de alarmar", parent=parent)
        self.config = config
        self.spin = SpinBox(self)
        self.spin.setRange(1, 60)
        self.spin.setValue(config.get("grace_period_frames", 10))
        self.spin.setSuffix(" frames")
        self._add_widget(self.spin)

    def value(self):
        return self.spin.value()


class CooldownSpinCard(SettingCard, _InputMixin):
    """Cooldown de síntesis de voz."""

    def __init__(self, config, parent=None):
        super().__init__(FIF.VOLUME, "Cooldown voz",
                         "Segundos entre advertencias habladas", parent=parent)
        self.config = config
        self.spin = SpinBox(self)
        self.spin.setRange(1, 30)
        self.spin.setValue(config.get("tts_cooldown_seconds", 4))
        self.spin.setSuffix(" s")
        self._add_widget(self.spin)

    def value(self):
        return self.spin.value()


class SettingsView(ScrollArea):
    settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsView")
        self.setWidgetResizable(True)

        self.current_settings = self._defaults()
        self._load_settings()

        self.container = QWidget()
        self.vBox = QVBoxLayout(self.container)
        self.vBox.setContentsMargins(32, 16, 32, 16)
        self.vBox.setSpacing(16)
        self.setWidget(self.container)

        # Título de la vista
        self.title = SubtitleLabel("Ajustes del sistema")
        self.vBox.addWidget(self.title)

        # ── Grupo: Detección ──
        self.grp_detection = SettingCardGroup("Detección", self.container)
        self.card_cam = CameraCard(self.current_settings, self.grp_detection)
        self.card_conf = ConfidenceCard(self.current_settings, self.grp_detection)
        self.grp_detection.addSettingCards([self.card_cam, self.card_conf])
        self.vBox.addWidget(self.grp_detection, 0, Qt.AlignTop)

        # ── Grupo: Temporalidad ──
        self.grp_temporal = SettingCardGroup("Temporalidad", self.container)
        self.card_grace = GraceSpinCard(self.current_settings, self.grp_temporal)
        self.grp_temporal.addSettingCard(self.card_grace)
        self.vBox.addWidget(self.grp_temporal, 0, Qt.AlignTop)

        # ── Grupo: Alertas y hardware ──
        self.grp_alerts = SettingCardGroup("Alertas y hardware", self.container)
        self.card_tts = SwitchSettingCard(
            FIF.MICROPHONE, "Síntesis de voz",
            "Reproducir advertencias por voz",
            configItem=None, parent=self.grp_alerts,
        )
        self.card_tts.setChecked(self.current_settings.get("tts_enabled", True))
        self.card_relay = SwitchSettingCard(
            FIF.BUS, "Relé serial (Arduino)",
            "Bloquear físicamente el área ante infracciones",
            configItem=None, parent=self.grp_alerts,
        )
        self.card_relay.setChecked(
            self.current_settings.get("arduino_relay_enabled", False)
        )
        self.card_port = PortCard(self.current_settings, self.grp_alerts)
        self.card_cd = CooldownSpinCard(self.current_settings, self.grp_alerts)
        self.grp_alerts.addSettingCards(
            [self.card_tts, self.card_cd, self.card_relay, self.card_port]
        )
        self.vBox.addWidget(self.grp_alerts, 0, Qt.AlignTop)

        # ── Botón guardar ──
        self.btn_save = PushSettingCard(
            "Guardar ajustes", FIF.SAVE, "Aplicar cambios",
            "Los ajustes se aplican en caliente al worker de video",
            self.container,
        )
        self.btn_save.clicked.connect(self._save_settings)
        self.vBox.addWidget(self.btn_save, 0, Qt.AlignTop)

        self.vBox.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

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

    def _load_settings(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    self.current_settings = json.load(f)
            except Exception:
                pass

    def _save_settings(self):
        new = {
            "default_camera": self.card_cam.value(),
            "confidence_threshold": self.card_conf.slider.value() / 100.0,
            "grace_period_frames": self.card_grace.value(),
            "tts_enabled": self.card_tts.isChecked(),
            "tts_cooldown_seconds": self.card_cd.value(),
            "arduino_relay_enabled": self.card_relay.isChecked(),
            "arduino_port": self.card_port.value(),
        }
        self.current_settings = new
        try:
            os.makedirs(paths.CONFIG_DIR, exist_ok=True)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(new, f, indent=2)
            InfoBar.success("Ajustes", "Guardados correctamente",
                            parent=self, position=InfoBarPosition.TOP, duration=2500)
            self.settings_changed.emit(new)
        except Exception as e:
            InfoBar.error("Ajustes", f"No se pudo guardar: {e}",
                          parent=self, position=InfoBarPosition.TOP, duration=4000)