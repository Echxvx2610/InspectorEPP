"""
Ventana Principal — Guardián EPP (PyQt-Fluent-Widgets).
FluentWindow con NavigationInterface reemplaza al sidebar QSS + QStackedWidget.

Incluye captura global de excepciones: si algo revienta en el arranque,
se escribe el traceback a guardian_error.log (y se muestra un diálogo)
en lugar de que la consola se cierre sin mostrar nada.
"""

import sys
import os
from pathlib import Path
import traceback

# Asegurar que la raíz del proyecto esté en sys.path para ejecuciones directas
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF,
    setTheme, Theme, Dialog
)


def _excepthook(exc_type, exc_value, exc_tb):
    """Escribe cualquier excepción no capturada a guardian_error.log."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(msg, file=sys.stderr, flush=True)  # a consola por si se ejecuta desde terminal
    try:
        log_path = PROJECT_ROOT / "guardian_error.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n" + "-" * 60 + "\n")
    except Exception:
        pass
    try:
        dlg = Dialog("Error inesperado", msg[-800:], None)
        dlg.cancelButton.hide()
        dlg.buttonLayout.insertStretch(0)
        dlg.exec()
    except Exception:
        pass


sys.excepthook = _excepthook


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardián EPP — Seguridad Industrial")
        self.resize(1280, 780)
        self.setMinimumSize(1080, 680)

        # Tema claro Fluent (coherente con el diseño actual)
        setTheme(Theme.LIGHT)

        self._last_frame = None

        # ── Vistas (cada una es ScrollArea con objectName único) ──
        from src.ui.monitor import MonitorView
        from src.ui.zone_editor import ZoneEditorView
        from src.ui.rules_editor import RulesEditorView
        from src.ui.events_view import EventsView
        from src.ui.settings_view import SettingsView

        self.view_monitor = MonitorView(self)
        self.view_zones = ZoneEditorView(self)
        self.view_rules = RulesEditorView(self)
        self.view_events = EventsView(self)
        self.view_settings = SettingsView(self)

        # ── Navegación (reemplaza el sidebar manual) ──
        # NOTA: FluentWindow registra cada interfaz automáticamente;
        # NO llamar a initNavigation() (no existe en FluentWindow).
        self.addSubInterface(self.view_monitor, FIF.VIDEO, "Monitoreo")
        self.addSubInterface(self.view_zones, FIF.PIN, "Zonas")
        self.addSubInterface(self.view_rules, FIF.DOCUMENT, "Reglas")
        self.addSubInterface(self.view_events, FIF.HISTORY, "Historial")
        self.addSubInterface(self.view_settings, FIF.SETTING, "Ajustes")

        # Ítem informativo fijo abajo (equivale al "v1.0 MVP")
        self.navigationInterface.addItem(
            routeKey="version",
            icon=FIF.INFO,
            text="v1.0 MVP",
            selectable=False,
            onClick=lambda: None,
            position=NavigationItemPosition.BOTTOM,
            tooltip="Guardián EPP v1.0",
        )

        # ── Señales entre vistas ──
        self.view_monitor.camera_changed.connect(self._on_camera_changed)
        self.view_zones.zones_updated.connect(self._on_zones_updated)
        self.view_zones.camera_selected.connect(self._on_zones_camera_selected)
        self.view_rules.rules_updated.connect(self._on_rules_updated)
        self.view_settings.settings_changed.connect(self._on_settings_changed)

        # ── Worker de video ──
        from src.ui.video_worker import VideoWorker
        self.video_worker = VideoWorker(source=0, parent=self)
        self.video_worker.frame_ready.connect(self._on_frame_received)
        self.video_worker.start()

    def _on_frame_received(self, frame, meta):
        if frame is not None:
            self._last_frame = frame
            self.view_monitor.update_frame(frame, meta)
            # Alimentar el lienzo del editor de zonas con el frame SIN
            # anotaciones (para trazarse encima); la vista se auto-limita
            # a ~5 Hz y solo repinta cuando su pestaña está activa.
            if self.view_zones.isVisible():
                self.view_zones.set_sample_frame(meta.get("raw", frame))
        else:
            self.view_monitor.update_frame(frame, meta)
        for ev in meta.get("events", []):
            self.view_events.add_event(
                ev["ts"], ev["cam"], ev["zone"], ev["person"],
                ev["infraction"], ev["rule"], ev["relay"]
            )

    def _on_camera_changed(self, source, _is_sim=False):
        self.video_worker.set_source(source)

    def _on_zones_camera_selected(self, cam_key):
        """El editor de zonas pidió otra cámara: apuntar el worker a esa
        fuente y sincronizar el combo de Monitoreo en silencio."""
        try:
            source = int(str(cam_key).split("_")[-1])
        except ValueError:
            return
        self.video_worker.set_source(source)
        self.view_monitor.set_source_index(source)

    def _on_settings_changed(self, settings):
        if hasattr(self, "video_worker"):
            self.video_worker.apply_settings(settings)

    def _on_zones_updated(self):
        if hasattr(self, "video_worker"):
            self.video_worker.reload_zones()
        self.view_events.refresh_zones()
        if self._last_frame is not None:
            self.view_zones.set_sample_frame(self._last_frame)

    def _on_rules_updated(self):
        if hasattr(self, "video_worker"):
            self.video_worker.reload_rules()
        self.view_zones._load_profiles()

    def closeEvent(self, event):
        if hasattr(self, "video_worker") and self.video_worker.isRunning():
            self.video_worker.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()