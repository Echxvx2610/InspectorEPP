"""
Worker de Video para captura asíncrona y procesamiento neuro-simbólico.
Sin cambios funcionales: QThread es independiente del framework de UI,
por lo que funciona igual con qfluentwidgets. Ajustes menores:
  - Emisiones protegidas (try/except) para evitar crashes si la vista
    ya fue destruida durante el cierre de la app.
  - stop() con quit()+wait() para cerrar limpio desde FluentWindow.

Pipeline:
  1. Captura de frame (Cámara / Video / RTSP)
  2. Módulo Geométrico: Dibujar zonas de seguridad delimitadas
  3. Módulo Conexionista: Detección + Tracking (YOLO + ByteTrack)
  4. Módulo Geométrico: Asociación Persona <-> EPP y Ubicación en zona (Pies)
  5. Módulo Simbólico: Evaluación de reglas por zona
  6. Módulo Temporal: Filtro anti-parpadeo de violaciones
  7. Alertas / Notificaciones
"""

import os
import json
import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from src.zones import ZoneManager
from src.detector import PPEDetector
from src.association import PPEAssociator
from src.rule_engine import RuleEngine
from src.temporal import TemporalFilter
from src.alert_system import AlertSystem
from src import paths

SETTINGS_PATH = str(paths.SETTINGS_PATH)  # absoluta: ver src/paths.py


