"""
Editor de Zonas de Seguridad — PyQt-Fluent-Widgets.
El lienzo interactivo (ZoneCanvas) se conserva igual; los paneles migran a
CardWidget, ComboBox, LineEdit, botones Fluent y MessageBox de qfluentwidgets.
"""

import os
import json
import time
import cv2
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QListWidgetItem
)

from qfluentwidgets import (
    CardWidget, ComboBox, LineEdit, ListWidget,
    PrimaryPushButton, PushButton, BodyLabel, CaptionLabel, FluentIcon as FIF,
    MessageBox, ScrollArea, isDarkTheme
)

PROFILE_COLORS = {
    "SOLDADURA":   (209, 52, 56),
    "LABORATORIO": (16, 124, 16),
    "GENERAL":     (0, 120, 212),
}


class ZoneCanvas(QLabel):
    """Lienzo interactivo para dibujar polígonos de zonas (sin cambios)."""
    point_added = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ZoneCanvas")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 400)
        self.setMouseTracking(True)
        self.setStyleSheet(
            "background-color: #0f1014; border-radius: 8px;"
        )

        self.background_frame = None
        self.background_pixmap = None
        self.current_points = []
        self.existing_zones = []
        self.selected_zone_name = None

    def set_background_frame(self, frame_bgr):
        """Recibe un frame BGR de OpenCV y lo convierte una sola vez."""
        self.background_frame = frame_bgr.copy()
        img_h, img_w, ch = self.background_frame.shape
        frame_rgb = cv2.cvtColor(self.background_frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(frame_rgb.data, img_w, img_h, ch * img_w, QImage.Format_RGB888)
        # .copy() para desacoplar de la vida útil del buffer numpy
        self.background_pixmap = QPixmap.fromImage(qimg.copy())
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

        if self.background_pixmap is not None:
            img_h, img_w, _ = self.background_frame.shape
            scale = min(self.width() / img_w, self.height() / img_h)
            dw, dh = int(img_w * scale), int(img_h * scale)
            ox = (self.width() - dw) // 2
            oy = (self.height() - dh) // 2
            painter.drawPixmap(ox, oy, dw, dh, self.background_pixmap)
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
            for p in qpts:
                painter.drawEllipse(p, 4, 4)


class ZoneEditorView(ScrollArea):
    zones_updated = Signal()
    # Emitida cuando el usuario cambia la cámara a editar ("camara_0", ...);
    # la ventana la conecta para apuntar el worker a esa fuente de video.
    camera_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("zonesView")
        self.setWidgetResizable(True)

        self.config_path = "config/zones.json"
        self.rules_path = "config/rules.json"
        self.current_cam = "camara_0"
        self._frozen = False          # imagen congelada para trazar cómodo
        self._last_bg_ts = 0.0        # throttle del refresco de fondo

        self.container = QWidget()
        self.main = QHBoxLayout(self.container)
        self.main.setContentsMargins(24, 16, 24, 16)
        self.main.setSpacing(16)
        self.setWidget(self.container)

        self._init_ui()
        self._load_profiles()
        self._load_zones()

    def _init_ui(self):
        # Lienzo
        canvas_col = QVBoxLayout()
        canvas_col.setSpacing(8)

        hint = CaptionLabel("Clic izquierdo: punto   |   Clic derecho: deshacer")
        canvas_col.addWidget(hint)

        self.canvas = ZoneCanvas()
        self.canvas.point_added.connect(self._on_point_added)
        canvas_col.addWidget(self.canvas, stretch=1)

        foot = QHBoxLayout()
        self.lbl_points = BodyLabel("Puntos: 0")
        btn_clear = PushButton(FIF.BROOM, "Limpiar")
        btn_clear.setMinimumWidth(100)
        btn_clear.clicked.connect(self._clear_points)
        foot.addWidget(self.lbl_points)
        foot.addStretch()
        foot.addWidget(btn_clear)
        self.btn_freeze = PushButton(FIF.PAUSE, "Congelar imagen")
        self.btn_freeze.setMinimumWidth(120)
        self.btn_freeze.clicked.connect(self._toggle_freeze)
        foot.addWidget(self.btn_freeze)
        canvas_col.addLayout(foot)

        self.main.addLayout(canvas_col, stretch=3)

        # Panel lateral
        panel = CardWidget()
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(310)
        p = QVBoxLayout(panel)
        p.setContentsMargins(16, 16, 16, 16)
        p.setSpacing(12)

        p.addWidget(BodyLabel("Cámara"))
        self.cam_combo = ComboBox(panel)
        self.cam_combo.addItem("camara_0", userData="camara_0")
        self.cam_combo.addItem("camara_1", userData="camara_1")
        self.cam_combo.currentIndexChanged.connect(self._on_cam_changed)
        p.addWidget(self.cam_combo)

        p.addWidget(BodyLabel("Zonas guardadas"))
        self.zone_list = ListWidget(panel)
        self.zone_list.itemClicked.connect(self._on_zone_selected)
        p.addWidget(self.zone_list, stretch=1)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        p.addWidget(sep)

        p.addWidget(BodyLabel("Nombre"))
        self.txt_zone_name = LineEdit(panel)
        self.txt_zone_name.setPlaceholderText("Ej: Estación Soldadura 1")
        p.addWidget(self.txt_zone_name)

        p.addWidget(BodyLabel("Perfil"))
        self.profile_combo = ComboBox(panel)
        p.addWidget(self.profile_combo)

        btn_save = PrimaryPushButton(FIF.SAVE, "Guardar zona")
        btn_save.clicked.connect(self._save_new_zone)
        p.addWidget(btn_save)

        btn_del = PushButton(FIF.DELETE, "Eliminar seleccionada")
        btn_del.clicked.connect(self._delete_selected_zone)
        p.addWidget(btn_del)

        self.main.addWidget(panel, stretch=1)

    # ── Interacción lienzo ──

    def set_sample_frame(self, frame_bgr):
        """
        Recibe frames en vivo del worker (llamado por MainWindow).
        - Throttle a ~5 Hz para no repintar el lienzo a 30 fps.
        - Si la imagen está congelada (trazado en curso), solo se
          almacena el último frame; se aplicará al reanudar.
        """
        if frame_bgr is None:
            return
        now = time.time()
        if self._frozen:
            return
        if now - self._last_bg_ts < 0.2:
            return
        self._last_bg_ts = now
        self.canvas.set_background_frame(frame_bgr)

    def _toggle_freeze(self):
        """Congela el fondo actual para trazar, o reanuda el vivo."""
        self._frozen = not self._frozen
        if self._frozen:
            self.btn_freeze.setText("Reanudar imagen")
            self.btn_freeze.setIcon(FIF.SYNC)
        else:
            self.btn_freeze.setText("Congelar imagen")
            self.btn_freeze.setIcon(FIF.PAUSE)
            self._last_bg_ts = 0.0  # refrescar de inmediato

    def _on_point_added(self, x, y):
        self.lbl_points.setText(f"Puntos: {len(self.canvas.current_points)}")

    def _clear_points(self):
        self.canvas.clear_current_points()
        self.lbl_points.setText("Puntos: 0")

    # ── Datos ──

    def _load_profiles(self):
        self.profile_combo.clear()
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    for name in json.load(f).keys():
                        self.profile_combo.addItem(name, userData=name)
            except Exception:
                pass
        if self.profile_combo.count() == 0:
            self.profile_combo.addItem("GENERAL", userData="GENERAL")
            self.profile_combo.addItem("SOLDADURA", userData="SOLDADURA")

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
            item = QListWidgetItem(
                f"{z.get('nombre')}  ({z.get('perfil')}) — {n} pts"
            )
            item.setData(Qt.UserRole, z)
            self.zone_list.addItem(item)
        self.canvas.set_selected_zone(None)

    def _on_cam_changed(self, index):
        self.current_cam = self.cam_combo.currentData()
        # Avisar a MainWindow para apuntar el worker a la cámara editada
        # (el fondo del lienzo debe corresponder a estas zonas).
        self.camera_selected.emit(self.current_cam)
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
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning("Atención", "Ingresa un nombre para la zona.",
                            parent=self, position=InfoBarPosition.TOP, duration=2500)
            return
        if len(points) < 3:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning("Atención", "Se requieren al menos 3 puntos.",
                            parent=self, position=InfoBarPosition.TOP, duration=2500)
            return

        all_data = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except Exception:
                pass

        all_data.setdefault(self.current_cam, []).append({
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
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error("Error", str(e),
                          parent=self, position=InfoBarPosition.TOP, duration=4000)

    def _delete_selected_zone(self):
        item = self.zone_list.currentItem()
        if not item:
            return
        d = item.data(Qt.UserRole)
        dlg = MessageBox(
            "Confirmar", f"Eliminar zona '{d.get('nombre')}'?", self.window()
        )
        if dlg.exec():
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