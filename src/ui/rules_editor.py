"""
Editor de Perfiles de EPP — PyQt-Fluent-Widgets.
ListWidget Fluent + CardWidget con checkboxes, InfoBar y MessageBox de qfluentwidgets.
"""

import os
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QCheckBox, QListWidgetItem
)

from src import paths
from qfluentwidgets import (
    CardWidget, ListWidget, PrimaryPushButton, PushButton,
    BodyLabel, CaptionLabel, SubtitleLabel, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, MessageBox, MessageBoxBase,
    ScrollArea, isDarkTheme
)

DEFAULT_CLASSES = {
    "helmet": "Casco de seguridad",
    "vest": "Chaleco reflectante",
    "welding_mask": "Careta de soldadura",
    "glasses": "Lentes de seguridad",
    "gloves": "Guantes de protección",
    "mask": "Cubrebocas",
    "boots": "Botas con casquillo",
}


class NameDialog(MessageBoxBase):
    """Diálogo Fluent para pedir el nombre de un nuevo perfil."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Nuevo perfil")
        self.edit = LineEdit(self)
        self.edit.setPlaceholderText("Nombre (ej: ALTURAS, PINTURA)")
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.edit)
        self.yesButton.setText("Crear")
        self.cancelButton.setText("Cancelar")
        self.widget.setMinimumWidth(420)

    def name(self):
        return self.edit.text().strip().upper()


class RulesEditorView(ScrollArea):
    rules_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rulesView")
        self.setWidgetResizable(True)

        self.rules_path = str(paths.RULES_PATH)
        self.classes_path = str(paths.CLASSES_PATH)
        # Para el renombrado: las zonas referencian perfil por NOMBRE;
        # renombrar un perfil debe actualizarlas a la vez (ver _apply_rename)
        self.zones_path = str(paths.ZONES_PATH)
        self.rules_data = {}
        self.classes_data = {}
        self.selected_profile = None

        self._load_classes()

        self.container = QWidget()
        self.main = QHBoxLayout(self.container)
        self.main.setContentsMargins(24, 16, 24, 16)
        self.main.setSpacing(16)
        self.setWidget(self.container)
        self._init_ui()
        self._load_rules()

    def _load_classes(self):
        if os.path.exists(self.classes_path):
            try:
                with open(self.classes_path, "r", encoding="utf-8") as f:
                    self.classes_data = json.load(f)
                    self.classes_data.pop("person", None)
            except Exception:
                self.classes_data = dict(DEFAULT_CLASSES)
        else:
            self.classes_data = dict(DEFAULT_CLASSES)

    def _init_ui(self):
        # ── Lista de perfiles ──
        left = CardWidget()
        left.setMinimumWidth(240)
        left.setMaximumWidth(280)
        l = QVBoxLayout(left)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(12)

        l.addWidget(SubtitleLabel("Perfiles de zona"))

        self.profile_list = ListWidget(left)
        self.profile_list.itemClicked.connect(self._on_profile_clicked)
        l.addWidget(self.profile_list, stretch=1)

        btns = QGridLayout()
        btns.setSpacing(8)
        btn_add = PrimaryPushButton(FIF.ADD, "Nuevo")
        btn_add.clicked.connect(self._add_profile)
        btn_rename = PushButton(FIF.EDIT, "Renombrar")
        btn_rename.clicked.connect(self._rename_profile)
        self.btn_del = PushButton(FIF.DELETE, "Eliminar")
        self.btn_del.setEnabled(False)
        self.btn_del.clicked.connect(self._del_profile)
        btns.addWidget(btn_add, 0, 0)
        btns.addWidget(btn_rename, 0, 1)
        btns.addWidget(self.btn_del, 1, 0, 1, 2)
        l.addLayout(btns)

        self.main.addWidget(left, stretch=1)

        # ── Editor ──
        right = CardWidget()
        right.setMaximumWidth(760)
        r = QVBoxLayout(right)
        r.setContentsMargins(20, 20, 20, 20)
        r.setSpacing(14)

        self.profile_header = SubtitleLabel("Ninguno seleccionado")
        r.addWidget(self.profile_header)

        r.addWidget(BodyLabel("EPP obligatorio"))

        grid = QGridLayout()
        grid.setSpacing(10)
        self.checkboxes = {}
        row, col = 0, 0
        for key, label in self.classes_data.items():
            cb = QCheckBox(label)
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

        r.addWidget(BodyLabel("Mensaje de advertencia"))
        self.txt_message = LineEdit(right)
        self.txt_message.setPlaceholderText(
            "Texto que se mostrará y reproducirá por voz"
        )
        r.addWidget(self.txt_message)

        r.addStretch()

        btn_save = PrimaryPushButton(FIF.SAVE, "Guardar cambios")
        btn_save.clicked.connect(self._save_changes)
        r.addWidget(btn_save)

        self.main.addWidget(right, stretch=2)

    # ── Datos ──

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
        dlg = NameDialog(self.window())
        if dlg.exec():
            name = dlg.name()
            if not name:
                return
            if name in self.rules_data:
                InfoBar.warning("Atención", f"'{name}' ya existe.",
                                parent=self, position=InfoBarPosition.TOP, duration=2500)
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
        dlg = MessageBox(
            "Confirmar",
            f"Eliminar perfil '{self.selected_profile}'?",
            self.window()
        )
        if dlg.exec():
            self.rules_data.pop(self.selected_profile, None)
            self.selected_profile = None
            self._save_to_file()
            self._load_rules()

    def _rename_profile(self):
        """Pide el nombre nuevo en un diálogo Fluent y aplica el cambio."""
        if not self.selected_profile:
            return
        viejo = self.selected_profile
        dlg = NameDialog(self.window())
        dlg.titleLabel.setText("Renombrar perfil")
        dlg.yesButton.setText("Renombrar")
        dlg.edit.setText(viejo)
        dlg.edit.selectAll()  # cómodo: escribir encima del nombre actual
        if dlg.exec():
            self._apply_rename(viejo, dlg.name())

    def _apply_rename(self, viejo, nuevo):
        """
        Renombra el perfil de verdad: reglas.json + zonas.json + selección.

        - Conserva el ORDEN de perfiles del JSON (solo cambia la clave).
        - Actualiza zones.json: toda zona que usaba el perfil viejo pasa
          a referenciar el nuevo. Si no, quedaría apuntando a un perfil
          que ya no existe (R0: sin regla = nunca alarmaría).
        """
        nuevo = (nuevo or "").strip().upper()
        if not nuevo or nuevo == viejo:
            return
        if nuevo in self.rules_data:
            InfoBar.warning(
                "Atención", f"'{nuevo}' ya existe.",
                parent=self, position=InfoBarPosition.TOP, duration=2500
            )
            return

        self.rules_data = {
            (nuevo if k == viejo else k): v
            for k, v in self.rules_data.items()
        }
        self.selected_profile = nuevo

        if not self._save_to_file():
            return
        n_zonas = self._renombrar_en_zonas(viejo, nuevo)
        self._load_rules()
        self._seleccionar(nuevo)
        self.rules_updated.emit()

        if n_zonas:
            InfoBar.success(
                "Reglas",
                f"Perfil renombrado a '{nuevo}' ({n_zonas} zona(s) actualizadas)",
                parent=self, position=InfoBarPosition.TOP, duration=2500
            )
        else:
            InfoBar.success(
                "Reglas", f"Perfil renombrado a '{nuevo}'",
                parent=self, position=InfoBarPosition.TOP, duration=2500
            )

    def _renombrar_en_zonas(self, viejo, nuevo):
        """Cambia z['perfil'] en zones.json; devuelve cuántas zonas tocó."""
        if not os.path.exists(self.zones_path):
            return 0
        try:
            with open(self.zones_path, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except Exception:
            return 0
        n = 0
        for zonas_camara in datos.values():
            if not isinstance(zonas_camara, list):
                continue
            for z in zonas_camara:
                if (isinstance(z, dict)
                        and (z.get("perfil") or "").upper() == viejo.upper()):
                    z["perfil"] = nuevo
                    n += 1
        if n:
            try:
                with open(self.zones_path, "w", encoding="utf-8") as f:
                    json.dump(datos, f, indent=2, ensure_ascii=False)
            except Exception:
                return 0
        return n

    def _seleccionar(self, nombre):
        """Deja seleccionado en la lista un perfil por nombre (tras reload)."""
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(Qt.UserRole) == nombre:
                self.profile_list.setCurrentRow(i)
                self._on_profile_clicked(item)
                return

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
            InfoBar.success(
                "Reglas",
                f"Reglas de '{self.selected_profile}' guardadas",
                parent=self, position=InfoBarPosition.TOP, duration=2500
            )
            self.rules_updated.emit()

    def _save_to_file(self):
        try:
            os.makedirs(paths.CONFIG_DIR, exist_ok=True)
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(self.rules_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            InfoBar.error("Error", str(e),
                          parent=self, position=InfoBarPosition.TOP, duration=4000)
            return False