"""
Editor de Perfiles de EPP — layout minimalista.
"""

import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QCheckBox,
    QLineEdit, QMessageBox, QGridLayout, QInputDialog
)

from src.ui.icons import icon_save, icon_plus, icon_trash
from src.ui.ui_helpers import set_role, tint_icon, Toast


class RulesEditorView(QWidget):
    rules_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules_path = "config/rules.json"
        self.classes_path = "config/classes.json"
        self.rules_data = {}
        self.classes_data = {}
        self.selected_profile = None
        self.toast = Toast(self)

        self._load_classes()
        self._init_ui()
        self._load_rules()

    def _load_classes(self):
        default = {
            "helmet": "Casco de seguridad",
            "vest": "Chaleco reflectante",
            "welding_mask": "Careta de soldadura",
            "glasses": "Lentes de seguridad",
            "gloves": "Guantes de protección",
            "mask": "Cubrebocas",
            "boots": "Botas con casquillo",
        }
        if os.path.exists(self.classes_path):
            try:
                with open(self.classes_path, "r", encoding="utf-8") as f:
                    self.classes_data = json.load(f)
                    self.classes_data.pop("person", None)
            except Exception:
                self.classes_data = default
        else:
            self.classes_data = default

    def _init_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(16)

        # Lista de perfiles
        left = QFrame()
        left.setProperty("class", "card")
        left.setMinimumWidth(220)
        left.setMaximumWidth(260)
        l_layout = QVBoxLayout(left)
        l_layout.setContentsMargins(16, 16, 16, 16)
        l_layout.setSpacing(10)

        l_layout.addWidget(set_role(QLabel("Perfiles de zona"), "section"))

        self.profile_list = QListWidget()
        self.profile_list.itemClicked.connect(self._on_profile_clicked)
        l_layout.addWidget(self.profile_list, stretch=1)

        btns = QHBoxLayout()
        btn_add = QPushButton("Nuevo")
        btn_add.setIcon(icon_plus())
        btn_add.setProperty("class", "btn-primary")
        btn_add.clicked.connect(self._add_profile)
        self.btn_del = QPushButton("Eliminar")
        self.btn_del.setIcon(icon_trash())
        self.btn_del.setProperty("class", "btn-danger")
        self.btn_del.setEnabled(False)
        self.btn_del.clicked.connect(self._del_profile)
        btns.addWidget(btn_add)
        btns.addWidget(self.btn_del)
        l_layout.addLayout(btns)

        main.addWidget(left, stretch=1)

        # Editor
        right = QFrame()
        right.setProperty("class", "card")
        right.setMaximumWidth(760)
        r = QVBoxLayout(right)
        r.setContentsMargins(20, 20, 20, 20)
        r.setSpacing(14)

        self.profile_header = QLabel("Ninguno seleccionado")
        set_role(self.profile_header, "section")
        r.addWidget(self.profile_header)

        r.addWidget(set_role(QLabel("EPP obligatorio"), "field"))

        grid = QGridLayout()
        grid.setSpacing(10)
        self.checkboxes = {}
        row, col = 0, 0
        for key, label in self.classes_data.items():
            cb = QCheckBox(f"{label}")
            self.checkboxes[key] = cb
            grid.addWidget(cb, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        r.addLayout(grid)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        r.addWidget(sep)

        r.addWidget(set_role(QLabel("Mensaje de advertencia"), "field"))
        self.txt_message = QLineEdit()
        self.txt_message.setPlaceholderText(
            "Texto que se mostrará y reproducirá por voz"
        )
        r.addWidget(self.txt_message)

        r.addStretch()

        btn_save = QPushButton("Guardar cambios")
        btn_save.setIcon(tint_icon(icon_save(), "#ffffff"))
        btn_save.setProperty("class", "btn-primary")
        btn_save.clicked.connect(self._save_changes)
        r.addWidget(btn_save)

        main.addWidget(right, stretch=2)

    def _load_rules(self):
        self.profile_list.clear()
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    self.rules_data = json.load(f)
            except Exception:
                self.rules_data = {}

        for name in self.rules_data:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.profile_list.addItem(item)

        if self.profile_list.count() > 0:
            self.profile_list.setCurrentRow(0)
            self._on_profile_clicked(self.profile_list.item(0))
        else:
            self.selected_profile = None
            self.profile_header.setText("Ninguno seleccionado")
            self.btn_del.setEnabled(False)

    def _on_profile_clicked(self, item):
        name = item.data(Qt.UserRole)
        self.selected_profile = name
        self.profile_header.setText(name)
        self.btn_del.setEnabled(True)

        info = self.rules_data.get(name, {})
        reqs = info.get("requeridos", [])
        msg = info.get("mensaje", info.get("mensaje_error", ""))

        for key, cb in self.checkboxes.items():
            cb.setChecked(key in reqs)
        self.txt_message.setText(msg)

    def _add_profile(self):
        name, ok = QInputDialog.getText(
            self, "Nuevo perfil", "Nombre (ej: ALTURAS, PINTURA):"
        )
        if ok and name.strip():
            name = name.strip().upper()
            if name in self.rules_data:
                QMessageBox.warning(self, "Atención", f"'{name}' ya existe.")
                return
            self.rules_data[name] = {
                "requeridos": ["helmet", "vest"],
                "mensaje": f"Se requiere EPP para {name}."
            }
            self._save_to_file()
            self._load_rules()

    def _del_profile(self):
        if not self.selected_profile:
            return
        if QMessageBox.question(
            self, "Confirmar",
            f"Eliminar perfil '{self.selected_profile}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.rules_data.pop(self.selected_profile, None)
            self.selected_profile = None
            self._save_to_file()
            self._load_rules()

    def _save_changes(self):
        if not self.selected_profile:
            return
        selected_ppe = [k for k, cb in self.checkboxes.items() if cb.isChecked()]
        msg = self.txt_message.text().strip()
        self.rules_data[self.selected_profile] = {
            "requeridos": selected_ppe,
            "mensaje": msg,
            "mensaje_error": msg,
        }
        if self._save_to_file():
            self.toast.show_message(
                f"Reglas de '{self.selected_profile}' guardadas"
            )
            self.rules_updated.emit()

    def _save_to_file(self):
        try:
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(self.rules_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return False
