"""
Editor de Zonas de Seguridad — layout minimalista.
"""

import os
import json
import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox
)

from src.ui.icons import icon_save, icon_trash, icon_eraser
from src.ui.ui_helpers import set_role, tint_icon

PROFILE_COLORS = {
    "SOLDADURA":   (209, 52, 56),
    "LABORATORIO": (16, 124, 16),
    "GENERAL":     (0, 120, 212),
}


class ZoneCanvas(QLabel):
    """Lienzo interactivo para dibujar polígonos de zonas."""
    point_added = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ZoneCanvas")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 400)
        self.setMouseTracking(True)

        self.background_frame = None
        self.current_points = []
        self.existing_zones = []
        self.selected_zone_name = None

    def set_background_frame(self, frame_bgr):
        self.background_frame = frame_bgr.copy()
        self.update()

    def clear_current_points(self):
        self.current_points = []
        self.update()

    def set_existing_zones(self, zones):
        self.existing_zones = zones
        self.update()

    def set_selected_zone(self, name):
        self.selected_zone_name = name
        self.update()

    def mousePressEvent(self, event):
        if self.background_frame is None:
            return
        if event.button() == Qt.LeftButton:
            img_x, img_y = self._widget_to_image_coords(
                event.position().x(), event.position().y()
            )
            if img_x is not None:
                self.current_points.append([img_x, img_y])
                self.point_added.emit(img_x, img_y)
                self.update()
        elif event.button() == Qt.RightButton:
            if self.current_points:
                self.current_points.pop()
                self.update()

    def _widget_to_image_coords(self, wx, wy):
        if self.background_frame is None:
            return None, None
        img_h, img_w, _ = self.background_frame.shape
        scale = min(self.width() / img_w, self.height() / img_h)
        disp_w, disp_h = int(img_w * scale), int(img_h * scale)
        ox = (self.width() - disp_w) // 2
        oy = (self.height() - disp_h) // 2
        if ox <= wx <= ox + disp_w and oy <= wy <= oy + disp_h:
            ix = max(0, min(img_w - 1, int((wx - ox) / scale)))
            iy = max(0, min(img_h - 1, int((wy - oy) / scale)))
            return ix, iy
        return None, None

    def _image_to_widget_coords(self, ix, iy):
        if self.background_frame is None:
            return ix, iy
        img_h, img_w, _ = self.background_frame.shape
        scale = min(self.width() / img_w, self.height() / img_h)
        disp_w, disp_h = int(img_w * scale), int(img_h * scale)
        ox = (self.width() - disp_w) // 2
        oy = (self.height() - disp_h) // 2
        return int(ix * scale + ox), int(iy * scale + oy)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.background_frame is not None:
            img_h, img_w, ch = self.background_frame.shape
            frame_rgb = cv2.cvtColor(self.background_frame, cv2.COLOR_BGR2RGB)
            qimg = QImage(frame_rgb.data, img_w, img_h, ch * img_w, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            scale = min(self.width() / img_w, self.height() / img_h)
            dw, dh = int(img_w * scale), int(img_h * scale)
            ox = (self.width() - dw) // 2
            oy = (self.height() - dh) // 2
            painter.drawPixmap(ox, oy, dw, dh, pix)
        else:
            painter.setPen(QColor("#8a8a8a"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(
                self.rect(), Qt.AlignCenter,
                "Sin imagen de referencia. Conecta una cámara en Monitoreo."
            )
            return

        # Zonas guardadas
        for zone in self.existing_zones:
            pts = zone.get("poligono", [])
            if len(pts) >= 3:
                qpts = [QPoint(*self._image_to_widget_coords(x, y)) for x, y in pts]
                r, g, b = PROFILE_COLORS.get(zone.get("perfil"), (0, 120, 212))
                selected = zone.get("nombre") == self.selected_zone_name
                painter.setBrush(QBrush(QColor(r, g, b, 70 if selected else 40)))
                painter.setPen(QPen(QColor(r, g, b), 3 if selected else 2, Qt.SolidLine))
                painter.drawPolygon(qpts)
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                tag = f"{zone.get('nombre', '')} [{zone.get('perfil', '')}]"
                painter.drawText(qpts[0].x() + 4, qpts[0].y() - 4, tag)

        # Polígono en construcción
        if self.current_points:
            qpts = [QPoint(*self._image_to_widget_coords(x, y)) for x, y in self.current_points]
            painter.setPen(QPen(QColor("#d13438"), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(209, 52, 56, 30)))
            if len(qpts) >= 3:
                painter.drawPolygon(qpts)
            elif len(qpts) == 2:
                painter.drawLine(qpts[0], qpts[1])
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QBrush(QColor("#d13438")))
            for i, p in enumerate(qpts):
                painter.drawEllipse(p, 4, 4)


class ZoneEditorView(QWidget):
    zones_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_path = "config/zones.json"
        self.rules_path = "config/rules.json"
        self.current_cam = "camara_0"
        self._init_ui()
        self._load_profiles()
        self._load_zones()

    def _init_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(16)

        # Lienzo
        canvas_col = QVBoxLayout()
        canvas_col.setSpacing(8)

        hint = QLabel("Clic izquierdo: punto  |  Clic derecho: deshacer")
        set_role(hint, "caption")

        self.canvas = ZoneCanvas()
        self.canvas.point_added.connect(self._on_point_added)

        foot = QHBoxLayout()
        self.lbl_points = QLabel("Puntos: 0")
        set_role(self.lbl_points, "field")
        btn_clear = QPushButton("Limpiar")
        btn_clear.setIcon(icon_eraser())
        btn_clear.setMaximumWidth(100)
        btn_clear.clicked.connect(self._clear_points)
        foot.addWidget(self.lbl_points)
        foot.addStretch()
        foot.addWidget(btn_clear)

        canvas_col.addWidget(hint)
        canvas_col.addWidget(self.canvas, stretch=1)
        canvas_col.addLayout(foot)
        main.addLayout(canvas_col, stretch=3)

        # Panel lateral
        panel = QFrame()
        panel.setProperty("class", "card")
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(310)
        p = QVBoxLayout(panel)
        p.setContentsMargins(16, 16, 16, 16)
        p.setSpacing(12)

        p.addWidget(set_role(QLabel("Cámara"), "field"))
        self.cam_combo = QComboBox()
        self.cam_combo.addItem("camara_0", "camara_0")
        self.cam_combo.addItem("camara_1", "camara_1")
        self.cam_combo.currentIndexChanged.connect(self._on_cam_changed)
        p.addWidget(self.cam_combo)

        p.addWidget(set_role(QLabel("Zonas guardadas"), "field"))
        self.zone_list = QListWidget()
        self.zone_list.itemClicked.connect(self._on_zone_selected)
        p.addWidget(self.zone_list, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        p.addWidget(sep)

        p.addWidget(set_role(QLabel("Nombre"), "field"))
        self.txt_zone_name = QLineEdit()
        self.txt_zone_name.setPlaceholderText("Ej: Estación Soldadura 1")
        p.addWidget(self.txt_zone_name)

        p.addWidget(set_role(QLabel("Perfil"), "field"))
        self.profile_combo = QComboBox()
        p.addWidget(self.profile_combo)

        btn_save = QPushButton("Guardar zona")
        btn_save.setIcon(tint_icon(icon_save(), "#0078d4"))
        btn_save.setProperty("class", "btn-primary-outline")
        btn_save.clicked.connect(self._save_new_zone)
        p.addWidget(btn_save)

        btn_del = QPushButton("Eliminar seleccionada")
        btn_del.setIcon(icon_trash())
        btn_del.setProperty("class", "btn-danger")
        btn_del.clicked.connect(self._delete_selected_zone)
        p.addWidget(btn_del)

        main.addWidget(panel, stretch=1)

    def set_sample_frame(self, frame_bgr):
        self.canvas.set_background_frame(frame_bgr)

    def _on_point_added(self, x, y):
        self.lbl_points.setText(f"Puntos: {len(self.canvas.current_points)}")

    def _clear_points(self):
        self.canvas.clear_current_points()
        self.lbl_points.setText("Puntos: 0")

    def _load_profiles(self):
        self.profile_combo.clear()
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    for name in json.load(f).keys():
                        self.profile_combo.addItem(name, name)
            except Exception:
                pass
        if self.profile_combo.count() == 0:
            self.profile_combo.addItem("GENERAL", "GENERAL")
            self.profile_combo.addItem("SOLDADURA", "SOLDADURA")

    def _load_zones(self):
        self.zone_list.clear()
        zones = []
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    zones = json.load(f).get(self.current_cam, [])
            except Exception:
                pass
        self.canvas.set_existing_zones(zones)
        for z in zones:
            n = len(z.get("poligono", []))
            item = QListWidgetItem(f"{z.get('nombre')}  ({z.get('perfil')}) — {n} pts")
            item.setData(Qt.UserRole, z)
            self.zone_list.addItem(item)
        self.canvas.set_selected_zone(None)

    def _on_cam_changed(self, index):
        self.current_cam = self.cam_combo.currentData()
        self._load_zones()

    def _on_zone_selected(self, item):
        d = item.data(Qt.UserRole)
        if d:
            self.txt_zone_name.setText(d.get("nombre", ""))
            idx = self.profile_combo.findData(d.get("perfil", ""))
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
            self.canvas.set_selected_zone(d.get("nombre"))

    def _save_new_zone(self):
        name = self.txt_zone_name.text().strip()
        profile = self.profile_combo.currentData()
        points = self.canvas.current_points
        if not name:
            QMessageBox.warning(self, "Atención", "Ingresa un nombre para la zona.")
            return
        if len(points) < 3:
            QMessageBox.warning(self, "Atención", "Se requieren al menos 3 puntos.")
            return

        all_data = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except Exception:
                pass

        if self.current_cam not in all_data:
            all_data[self.current_cam] = []

        all_data[self.current_cam].append({
            "nombre": name, "perfil": profile, "poligono": points
        })

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            self._clear_points()
            self.txt_zone_name.clear()
            self._load_zones()
            self.zones_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete_selected_zone(self):
        item = self.zone_list.currentItem()
        if not item:
            return
        d = item.data(Qt.UserRole)
        if QMessageBox.question(
            self, "Confirmar",
            f"Eliminar zona '{d.get('nombre')}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            all_data = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            if self.current_cam in all_data:
                all_data[self.current_cam] = [
                    z for z in all_data[self.current_cam]
                    if z.get("nombre") != d.get("nombre")
                ]
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, indent=2, ensure_ascii=False)
                self._load_zones()
                self.zones_updated.emit()
