"""
Pantalla de Monitoreo en Tiempo Real — layout minimalista.
Muestra video de cámara/archivo o estado en negro con icono si no está disponible.
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, Slot, Signal, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QListWidget, QListWidgetItem,
    QSizePolicy, QGridLayout, QFileDialog, QStackedWidget
)

from src.ui.icons import (
    icon_pause, icon_play,
    pixmap_check, pixmap_x, pixmap_dot, pixmap_camera_off
)
from src.ui.ui_helpers import StatusChip, set_role, set_state


class VideoLabel(QLabel):
    """Visor de video responsivo que mantiene relación de aspecto o muestra pantalla negra con icono sin cámara."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #0c0d0e; border: 1px solid #e0e0e0;"
            "border-radius: 4px;"
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
        bytes_per_line = ch * w
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
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
        else:
            # Pantalla negra limpia con icono SVG de cámara no disponible
            placeholder = QPixmap(w, h)
            placeholder.fill(QColor("#0d0f12"))
            painter = QPainter(placeholder)
            painter.setRenderHint(QPainter.Antialiasing)

            icon_size = 48
            cam_icon_pixmap = pixmap_camera_off(color="#4b5563", size=icon_size)
            ix = (w - icon_size) // 2
            iy = (h - icon_size) // 2 - 18
            painter.drawPixmap(ix, iy, cam_icon_pixmap)

            # Texto de estado minimalista
            painter.setPen(QColor("#9ca3af"))
            font = QFont("Segoe UI", 11)
            font.setBold(True)
            painter.setFont(font)
            text_rect = QRect(0, iy + icon_size + 14, w, 22)
            painter.drawText(text_rect, Qt.AlignCenter, self._no_camera_message)

            painter.setPen(QColor("#6b7280"))
            sub_font = QFont("Segoe UI", 9)
            painter.setFont(sub_font)
            sub_rect = QRect(0, iy + icon_size + 36, w, 20)
            painter.drawText(sub_rect, Qt.AlignCenter, "Conecte un dispositivo o seleccione otra fuente")

            painter.end()
            self.setPixmap(placeholder)


