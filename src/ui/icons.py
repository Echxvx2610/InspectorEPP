"""
Íconos residuales para Guardián EPP en PyQt-Fluent-Widgets.

Los íconos de navegación, botones y diálogos ahora vienen de
qfluentwidgets.FluentIcon (FIF.VIDEO, FIF.MAP, FIF.SAVE, FIF.DELETE...),
por lo que solo quedan:
  - icon_shield:        logo de la marca en la navegación.
  - pixmap_*:           pixmaps que se dibujan DIRECTAMENTE sobre el video
                        o el lienzo (no pueden ser QIcon de botón).
"""

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ACCENT = "#0078d4"
GREEN = "#107c10"
RED = "#d13438"
GRAY = "#8a8a8a"


def _svg(svg_str, size=20):
    """Renderiza SVG inline a QPixmap (para pintar sobre frames/canvas)."""
    data = QByteArray(svg_str.encode("utf-8"))
    renderer = QSvgRenderer(data)
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(img)


def _svg_icon(svg_str, size=20):
    """Renderiza SVG inline a QIcon (para botones/labels)."""
    return QIcon(_svg(svg_str, size))


# ── Marca ────────────────────────────────────────────────

def icon_shield(color=ACCENT, size=22):
    return _svg_icon(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>''', size)


# ── Pixmaps para overlay sobre video ─────────────────────

def pixmap_camera_off(color="#4b5563", size=48):
    return _svg(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <line x1="1" y1="1" x2="23" y2="23"/>
        <path d="M21 21H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3m3-3h6l2 3h4a2 2 0 0 1 2 2v9.34m-7.72-2.06a4 4 0 1 1-5.56-5.56"/>
    </svg>''', size)


def pixmap_check(color=GREEN, size=16):
    return _svg(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
    </svg>''', size)


def pixmap_x(color=RED, size=16):
    return _svg(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>''', size)


def pixmap_dot(color=GRAY, size=16):
    return _svg(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>''', size)