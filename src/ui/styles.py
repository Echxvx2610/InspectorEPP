"""
Sistema de estilos QSS para Guardián EPP.
Tema: Windows Fluent Light.

Reglas de diseño:
- Solo QMainWindow/QDialog pintan el fondo gris; el resto de widgets es transparente.
- Los fondos blancos viven únicamente en tarjetas ([class="card"]) e inputs.
- El azul se reserva para acciones y estado activo (nav activo, botón primario, foco).
- Los textos usan roles: title / section / eyebrow / field / caption / muted / value.
  Se asignan con  widget.setProperty("role", "...")  o con ui_helpers.set_role().

Assets requeridos (en <raíz del proyecto>/assets/icons/):
  chevron-down.svg, check.svg
"""

from pathlib import Path

# src/ui/styles.py -> raíz del proyecto = parents[2]
_ICONS = (Path(__file__).resolve().parents[2] / "assets" / "icons").as_posix()

_QSS = """
/* ══ Base ══ */
QWidget {
    background: transparent;
    color: #1a1a1a;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}

QMainWindow, QDialog {
    background-color: #f3f3f3;
}

QMessageBox QPushButton, QInputDialog QPushButton {
    min-width: 72px;
}

QToolTip {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d1d1d1;
    padding: 4px 8px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 20px; border-radius: 3px; }
QMenu::item:selected { background-color: #e8f0fe; }

QScrollArea { background: transparent; border: none; }

/* ══ Sidebar ══ */
#Sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    min-width: 200px;
    max-width: 200px;
}

QPushButton[class="nav-btn"] {
    background-color: transparent;
    color: #616161;
    border: none;
    border-radius: 4px;
    text-align: left;
    padding: 9px 12px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton[class="nav-btn"]:hover {
    background-color: #f0f0f0;
    color: #1a1a1a;
}
QPushButton[class="nav-btn"]:checked {
    background-color: #e8f0fe;
    color: #0078d4;
}

/* ══ Tarjetas ══ */
QFrame[class="card"] {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
}

/* ══ Roles de texto ══ */
QLabel[role="title"]   { font-size: 18px; font-weight: 700; }
QLabel[role="brand"]   { font-size: 14px; font-weight: 700; }
QLabel[role="section"] { font-size: 14px; font-weight: 700; }
QLabel[role="eyebrow"] { color: #8a8a8a; font-size: 11px; font-weight: 700; }
QLabel[role="field"]   { color: #616161; font-size: 12px; font-weight: 600; }
QLabel[role="caption"] { color: #8a8a8a; font-size: 11px; }
QLabel[role="muted"]   { color: #8a8a8a; font-size: 12px; }
QLabel[role="value"]   { font-size: 22px; font-weight: 700; }
QLabel[role="value-sm"] { font-size: 13px; font-weight: 700; }
QLabel[role="value"][state="ok"]  { color: #107c10; }
QLabel[role="value"][state="bad"] { color: #d13438; }

/* ══ Chips de estado ══ */
QFrame[role="chip"] {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
}
QFrame[role="chip"][state="ok"]   { background-color: #f1faf1; border-color: #c7e6c7; }
QFrame[role="chip"][state="warn"] { background-color: #fff8e5; border-color: #f2dfa0; }
QFrame[role="chip"][state="bad"]  { background-color: #fdf3f4; border-color: #f1bbbc; }

QFrame[role="chip-dot"] { background-color: #a0a0a0; border: none; border-radius: 4px; }
QFrame[role="chip-dot"][state="ok"]   { background-color: #107c10; }
QFrame[role="chip-dot"][state="warn"] { background-color: #f7630c; }
QFrame[role="chip-dot"][state="bad"]  { background-color: #d13438; }

QLabel[role="chip-text"] { color: #424242; font-size: 12px; font-weight: 600; }

/* ══ Toast (confirmaciones no bloqueantes) ══ */
QLabel[role="toast"] {
    background-color: #1a1a1a;
    color: #ffffff;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}
QLabel[role="toast"][state="bad"] { background-color: #d13438; }

/* ══ Superficies oscuras (video / lienzo) ══ */
#ZoneCanvas {
    background-color: #0f1014;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
}

/* ══ Separadores ══ */
QFrame[frameShape="4"] {
    background-color: #ebebeb;
    border: none;
    min-height: 1px;
    max-height: 1px;
}
QFrame[frameShape="5"] {
    background-color: #ebebeb;
    border: none;
    min-width: 1px;
    max-width: 1px;
}

/* ══ Botones ══ */
QPushButton {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover    { background-color: #f5f5f5; border-color: #c1c1c1; }
QPushButton:pressed  { background-color: #ebebeb; }
QPushButton:disabled { background-color: #f3f3f3; color: #a0a0a0; border-color: #e0e0e0; }
QPushButton:focus    { outline: none; }

QPushButton[class="btn-primary"] {
    background-color: #0078d4;
    border: 1px solid #006cbe;
    color: #ffffff;
}
QPushButton[class="btn-primary"]:hover    { background-color: #106ebe; }
QPushButton[class="btn-primary"]:pressed  { background-color: #005a9e; }
QPushButton[class="btn-primary"]:disabled { background-color: #cfe4f7; border-color: #cfe4f7; color: #ffffff; }

QPushButton[class="btn-primary-outline"] {
    background-color: #ffffff;
    border: 1px solid #0078d4;
    color: #0078d4;
}
QPushButton[class="btn-primary-outline"]:hover   { background-color: #e8f0fe; }
QPushButton[class="btn-primary-outline"]:pressed { background-color: #d6e6fb; }

QPushButton[class="btn-danger"] {
    background-color: #ffffff;
    border: 1px solid #d13438;
    color: #d13438;
}
QPushButton[class="btn-danger"]:hover    { background-color: #fef1f1; }
QPushButton[class="btn-danger"]:pressed  { background-color: #fbe0e0; }
QPushButton[class="btn-danger"]:disabled { border-color: #e8c5c6; color: #e0a3a5; background-color: #f3f3f3; }

/* ══ Inputs ══ */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 6px 10px;
    color: #1a1a1a;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #b5b5b5; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #0078d4; }
QLineEdit:disabled, QSpinBox:disabled { background-color: #f3f3f3; color: #a0a0a0; }

QComboBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 5px 10px;
    color: #1a1a1a;
    min-width: 120px;
}
QComboBox:hover { border-color: #0078d4; }
QComboBox::drop-down {
    border: none;
    width: 26px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}
QComboBox::down-arrow {
    image: url(__ICONS__/chevron-down.svg);
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    selection-background-color: #e8f0fe;
    selection-color: #1a1a1a;
    color: #1a1a1a;
    padding: 2px;
    outline: none;
}

/* ══ Tablas ══ */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    gridline-color: transparent;
    color: #1a1a1a;
    outline: none;
}
QTableWidget::item { padding: 6px 10px; border: none; }
QTableWidget::item:selected { background-color: #e8f0fe; color: #1a1a1a; }
QTableCornerButton::section { background-color: #fafafa; border: none; }

QHeaderView::section {
    background-color: #fafafa;
    color: #616161;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #e0e0e0;
    padding: 8px 10px;
}

/* ══ Listas ══ */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    color: #1a1a1a;
    padding: 2px;
    outline: none;
}
QListWidget::item { border-radius: 3px; padding: 7px 10px; margin-bottom: 1px; }
QListWidget::item:hover    { background-color: #f5f5f5; }
QListWidget::item:selected { background-color: #e8f0fe; color: #1a1a1a; }

/* ══ Checkboxes ══ */
QCheckBox { spacing: 8px; font-size: 13px; color: #1a1a1a; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #b5b5b5;
    background-color: #ffffff;
}
QCheckBox::indicator:hover { border-color: #0078d4; }
QCheckBox::indicator:checked {
    background-color: #0078d4;
    border-color: #0078d4;
    image: url(__ICONS__/check.svg);
}

/* ══ Sliders ══ */
QSlider::groove:horizontal { height: 4px; background: #d1d1d1; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #0078d4; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #b5b5b5;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { border-color: #0078d4; }

/* ══ Scrollbars ══ */
QScrollBar:vertical   { border: none; background: transparent; width: 8px; margin: 0; }
QScrollBar:horizontal { border: none; background: transparent; height: 8px; margin: 0; }
QScrollBar::handle:vertical   { background: #c1c1c1; min-height: 24px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #c1c1c1; min-width: 24px; border-radius: 4px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #a0a0a0; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""

MAIN_STYLESHEET = _QSS.replace("__ICONS__", _ICONS)