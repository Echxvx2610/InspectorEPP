"""
Utilidades de UI compartidas: roles de texto, iconos con estados,
chips de estado y notificaciones no bloqueantes (toast).
"""

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


# ── Propiedades dinámicas (role / state) ─────────────────────────────

def _repolish(widget: QWidget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_role(widget: QWidget, role: str) -> QWidget:
    """Asigna un rol de texto definido en styles.py. Devuelve el widget."""
    widget.setProperty("role", role)
    _repolish(widget)
    return widget


def set_state(widget: QWidget, state: str) -> QWidget:
    """Asigna estado visual: ok | warn | bad | idle."""
    widget.setProperty("state", state)
    _repolish(widget)
    return widget


def make_label(text: str, role: str = None) -> QLabel:
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    return lbl


# ── Iconos SVG con color según estado ────────────────────────────────

def _tinted_pixmap(icon: QIcon, color: str, size: int) -> QPixmap:
    src = icon.pixmap(QSize(size, size))
    out = QPixmap(src.size())
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, src)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return out


def tint_icon(icon: QIcon, color: str, size: int = 18) -> QIcon:
    """Devuelve el mismo icono con un color sólido (útil para botones primarios: blanco)."""
    out = QIcon()
    out.addPixmap(_tinted_pixmap(icon, color, size))
    return out


def nav_icon(icon: QIcon, off: str = "#616161", on: str = "#0078d4", size: int = 18) -> QIcon:
    """Icono para botones checkables: gris en reposo, azul cuando está activo."""
    out = QIcon()
    out.addPixmap(_tinted_pixmap(icon, off, size), QIcon.Normal, QIcon.Off)
    out.addPixmap(_tinted_pixmap(icon, on, size), QIcon.Normal, QIcon.On)
    return out


# ── Chip de estado (punto de color + texto) ──────────────────────────

class StatusChip(QFrame):
    """
    Indicador compacto: [● Texto]. Estados: idle | ok | warn | bad.
    Ejemplo:  chip.set_status("Transmisión activa", "ok")
    """

    def __init__(self, text: str = "", state: str = "idle", parent=None):
        super().__init__(parent)
        self.setProperty("role", "chip")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 12, 4)
        lay.setSpacing(7)

        self.dot = QFrame()
        self.dot.setFixedSize(8, 8)
        self.dot.setProperty("role", "chip-dot")

        self.label = QLabel(text)
        self.label.setProperty("role", "chip-text")

        lay.addWidget(self.dot)
        lay.addWidget(self.label)
        self.set_status(text, state)

    def set_status(self, text: str, state: str = "idle"):
        self.label.setText(text)
        for w in (self, self.dot):
            w.setProperty("state", state)
            _repolish(w)


# ── Toast no bloqueante ──────────────────────────────────────────────

class Toast(QLabel):
    """
    Mensaje flotante centrado abajo del widget padre. Sustituye a
    QMessageBox.information() para confirmaciones simples.

        self.toast = Toast(self)
        self.toast.show_message("Ajustes guardados")
        self.toast.show_message("No se pudo guardar", "bad")
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setProperty("role", "toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text: str, state: str = "ok", ms: int = 2500):
        self.setText(text)
        self.setProperty("state", state)
        _repolish(self)
        self.adjustSize()
        parent = self.parentWidget()
        self.move((parent.width() - self.width()) // 2,
                  parent.height() - self.height() - 24)
        self.raise_()
        self.show()
        self._timer.start(ms)