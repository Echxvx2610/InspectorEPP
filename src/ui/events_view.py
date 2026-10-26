"""
Historial de Eventos — PyQt-Fluent-Widgets.
TableWidget (Fluent), SearchLineEdit, ComboBox, PrimaryPushButton, InfoBar.
"""

import csv
import os
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QHeaderView, QTableWidgetItem, QAbstractItemView
)

from qfluentwidgets import (
    CardWidget, TableWidget, SearchLineEdit, ComboBox, PrimaryPushButton,
    PushButton, BodyLabel, CaptionLabel, FluentIcon as FIF, InfoBar,
    InfoBarPosition, isDarkTheme
)

from src import paths

DEMO_DATA = False

STATE_COLOR = {
    "Bloqueado": "#d13438",
    "Advertencia": "#9d5d00",
    "Activo": "#107c10",
}

HEADERS = ["Hora", "Cámara", "Zona", "Persona", "Infracción", "Regla", "Relé"]


class EventsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("eventsView")
        self.records = []
        self._init_ui()
        self._load_zones()
        if DEMO_DATA:
            self._load_sample_data()
        self._update_empty_state()

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 16, 24, 16)
        main.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("Filtrar...")
        self.search_box.setFixedWidth(240)
        self.search_box.textChanged.connect(self._apply_filter)

        self.zone_filter = ComboBox()
        self.zone_filter.addItem("Todas", userData="ALL")
        self.zone_filter.setMinimumWidth(160)
        self.zone_filter.currentIndexChanged.connect(self._apply_filter)

        btn_export = PrimaryPushButton(FIF.DOWNLOAD, "Exportar CSV")
        btn_export.clicked.connect(self._export_to_csv)

        btn_clear = PushButton(FIF.DELETE, "Limpiar")
        btn_clear.clicked.connect(self._clear_records)

        toolbar.addWidget(self.search_box)
        toolbar.addWidget(self.zone_filter)
        toolbar.addStretch()
        toolbar.addWidget(btn_export)
        toolbar.addWidget(btn_clear)
        main.addLayout(toolbar)

        # Tabla Fluent
        self.table = TableWidget(self)
        self.table.setBorderVisible(True)
        self.table.setWordWrap(False)
        self.table.setCornerButtonEnabled(False)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(HEADERS)
        # Header grande estilo Win11, primera/última columnas auto-ajustadas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setBorderVisible(True)

        # Estado vacío
        self.empty_page = QWidget()
        ep = QVBoxLayout(self.empty_page)
        empty_lbl = BodyLabel("Sin registros de infracciones")
        empty_lbl.setStyleSheet("color: #8a8a8a;")
        empty_lbl.setAlignment(Qt.AlignCenter)
        ep.addStretch()
        ep.addWidget(empty_lbl)
        ep.addStretch()

        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.table)
        self.view_stack.addWidget(self.empty_page)
        main.addWidget(self.view_stack, stretch=1)

    # ── Zonas ──

    def _load_zones(self):
        self.zone_filter.blockSignals(True)
        self.zone_filter.clear()
        self.zone_filter.addItem("Todas", userData="ALL")
        if os.path.exists(paths.ZONES_PATH):
            try:
                with open(paths.ZONES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                names = set()
                for cam_zones in data.values():
                    for z in cam_zones:
                        if z.get("nombre"):
                            names.add(z["nombre"])
                for name in sorted(names):
                    self.zone_filter.addItem(name, userData=name)
            except Exception:
                pass
        self.zone_filter.blockSignals(False)

    def refresh_zones(self):
        self._load_zones()

    def _load_sample_data(self):
        samples = [
            ("14:30:12", "camara_0", "SOLDADURA", "#1", "Conforme", "R0", "Activo"),
            ("14:32:05", "camara_0", "SOLDADURA", "#3", "Falta chaleco", "R2", "Bloqueado"),
            ("14:33:40", "camara_0", "GENERAL", "#7", "Conforme", "R0", "Activo"),
            ("14:35:18", "camara_0", "SOLDADURA", "#3", "Falta careta y chaleco", "R1, R2", "Bloqueado"),
            ("14:36:50", "camara_0", "LABORATORIO", "#2", "Falta mascarilla", "R1", "Advertencia"),
        ]
        for s in samples:
            self.add_event(*s)

    # ── Registros ──

    def add_event(self, ts, cam, zone, person, infraction, rule, relay):
        record = {
            "timestamp": ts, "cam": cam, "zone": zone,
            "person": person, "infraction": infraction,
            "rule": rule, "relay": relay
        }
        self.records.append(record)
        row = self.table.rowCount()
        self.table.insertRow(row)
        items = [
            self.table._make_item(ts), self.table._make_item(cam),
            self.table._make_item(zone), self.table._make_item(person),
            self.table._make_item(infraction), self.table._make_item(rule),
            self.table._make_item(relay)
        ]
        color = STATE_COLOR.get(relay)
        if color:
            brush = QBrush(QColor(color))
            items[4].setForeground(brush)
            items[6].setForeground(brush)

        for col, itm in enumerate(items):
            self.table.setItem(row, col, itm)

        self._update_empty_state()

    def _apply_filter(self):
        q = self.search_box.text().lower()
        zone_sel = self.zone_filter.currentData()

        for row in range(self.table.rowCount()):
            zone_text = self.table.item(row, 2).text()
            ok_zone = zone_sel == "ALL" or zone_text == zone_sel
            row_text = " ".join(
                self.table.item(row, c).text().lower()
                for c in range(self.table.columnCount())
            )
            ok_query = q in row_text if q else True
            self.table.setRowHidden(row, not (ok_zone and ok_query))

        self._update_empty_state()

    def _update_empty_state(self):
        any_visible = any(
            not self.table.isRowHidden(r)
            for r in range(self.table.rowCount())
        )
        self.view_stack.setCurrentIndex(0 if any_visible else 1)

    # ── Exportar / limpiar ──

    def _export_to_csv(self):
        if not self.records:
            InfoBar.info("Aviso", "Sin registros.",
                         parent=self, position=InfoBarPosition.TOP, duration=2500)
            return
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar", "reporte_epp.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(HEADERS)
                for r in self.records:
                    w.writerow([r["timestamp"], r["cam"], r["zone"], r["person"],
                                r["infraction"], r["rule"], r["relay"]])
            InfoBar.success("Exportado", f"Guardado en:\n{path}",
                            parent=self, position=InfoBarPosition.TOP, duration=3000)
        except Exception as e:
            InfoBar.error("Error", str(e),
                          parent=self, position=InfoBarPosition.TOP, duration=4000)

    def _clear_records(self):
        self.records.clear()
        self.table.setRowCount(0)
        self._update_empty_state()