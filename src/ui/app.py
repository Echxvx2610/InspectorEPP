"""
Ventana Principal — Guardián EPP.
Sidebar minimalista con iconos SVG + QStackedWidget.
"""

from asyncio import subprocess
import sys
import numpy as np
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame
)

from src.ui.styles import MAIN_STYLESHEET
from src.ui.icons import (
    icon_shield, icon_monitor, icon_map,
    icon_clipboard, icon_history, icon_settings
)
from src.ui.ui_helpers import nav_icon, tint_icon, set_role
from src.ui.video_worker import VideoWorker
from src.ui.monitor import MonitorView
from src.ui.zone_editor import ZoneEditorView
from src.ui.rules_editor import RulesEditorView
from src.ui.events_view import EventsView
from src.ui.settings_view import SettingsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardián EPP — Seguridad Industrial")
        self.resize(1280, 780)
        self.setMinimumSize(1080, 680)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._last_frame = None
        self._init_ui()

        self.video_worker = VideoWorker(
            source=0, parent=self
        )
        self.video_worker.frame_ready.connect(self._on_frame_received)
        self.video_worker.start()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(8, 14, 8, 14)
        sb.setSpacing(4)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 10)
        logo = QLabel()
        logo.setPixmap(tint_icon(icon_shield(), "#0078d4", 22).pixmap(22, 22))
        name = QLabel("Guardián EPP")
        set_role(name, "brand")
        brand.addWidget(logo)
        brand.addWidget(name)
        brand.addStretch()
        sb.addLayout(brand)

        self.nav_buttons = []
        self.btn_monitor = self._nav("Monitoreo", icon_monitor(), 0)
        self.btn_zones = self._nav("Zonas", icon_map(), 1)
        self.btn_rules = self._nav("Reglas", icon_clipboard(), 2)
        self.btn_events = self._nav("Historial", icon_history(), 3)
        self.btn_settings = self._nav("Ajustes", icon_settings(), 4)

        for b in self.nav_buttons:
            sb.addWidget(b)

        sb.addStretch()

        ver = QLabel("v1.0  MVP")
        set_role(ver, "caption")
        sb.addWidget(ver)

        root.addWidget(sidebar)

        # ── Stack ──
        self.stack = QStackedWidget()
        self.view_monitor = MonitorView()
        self.view_zones = ZoneEditorView()
        self.view_rules = RulesEditorView()
        self.view_events = EventsView()
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_monitor)
        self.stack.addWidget(self.view_zones)
        self.stack.addWidget(self.view_rules)
        self.stack.addWidget(self.view_events)
        self.stack.addWidget(self.view_settings)

        root.addWidget(self.stack, stretch=1)

        self.view_monitor.camera_changed.connect(self._on_camera_changed)
        self.view_zones.zones_updated.connect(self._on_zones_updated)
        self.view_rules.rules_updated.connect(self._on_rules_updated)
        self.view_settings.settings_changed.connect(self._on_settings_changed)

        self._switch(0)

    def _nav(self, text, icon, idx):
        btn = QPushButton(text)
        btn.setIcon(nav_icon(icon))
        btn.setIconSize(QSize(18, 18))
        btn.setProperty("class", "nav-btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._switch(idx))
        self.nav_buttons.append(btn)
        return btn

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)
            b.setProperty("active", "true" if i == idx else "false")
            b.style().unpolish(b)
            b.style().polish(b)
        if idx == 1 and self._last_frame is not None:
            self.view_zones.set_sample_frame(self._last_frame)

    @Slot(object, dict)
    def _on_frame_received(self, frame, meta):
        self._last_frame = frame
        if self.stack.currentIndex() == 0:
            self.view_monitor.update_frame(frame, meta)
        for ev in meta.get("events", []):
            self.view_events.add_event(
                ev["ts"], ev["cam"], ev["zone"], ev["person"],
                ev["infraction"], ev["rule"], ev["relay"]
            )

    def _on_camera_changed(self, source, _is_sim=False):
        self.video_worker.set_source(source)

    def _on_settings_changed(self, settings):
        if hasattr(self, "video_worker"):
            self.video_worker.apply_settings(settings)

    def _on_zones_updated(self):
        if hasattr(self, "video_worker"):
            self.video_worker.reload_zones()
        self.view_events.refresh_zones()

    def _on_rules_updated(self):
        if hasattr(self, "video_worker"):
            self.video_worker.reload_rules()
        self.view_zones._load_profiles()

    def closeEvent(self, event):
        if hasattr(self, "video_worker") and self.video_worker.isRunning():
            self.video_worker.stop()
        event.accept()
