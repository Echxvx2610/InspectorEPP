"""
Pantalla de Monitoreo en Tiempo Real — PyQt-Fluent-Widgets.
CardWidget, ComboBox, PushButton, InfoBadge (chips de estado), BodyLabel/CaptionLabel.
"""

import cv2
from PySide6.QtCore import Qt, Slot, Signal, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QGridLayout, QFileDialog, QStackedWidget
)

from qfluentwidgets import (
    CardWidget, ComboBox, PushButton, PrimaryPushButton, BodyLabel,
    CaptionLabel, SubtitleLabel, StrongBodyLabel, ScrollArea,
    ListWidget, InfoBadge, InfoBadgePosition, FluentIcon as FIF,
    isDarkTheme, Theme
)

from src.ui.icons import (
    pixmap_check, pixmap_x, pixmap_dot, pixmap_camera_off
)


class VideoLabel(QLabel):
    """Visor de video responsivo o pantalla negra con icono si no hay cámara."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #0c0d0e; border-radius: 8px;"
        )
        self.setMinimumSize(480, 320)
        self._current_pixmap = None
        self._no_camera_message = "Cámara no disponible"
        self._update_display()

    def set_frame(self, frame_bgr):
        if frame_bgr is None:
            self._current_pixmap = None
            self._update_display()
            return
        h, w, ch = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(qimg)
        self._update_display()

    def set_no_camera(self, message="Cámara no disponible"):
        self._no_camera_message = message
        self._current_pixmap = None
        self._update_display()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def _update_display(self):
        w = max(self.width(), 480)
        h = max(self.height(), 320)

        if self._current_pixmap and not self._current_pixmap.isNull():
            scaled = self._current_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)
            return

        placeholder = QPixmap(w, h)
        placeholder.fill(QColor("#0d0f12"))
        painter = QPainter(placeholder)
        painter.setRenderHint(QPainter.Antialiasing)

        icon_size = 48
        cam_pixmap = pixmap_camera_off(color="#4b5563", size=icon_size)
        ix = (w - icon_size) // 2
        iy = (h - icon_size) // 2 - 18
        painter.drawPixmap(ix, iy, cam_pixmap)

        painter.setPen(QColor("#9ca3af"))
        font = QFont("Segoe UI", 11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(0, iy + icon_size + 14, w, 22),
                         Qt.AlignCenter, self._no_camera_message)

        painter.setPen(QColor("#6b7280"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRect(0, iy + icon_size + 36, w, 20),
                         Qt.AlignCenter,
                         "Conecte un dispositivo o seleccione otra fuente")
        painter.end()
        self.setPixmap(placeholder)


class StatusBadge(QWidget):
    """Equivalente Fluent del StatusChip: [● texto] usando InfoBadge."""

    _STYLE = {
        "idle": ("#9a9a9a", "#f5f5f5"),
        "ok":   ("#107c10", "#f1faf1"),
        "warn": ("#f7630c", "#fff8e5"),
        "bad":  ("#d13438", "#fdf3f4"),
    }

    def __init__(self, text="", state="idle", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 5, 14, 5)
        lay.setSpacing(8)

        fg, bg = self._STYLE.get(state, self._STYLE["idle"])
        self.badge = InfoBadge.error(text) if state == "bad" else (
            InfoBadge.success(text) if state == "ok" else (
                InfoBadge.warning(text) if state == "warn" else InfoBadge.info(text)
            )
        )
        lay.addWidget(self.badge)

    def set_status(self, text, state):
        fg, bg = self._STYLE.get(state, self._STYLE["idle"])
        lay = self.layout()
        lay.removeWidget(self.badge)
        self.badge.deleteLater()
        if state == "bad":
            self.badge = InfoBadge.error(text)
        elif state == "ok":
            self.badge = InfoBadge.success(text)
        elif state == "warn":
            self.badge = InfoBadge.warning(text)
        else:
            self.badge = InfoBadge.info(text)
        lay.addWidget(self.badge)


class MonitorView(ScrollArea):
    camera_changed = Signal(object, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("monitorView")
        self.setWidgetResizable(True)
        self._current_metadata = {}

        container = QWidget()
        self.vBoxLayout = QVBoxLayout(container)
        self.vBoxLayout.setContentsMargins(24, 16, 24, 16)
        self.vBoxLayout.setSpacing(12)
        self.setWidget(container)
        self._init_ui()

    def _init_ui(self):
        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        toolbar.addWidget(BodyLabel("Fuente"))
        self.cam_combo = ComboBox()
        self.cam_combo.addItems(["Cámara 0", "Cámara 1", "Cámara 2", "Archivo de video..."])
        self.cam_combo.setItemData(0, 0); self.cam_combo.setItemData(1, 1)
        self.cam_combo.setItemData(2, 2); self.cam_combo.setItemData(3, "FILE")
        self.cam_combo.setCurrentIndex(0)
        self.cam_combo.setMinimumWidth(170)
        self.cam_combo.currentIndexChanged.connect(self._on_camera_select)

        self.chip_fps = StatusBadge("-- fps", "idle")
        self.chip_signal = StatusBadge("Sin señal", "bad")
        self.chip_relay = StatusBadge("Relé inactivo", "idle")

        self.btn_pause = PushButton(FIF.PAUSE, "Pausar")
        self.btn_pause.setMinimumWidth(110)
        self.btn_pause.clicked.connect(self._toggle_pause)
        self._is_paused = False

        toolbar.addWidget(self.cam_combo)
        toolbar.addStretch()
        toolbar.addWidget(self.chip_fps)
        toolbar.addWidget(self.chip_signal)
        toolbar.addWidget(self.chip_relay)
        toolbar.addWidget(self.btn_pause)
        self.vBoxLayout.addLayout(toolbar)

        # ── Video + panel lateral ──
        content = QHBoxLayout()
        content.setSpacing(16)

        self.video_view = VideoLabel()
        content.addWidget(self.video_view, stretch=3)

        panel = CardWidget()
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(300)
        p = QVBoxLayout(panel)
        p.setContentsMargins(18, 18, 18, 18)
        p.setSpacing(12)

        p.addWidget(CaptionLabel("Zona activa"))
        self.zone_name_lbl = SubtitleLabel("GENERAL")
        p.addWidget(self.zone_name_lbl)

        # Estado
        self.state_icon_lbl = QLabel()
        self.state_icon_lbl.setPixmap(pixmap_dot(size=20))
        self.state_icon_lbl.setFixedSize(20, 20)
        self.state_icon_lbl.setAlignment(Qt.AlignCenter)
        self.state_text_lbl = StrongBodyLabel("En espera")
        state_row = QHBoxLayout()
        state_row.setSpacing(6)
        state_row.addWidget(self.state_icon_lbl)
        state_row.addWidget(self.state_text_lbl)
        state_row.addStretch()
        p.addLayout(state_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        p.addWidget(sep)

        # Selector de persona
        self.person_combo = ComboBox()
        self.person_combo.setMinimumWidth(200)
        self.person_combo.currentIndexChanged.connect(self._on_person_selected)
        p.addWidget(self.person_combo)

        # Checklist EPP
        self.ppe_items = {
            "welding_mask": self._make_ppe_row("Careta"),
            "vest": self._make_ppe_row("Chaleco"),
            "gloves": self._make_ppe_row("Guantes"),
            "helmet": self._make_ppe_row("Casco"),
        }
        for row_widget, _, _ in self.ppe_items.values():
            p.addWidget(row_widget)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        p.addWidget(sep2)

        p.addWidget(CaptionLabel("Regla evaluada"))
        self.rule_detail_lbl = BodyLabel("Sin señal de video")
        self.rule_detail_lbl.setWordWrap(True)
        p.addWidget(self.rule_detail_lbl)

        metrics = QGridLayout()
        metrics.setSpacing(4)
        metrics.addWidget(CaptionLabel("Personas"), 0, 0)
        self.val_p_count = SubtitleLabel("0")
        metrics.addWidget(self.val_p_count, 1, 0)
        metrics.addWidget(CaptionLabel("Infracciones"), 0, 1)
        self.val_v_count = SubtitleLabel("0")
        metrics.addWidget(self.val_v_count, 1, 1)
        p.addLayout(metrics)

        p.addStretch()
        content.addWidget(panel, stretch=1)
        self.vBoxLayout.addLayout(content, stretch=1)

        # ── Log de eventos recientes ──
        log_header = QHBoxLayout()
        log_header.addWidget(BodyLabel("Eventos recientes"))
        log_header.addStretch()
        btn_clear = PushButton("Limpiar")
        btn_clear.setMinimumWidth(80)
        btn_clear.clicked.connect(self._clear_logs)
        log_header.addWidget(btn_clear)
        self.vBoxLayout.addLayout(log_header)

        self.log_list = ListWidget()
        self.log_list.setMinimumHeight(100)
        self.vBoxLayout.addWidget(self.log_list)

    def _make_ppe_row(self, label_text):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(pixmap_dot(size=14))
        icon_lbl.setFixedSize(16, 16)
        icon_lbl.setAlignment(Qt.AlignCenter)
        text_lbl = BodyLabel(label_text)
        status_lbl = BodyLabel("--")
        h.addWidget(icon_lbl)
        h.addWidget(text_lbl)
        h.addStretch()
        h.addWidget(status_lbl)
        return (w, icon_lbl, status_lbl)

    # ── Slots ──

    def _on_camera_select(self, index):
        data = self.cam_combo.itemData(index)
        if data == "FILE":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar archivo de video", "",
                "Archivos de video (*.mp4 *.avi *.mkv *.mov);;Todos los archivos (*.*)"
            )
            if file_path:
                self.camera_changed.emit(file_path, False)
            else:
                self.cam_combo.blockSignals(True)
                self.cam_combo.setCurrentIndex(0)
                self.cam_combo.blockSignals(False)
        else:
            self.camera_changed.emit(data, False)

    def set_source_index(self, source):
        """Sincroniza el combo con un source externo (p. ej. el editor de
        zonas) sin re-emitir camera_changed."""
        idx = self.cam_combo.findData(int(source) if isinstance(source, str) and source.isdigit() else source)
        if idx is not None and idx >= 0:
            self.cam_combo.blockSignals(True)
            self.cam_combo.setCurrentIndex(idx)
            self.cam_combo.blockSignals(False)

    def _toggle_pause(self):
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.btn_pause.setText("Reanudar")
            self.btn_pause.setIcon(FIF.PLAY)
        else:
            self.btn_pause.setText("Pausar")
            self.btn_pause.setIcon(FIF.PAUSE)

    def _clear_logs(self):
        self.log_list.clear()

    @Slot(object, dict)
    def update_frame(self, frame, metadata):
        self._current_metadata = metadata
        camera_available = metadata.get("camera_available", True)

        if not camera_available or frame is None:
            status_text = metadata.get("status", "Cámara no disponible")
            self.video_view.set_no_camera(status_text)
            self.chip_fps.set_status("-- fps", "idle")
            self.chip_signal.set_status("Sin señal", "bad")
            self.chip_relay.set_status("Relé inactivo", "idle")
            self.state_icon_lbl.setPixmap(pixmap_dot(size=20))
            self.state_text_lbl.setText("Sin señal")
            self.state_icon_lbl.setStyleSheet("color: #8a8a8a;")
            self.val_p_count.setText("0")
            self.val_v_count.setText("0")
            self.rule_detail_lbl.setText("Cámara no detectada o desconectada.")
            return

        self.video_view.set_frame(frame)

        fps = metadata.get("fps", 0.0)
        self.chip_fps.set_status(f"{fps:.0f} fps", "ok")
        self.chip_signal.set_status("Transmisión activa", "ok")

        global_safe = metadata.get("global_safe", True)
        relay_blocked = metadata.get("relay_blocked", False)

        if global_safe:
            self.state_icon_lbl.setPixmap(pixmap_check(size=20))
            self.state_text_lbl.setText("Conforme")
        else:
            self.state_icon_lbl.setPixmap(pixmap_x(size=20))
            self.state_text_lbl.setText("Incumplimiento")

        if relay_blocked:
            self.chip_relay.set_status("Relé bloqueado", "bad")
        else:
            self.chip_relay.set_status("Relé activo", "ok")

        persons = metadata.get("persons", [])
        self.val_p_count.setText(str(len(persons)))
        violations = sum(1 for p in persons if not p.get("is_safe", True))
        self.val_v_count.setText(str(violations))

        current_ids = [p["id"] for p in persons]
        combo_ids = [self.person_combo.itemData(i) for i in range(self.person_combo.count())]
        if current_ids != combo_ids:
            self.person_combo.blockSignals(True)
            prev = self.person_combo.currentData()
            self.person_combo.clear()
            for p in persons:
                self.person_combo.addItem(
                    f"Persona #{p['id']}  ({p.get('zone', '')})", p["id"]
                )
            idx = self.person_combo.findData(prev)
            if idx >= 0:
                self.person_combo.setCurrentIndex(idx)
            self.person_combo.blockSignals(False)

        self._update_person_telemetry()

        for alert_txt in metadata.get("alerts", []):
            ts = metadata.get("timestamp", "")
            log_line = f"{ts}   {alert_txt}"
            items = self.log_list.items
            if not items or items[-1].text() != log_line:
                self.log_list.addItem(log_line)
                self.log_list.scrollToBottom()

    def _on_person_selected(self, index):
        self._update_person_telemetry()

    def _update_person_telemetry(self):
        p_id = self.person_combo.currentData()
        persons = self._current_metadata.get("persons", [])
        target = next((p for p in persons if p["id"] == p_id), None)
        target = target or (persons[0] if persons else None)

        if not target:
            active_z = self._current_metadata.get("active_zone", "GENERAL")
            self.zone_name_lbl.setText(active_z)
            self.rule_detail_lbl.setText("Sin personas detectadas en cuadro.")
            for _, icon_lbl, status_lbl in self.ppe_items.values():
                icon_lbl.setPixmap(pixmap_dot(size=14))
                status_lbl.setText("--")
            return

        self.zone_name_lbl.setText(target.get("zone", "GENERAL"))
        present = target.get("present_ppe", [])
        missing = target.get("missing_ppe", [])

        for ppe_key, (_, icon_lbl, status_lbl) in self.ppe_items.items():
            if ppe_key in present:
                icon_lbl.setPixmap(pixmap_check(size=14))
                status_lbl.setText("Detectado")
            elif ppe_key in missing:
                icon_lbl.setPixmap(pixmap_x(size=14))
                status_lbl.setText("Faltante")
            else:
                icon_lbl.setPixmap(pixmap_dot(size=14))
                status_lbl.setText("N/A")

        self.rule_detail_lbl.setText(target.get("rule", "Sin regla activa."))