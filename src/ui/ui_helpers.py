"""
Utilidades residuales de UI para la versión PyQt-Fluent-Widgets.

Con Fluent la mayoría de helpers originales desaparecen:
  - set_role / set_state / make_label -> BodyLabel, SubtitleLabel,
    CaptionLabel, StrongBodyLabel... de qfluentwidgets.
  - StatusChip -> InfoBadge (success / warning / error / info).
  - Toast       -> InfoBar.success(...) / InfoBar.error(...).
Solo queda tint_icon: reutilizado para colorear el escudo de la marca.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget


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
    """Devuelve el mismo icono con un color sólido."""
    out = QIcon()
    out.addPixmap(_tinted_pixmap(icon, color, size))
    return out


# ── Mapa de equivalencias (referencia rápida, no se ejecuta) ──
#
#   ANTES (QSS custom)                  AHORA (qfluentwidgets)
#   ────────────────────────────────    ─────────────────────────────────
#   set_role(lbl, "title")          ->  TitleLabel("...")
#   set_role(lbl, "section")        ->  SubtitleLabel("...")
#   set_role(lbl, "field")          ->  BodyLabel("...")
#   set_role(lbl, "caption")        ->  CaptionLabel("...")
#   set_role(lbl, "muted")           ->  BodyLabel + setStyleSheet color
#   set_role(lbl, "value")           ->  SubtitleLabel / TitleLabel
#   StatusChip("txt", "ok")          ->  InfoBadge.success("txt")
#   StatusChip("txt", "bad")         ->  InfoBadge.error("txt")
#   StatusChip("txt", "warn")        ->  InfoBadge.warning("txt")
#   StatusChip("txt", "idle")        ->  InfoBadge.info("txt")
#   Toast.show_message("ok msg")     ->  InfoBar.success(...)
#   Toast.show_message(msg, "bad")   ->  InfoBar.error(...)
#   QMessageBox.information          ->  InfoBar.info(...)
#   QMessageBox.question            ->  MessageBox(...).exec()
#   QPushButton + class="btn-primary" ->  PrimaryPushButton(FIF.X, "...")
#   QPushButton + class="btn-danger" ->  PushButton(FIF.DELETE, "...")
#   QComboBox                        ->  ComboBox
#   QLineEdit                        ->  LineEdit
#   QTableWidget                     ->  TableWidget
#   QListWidget                      ->  ListWidget
#   QFrame class="card"              ->  CardWidget
#   QSS MAIN_STYLESHEET              ->  setTheme(Theme.LIGHT/DARK)