class VideoWorker(QThread):
    # Emite: (frame_anotado o None, metadata_dict)
    frame_ready = Signal(object, dict)
    fps_updated = Signal(float)
    status_message = Signal(str)

    def __init__(self, source=0, parent=None):
        super().__init__(parent)
        self.source = source
        self._running = False
        self._paused = False
        self._mutex = QMutex()
        self.cap = None
        self.conf_threshold = 0.30

        # Módulos del sistema neuro-simbólico
        self.zone_manager = ZoneManager()
        self.detector = PPEDetector()
        self.associator = PPEAssociator()
        self.rule_engine = RuleEngine()
        self.temporal = TemporalFilter(grace_period_sec=1.5, min_consecutive_frames=4)
        self.alert_system = AlertSystem()

        self._load_settings()

    def _load_settings(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    self.apply_settings(json.load(f))
            except Exception:
                pass

    def apply_settings(self, s: dict):
        """Aplica los ajustes de la vista de Ajustes en caliente."""
        with QMutexLocker(self._mutex):
            self.conf_threshold = float(s.get("confidence_threshold", 0.30))
            self.temporal.min_consecutive_frames = int(
                s.get("grace_period_frames", 4)
            )

    def reload_zones(self):
        """Recarga la configuración de zonas desde archivo."""
        with QMutexLocker(self._mutex):
            self.zone_manager.reload()

    def reload_rules(self):
        """Recarga las reglas de EPP desde archivo."""
        with QMutexLocker(self._mutex):
            self.rule_engine.reload()

    def set_source(self, source):
        with QMutexLocker(self._mutex):
            self.source = source
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def pause(self):
        with QMutexLocker(self._mutex):
            self._paused = True

    def resume(self):
        with QMutexLocker(self._mutex):
            self._paused = False

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False
        self.quit()
        # La apertura de cámara con CAP_DSHOW bloquea ~2-6 s sin poder
        # cancelarse; un wait() corto destruiría el QThread mientras
        # sigue vivo y aborta el proceso. Esperar hasta que termine.
        self.wait(10000)

    def _emit_frame(self, frame, metadata):
        """Emite de forma segura: si la vista UI ya no existe, no crashea."""
        try:
            self.frame_ready.emit(frame, metadata)
        except RuntimeError:
            self._running = False

    def _open_capture(self, src):
        """Intenta abrir la fuente de video con backend adecuado."""
        if isinstance(src, int) or (isinstance(src, str) and str(src).isdigit()):
            idx = int(src)
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(idx)
            return cap
        return cv2.VideoCapture(str(src))

    def run(self):
        self._running = True
        fps_count = 0
        fps_start = time.time()
        current_fps = 0.0

        while self._running:
            if self._paused:
                self.msleep(100)
                continue

            with QMutexLocker(self._mutex):
                src = self.source

            # Inicializar captura si no está abierta
            if self.cap is None or not self.cap.isOpened():
                try:
                    self.cap = self._open_capture(src)
                except Exception:
                    self.cap = None

                if self.cap is None or not self.cap.isOpened():
                    self.status_message.emit(f"Cámara {src} no disponible.")
                    metadata = {
                        "timestamp": time.strftime("%H:%M:%S"),
                        "camera_available": False,
                        "status": "Cámara no disponible",
                        "persons": [],
                        "global_safe": True,
                        "active_zone": "--",
                        "fps": 0.0,
                        "relay_blocked": False,
                        "alerts": [],
                        "events": []
                    }
                    self.fps_updated.emit(0.0)
                    self._emit_frame(None, metadata)
                    if self.cap is not None:
                        self.cap.release()
                        self.cap = None
                    self.msleep(1000)
                    continue
                else:
                    self.status_message.emit(f"Cámara {src} conectada.")

            ret, frame = self.cap.read()
            if not ret or frame is None:
                # Si es archivo de video, reiniciar en loop infinito
                if isinstance(src, str) and not src.isdigit():
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()

                if not ret or frame is None:
                    metadata = {
                        "timestamp": time.strftime("%H:%M:%S"),
                        "camera_available": False,
                        "status": "Sin señal de video",
                        "persons": [],
                        "global_safe": True,
                        "active_zone": "--",
                        "fps": 0.0,
                        "relay_blocked": False,
                        "alerts": [],
                        "events": []
                    }
                    self.fps_updated.emit(0.0)
                    self._emit_frame(None, metadata)
                    self.msleep(500)
                    continue

            # ── 1. Pipeline Neuro-Simbólico ──
            annotated_frame = frame.copy()
            cam_key = f"camara_{src}" if str(src).isdigit() else "camara_0"

            with QMutexLocker(self._mutex):
                conf = self.conf_threshold

            # A. Dibujar zonas de seguridad delimitadas sobre el frame
            annotated_frame = self.zone_manager.draw_zones(
                annotated_frame, camera_key=cam_key
            )

            # B. Inferencia conexionista + tracking de personas y EPP
            persons, ppe_items, _ = self.detector.detect_and_track(frame, conf=conf)

            # C. Asociación geométrica Persona <-> EPP
            associations = self.associator.associate(persons, ppe_items)

            # D. Evaluación simbólica y temporal por persona
            persons_meta = []
            global_safe = True
            relay_blocked = False
            alerts = []
            events = []
            active_zones_found = set()

            for p in persons:
                pid = p["id"]
                px1, py1, px2, py2 = p["bbox"]

                # Punto de evaluación geométrica: centro inferior de los pies
                feet_point = (int((px1 + px2) / 2), int(py2))

                zone = self.zone_manager.find_zone_for_point(
                    feet_point, camera_key=cam_key
                )
                zone_profile = zone.get("perfil") if zone else None
                zone_name = zone.get("nombre") if zone else "Fuera de zona"

                if zone_profile:
                    active_zones_found.add(zone_name)

                assoc_data = associations.get(pid, {"present_ppe": [], "items": []})
                present_ppe = assoc_data["present_ppe"]

                eval_res = self.rule_engine.evaluate_person(
                    present_ppe, zone_profile, zone_name
                )
                is_violating = not eval_res["is_safe"]

                is_confirmed_alarm = self.temporal.update(pid, is_violating)

                # Anotación visual de la persona en el frame
                if not zone_profile:
                    color = (160, 160, 160)
                    status_text = "FUERA DE ZONA"
                    tag_bg = (60, 60, 60)
                elif eval_res["is_safe"]:
                    color = (50, 205, 50)
                    status_text = "CONFORME"
                    tag_bg = (30, 140, 30)
                else:
                    color = (40, 40, 230)
                    status_text = f"FALTA EPP ({', '.join(eval_res['missing'])})"
                    tag_bg = (30, 30, 180)

                    if is_confirmed_alarm:
                        global_safe = False
                        relay_blocked = True
                        alert_msg = (
                            f"Persona #{pid} en {zone_name} "
                            f"({zone_profile}): {eval_res['explanation']}"
                        )
                        alerts.append(alert_msg)
                        events.append({
                            "ts": time.strftime("%H:%M:%S"),
                            "cam": cam_key,
                            "zone": zone_name,
                            "person": f"#{pid}",
                            "infraction": f"Falta {', '.join(eval_res['missing'])}",
                            "rule": zone_profile or "--",
                            "relay": "Bloqueado",
                        })
                        self.alert_system.trigger_alert(
                            f"Infracción en {zone_name}: {eval_res['explanation']}"
                        )

                cv2.rectangle(
                    annotated_frame, (px1, py1), (px2, py2), color, 2, cv2.LINE_AA
                )

                badge_text = f"#{pid} {status_text}"
                (tw, th), _ = cv2.getTextSize(
                    badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
                )
                cv2.rectangle(
                    annotated_frame,
                    (px1, max(0, py1 - th - 8)), (px1 + tw + 8, py1),
                    tag_bg, -1
                )
                cv2.putText(
                    annotated_frame, badge_text, (px1 + 4, max(12, py1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA
                )

                cv2.circle(annotated_frame, feet_point, 4, color, -1)

                persons_meta.append({
                    "id": pid,
                    "zone": zone_name,
                    "profile": zone_profile or "GENERAL",
                    "is_safe": eval_res["is_safe"],
                    "bbox": [px1, py1, px2, py2],
                    "present_ppe": present_ppe,
                    "missing_ppe": eval_res["missing"],
                    "rule": eval_res["explanation"]
                })

            self.temporal.cleanup_old_tracks([p["id"] for p in persons])

            # Cálculo de FPS real
            fps_count += 1
            now = time.time()
            if now - fps_start >= 0.5:
                current_fps = round(fps_count / (now - fps_start), 1)
                fps_count = 0
                fps_start = now
                self.fps_updated.emit(current_fps)

            zone_display = ", ".join(active_zones_found) if active_zones_found else "GENERAL"
            metadata = {
                "timestamp": time.strftime("%H:%M:%S"),
                "camera_available": True,
                "status": "Transmisión activa",
                "persons": persons_meta,
                "global_safe": global_safe,
                "active_zone": zone_display,
                "fps": current_fps,
                "relay_blocked": relay_blocked,
                "alerts": alerts,
                "events": events,
                # Frame BGR original (sin zonas/cajas dibujadas), para el
                # editor de zonas: los polígonos deben marcarse sobre
                # la imagen limpia de la cámara.
                "raw": frame
            }

            if self._running:
                self._emit_frame(annotated_frame, metadata)

            self.msleep(10)

        if self.cap is not None:
            self.cap.release()
            self.cap = None