class MonitorView(QWidget):
    camera_changed = Signal(object, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._current_metadata = {}

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        cam_lbl = QLabel("Fuente")
        set_role(cam_lbl, "field")
        self.cam_combo = QComboBox()
        self.cam_combo.addItem("Cámara 0", 0)
        self.cam_combo.addItem("Cámara 1", 1)
        self.cam_combo.addItem("Cámara 2", 2)
        self.cam_combo.addItem("Archivo de video...", "FILE")
        self.cam_combo.setMaximumWidth(170)
        self.cam_combo.currentIndexChanged.connect(self._on_camera_select)

        self.chip_fps = StatusChip("-- fps", "idle")
        self.chip_signal = StatusChip("Sin señal", "bad")
        self.chip_relay = StatusChip("Relé inactivo", "idle")

        self.btn_pause = QPushButton("Pausar")
        self.btn_pause.setIcon(icon_pause())
        self.btn_pause.setMaximumWidth(110)
        self.btn_pause.clicked.connect(self._toggle_pause)
        self._is_paused = False

        toolbar.addWidget(cam_lbl)
        toolbar.addWidget(self.cam_combo)
        toolbar.addStretch()
        toolbar.addWidget(self.chip_fps)
        toolbar.addWidget(self.chip_signal)
        toolbar.addWidget(self.chip_relay)
        toolbar.addWidget(self.btn_pause)

        main_layout.addLayout(toolbar)

        # ── Content: video + sidebar ──
        content = QHBoxLayout()
        content.setSpacing(16)

        self.video_view = VideoLabel()
        content.addWidget(self.video_view, stretch=3)

        # ── Sidebar panel ──
        panel = QFrame()
        panel.setProperty("class", "card")
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(290)
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(16, 16, 16, 16)
        p_layout.setSpacing(14)

        # Zona
        zone_caption = QLabel("Zona activa")
        set_role(zone_caption, "caption")
        self.zone_name_lbl = QLabel("GENERAL")
        set_role(self.zone_name_lbl, "section")
        p_layout.addWidget(zone_caption)
        p_layout.addWidget(self.zone_name_lbl)

        # Estado
        self.state_icon_lbl = QLabel()
        self.state_icon_lbl.setPixmap(pixmap_dot(size=20))
        self.state_icon_lbl.setFixedSize(20, 20)
        self.state_icon_lbl.setAlignment(Qt.AlignCenter)
        self.state_text_lbl = QLabel("En espera")
        self.state_text_lbl.setStyleSheet(
            "color: #8a8a8a; font-weight: 700; font-size: 14px;"
        )
        state_row = QHBoxLayout()
        state_row.setSpacing(6)
        state_row.addWidget(self.state_icon_lbl)
        state_row.addWidget(self.state_text_lbl)
        state_row.addStretch()
        p_layout.addLayout(state_row)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        p_layout.addWidget(sep)

        # Persona selector
        self.person_combo = QComboBox()
        self.person_combo.setMaximumWidth(200)
        self.person_combo.currentIndexChanged.connect(self._on_person_selected)
        p_layout.addWidget(self.person_combo)

        # EPP checklist
        self.ppe_items = {
            "welding_mask": self._make_ppe_row("Careta"),
            "vest": self._make_ppe_row("Chaleco"),
            "gloves": self._make_ppe_row("Guantes"),
            "helmet": self._make_ppe_row("Casco"),
        }
        for key, (row_widget, _, _) in self.ppe_items.items():
            p_layout.addWidget(row_widget)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        p_layout.addWidget(sep2)

        # Regla
        rule_caption = QLabel("Regla evaluada")
        set_role(rule_caption, "caption")
        self.rule_detail_lbl = QLabel("Sin señal de video")
        self.rule_detail_lbl.setWordWrap(True)
        p_layout.addWidget(rule_caption)
        p_layout.addWidget(self.rule_detail_lbl)

        # Metrics
        metrics = QGridLayout()
        metrics.setSpacing(4)
        lbl_p = QLabel("Personas")
        set_role(lbl_p, "caption")
        self.val_p_count = QLabel("0")
        set_role(self.val_p_count, "value")
        lbl_v = QLabel("Infracciones")
        set_role(lbl_v, "caption")
        self.val_v_count = QLabel("0")
        set_role(self.val_v_count, "value")
        metrics.addWidget(lbl_p, 0, 0)
        metrics.addWidget(self.val_p_count, 1, 0)
        metrics.addWidget(lbl_v, 0, 1)
        metrics.addWidget(self.val_v_count, 1, 1)
        p_layout.addLayout(metrics)

        p_layout.addStretch()
        content.addWidget(panel, stretch=1)
        main_layout.addLayout(content, stretch=1)

        # ── Log strip ──
        log_header = QHBoxLayout()
        log_title = QLabel("Eventos recientes")
        set_role(log_title, "field")
        btn_clear = QPushButton("Limpiar")
        btn_clear.setMaximumWidth(70)
        btn_clear.clicked.connect(self._clear_logs)
        log_header.addWidget(log_title)
        log_header.addStretch()
        log_header.addWidget(btn_clear)
        main_layout.addLayout(log_header)

        self.log_list = QListWidget()
        self.log_list.setMaximumHeight(100)

        log_empty = QWidget()
        le = QVBoxLayout(log_empty)
        empty_lbl = QLabel("Sin eventos recientes")
        set_role(empty_lbl, "muted")
        empty_lbl.setAlignment(Qt.AlignCenter)
        le.addStretch()
        le.addWidget(empty_lbl)
        le.addStretch()

        self.log_stack = QStackedWidget()
        self.log_stack.setMaximumHeight(100)
        self.log_stack.addWidget(self.log_list)
        self.log_stack.addWidget(log_empty)
        self.log_stack.setCurrentIndex(1)
        main_layout.addWidget(self.log_stack)

    def _make_ppe_row(self, label_text):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(pixmap_dot(size=14))
        icon_lbl.setFixedSize(16, 16)
        icon_lbl.setAlignment(Qt.AlignCenter)
        text_lbl = QLabel(label_text)
        status_lbl = QLabel("--")
        status_lbl.setStyleSheet("color: #8a8a8a; font-weight: 600;")
        h.addWidget(icon_lbl)
        h.addWidget(text_lbl)
        h.addStretch()
        h.addWidget(status_lbl)
        return (w, icon_lbl, status_lbl)

    # ── Slots ──

    def _on_camera_select(self, index):
        data = self.cam_combo.currentData()
        if data == "FILE":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar archivo de video", "",
                "Archivos de video (*.mp4 *.avi *.mkv *.mov);;Todos los archivos (*.*)"
            )
            if file_path:
                self.camera_changed.emit(file_path, False)
            else:
                # Volver a índice 0 si canceló
                self.cam_combo.blockSignals(True)
                self.cam_combo.setCurrentIndex(0)
                self.cam_combo.blockSignals(False)
        else:
            self.camera_changed.emit(data, False)

    def _toggle_pause(self):
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.btn_pause.setText("Reanudar")
            self.btn_pause.setIcon(icon_play())
        else:
            self.btn_pause.setText("Pausar")
            self.btn_pause.setIcon(icon_pause())

    def _clear_logs(self):
        self.log_list.clear()
        self.log_stack.setCurrentIndex(1)

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
            self.state_text_lbl.setStyleSheet("color: #8a8a8a; font-weight: 700; font-size: 14px;")
            self.val_p_count.setText("0")
            self.val_v_count.setText("0")
            set_state(self.val_v_count, "idle")
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
            self.state_text_lbl.setStyleSheet("color: #107c10; font-weight: 700; font-size: 14px;")
        else:
            self.state_icon_lbl.setPixmap(pixmap_x(size=20))
            self.state_text_lbl.setText("Incumplimiento")
            self.state_text_lbl.setStyleSheet("color: #d13438; font-weight: 700; font-size: 14px;")

        if relay_blocked:
            self.chip_relay.set_status("Relé bloqueado", "bad")
        else:
            self.chip_relay.set_status("Relé activo", "ok")

        persons = metadata.get("persons", [])
        self.val_p_count.setText(str(len(persons)))
        violations_count = sum(1 for p in persons if not p.get("is_safe", True))
        self.val_v_count.setText(str(violations_count))
        set_state(self.val_v_count, "bad" if violations_count > 0 else "idle")

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
            if (self.log_list.count() == 0
                    or self.log_list.item(self.log_list.count() - 1).text() != log_line):
                item = QListWidgetItem(log_line)
                item.setForeground(QColor("#d13438"))
                self.log_list.addItem(item)
                self.log_list.scrollToBottom()
                self.log_stack.setCurrentIndex(0)

    def _on_person_selected(self, index):
        self._update_person_telemetry()

    def _update_person_telemetry(self):
        p_id = self.person_combo.currentData()
        persons = self._current_metadata.get("persons", [])
        target = next((p for p in persons if p["id"] == p_id), None)

        if not target:
            target = persons[0] if persons else None

        if not target:
            active_z = self._current_metadata.get("active_zone", "GENERAL")
            self.zone_name_lbl.setText(active_z)
            self.rule_detail_lbl.setText("Sin personas detectadas en cuadro.")
            for _, icon_lbl, status_lbl in self.ppe_items.values():
                icon_lbl.setPixmap(pixmap_dot(size=14))
                status_lbl.setText("--")
                status_lbl.setStyleSheet("color: #8a8a8a; font-weight: 600;")
            return

        self.zone_name_lbl.setText(target.get("zone", "GENERAL"))
        present = target.get("present_ppe", [])
        missing = target.get("missing_ppe", [])

        for ppe_key, (_, icon_lbl, status_lbl) in self.ppe_items.items():
            if ppe_key in present:
                icon_lbl.setPixmap(pixmap_check(size=14))
                status_lbl.setText("Detectado")
                status_lbl.setStyleSheet("color: #107c10; font-weight: 600;")
            elif ppe_key in missing:
                icon_lbl.setPixmap(pixmap_x(size=14))
                status_lbl.setText("Faltante")
                status_lbl.setStyleSheet("color: #d13438; font-weight: 600;")
            else:
                icon_lbl.setPixmap(pixmap_dot(size=14))
                status_lbl.setText("N/A")
                status_lbl.setStyleSheet("color: #8a8a8a; font-weight: 600;")

        self.rule_detail_lbl.setText(target.get("rule", "Sin regla activa."))
