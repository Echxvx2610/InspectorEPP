"""
Historial de Eventos — layout minimalista.
"""

import csv
import os
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QStackedWidget
)

from src.ui.icons import icon_download, icon_trash
from src.ui.ui_helpers import set_role

DEMO_DATA = False

STATE_COLOR = {
    "Bloqueado": "#d13438",
    "Advertencia": "#9d5d00",
    "Activo": "#107c10",
}


class EventsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self._init_ui()
        self._load_zones()
        if DEMO_DATA:
            self._load_sample_data()
        self._update_empty_state()

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(10)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filtrar...")
        self.search_box.setMaximumWidth(220)
        self.search_box.textChanged.connect(self._apply_filter)

        self.zone_filter = QComboBox()
        self.zone_filter.addItem("Todas", "ALL")
        self.zone_filter.setMaximumWidth(160)
        self.zone_filter.currentIndexChanged.connect(self._apply_filter)

        btn_export = QPushButton("Exportar CSV")
        btn_export.setIcon(icon_download())
        btn_export.setProperty("class", "btn-primary")
        btn_export.clicked.connect(self._export_to_csv)

        btn_clear = QPushButton("Limpiar")
        btn_clear.setIcon(icon_trash())
        btn_clear.clicked.connect(self._clear_records)

        toolbar.addWidget(self.search_box)
        toolbar.addWidget(self.zone_filter)
        toolbar.addStretch()
        toolbar.addWidget(btn_export)
        toolbar.addWidget(btn_clear)

        main.addLayout(toolbar)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Hora", "Cámara", "Zona", "Persona",
            "Infracción", "Regla", "Relé"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setFocusPolicy(Qt.NoFocus)

        # Estado vacío
        self.empty_page = QWidget()
        ep = QVBoxLayout(self.empty_page)
        empty_lbl = QLabel("Sin registros de infracciones")
        set_role(empty_lbl, "muted")
        empty_lbl.setAlignment(Qt.AlignCenter)
        ep.addStretch()
        ep.addWidget(empty_lbl)
        ep.addStretch()

        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.table)
        self.view_stack.addWidget(self.empty_page)
        main.addWidget(self.view_stack, stretch=1)

    def _load_zones(self):
        self.zone_filter.blockSignals(True)
        self.zone_filter.clear()
        self.zone_filter.addItem("Todas", "ALL")
        if os.path.exists("config/zones.json"):
            try:
                with open("config/zones.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                names = set()
                for cam_zones in data.values():
                    for z in cam_zones:
                        if z.get("nombre"):
                            names.add(z["nombre"])
                for name in sorted(names):
                    self.zone_filter.addItem(name, name)
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
            QTableWidgetItem(ts), QTableWidgetItem(cam),
            QTableWidgetItem(zone), QTableWidgetItem(person),
            QTableWidgetItem(infraction), QTableWidgetItem(rule),
            QTableWidgetItem(relay)
        ]
        color = STATE_COLOR.get(relay)
        if color:
            items[4].setForeground(QColor(color))
            items[6].setForeground(QColor(color))

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

    def _export_to_csv(self):
        if not self.records:
            QMessageBox.information(self, "Aviso", "Sin registros.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar", "reporte_epp.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Hora", "Cámara", "Zona", "Persona", "Infracción", "Regla", "Relé"])
                for r in self.records:
                    w.writerow([
                        r["timestamp"], r["cam"], r["zone"], r["person"],
                        r["infraction"], r["rule"], r["relay"]
                    ])
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _clear_records(self):
        self.records.clear()
        self.table.setRowCount(0)
        self._update_empty_state()
