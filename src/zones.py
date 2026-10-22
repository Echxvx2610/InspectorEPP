"""
Módulo de Gestión de Zonas de Seguridad (Geométrico).
Carga polígonos desde config/zones.json, evalúa si puntos (pies) caen en zonas
y dibuja los polígonos y etiquetas sobre los frames de video.
"""

import os
import json
import cv2
import numpy as np


# Colores por perfil (BGR)
PROFILE_COLORS = {
    "SOLDADURA": ((30, 140, 255), (20, 40, 80)),    # Borde naranja, fondo tenue
    "SMT": ((235, 170, 0), (70, 50, 10)),            # Borde cian/azul claro, fondo tenue
    "LABORATORIO": ((220, 200, 40), (60, 50, 10)),   # Borde turquesa
    "GENERAL": ((60, 210, 80), (15, 60, 25)),        # Borde verde
}
DEFAULT_COLOR = ((240, 160, 40), (60, 40, 10))


class ZoneManager:
    def __init__(self, config_path="config/zones.json"):
        self.config_path = config_path
        self.zones_by_camera = {}
        self.reload()

    def reload(self):
        """Recarga la configuración de zonas desde el archivo JSON."""
        if not os.path.exists(self.config_path):
            self.zones_by_camera = {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.zones_by_camera = json.load(f)
        except Exception as e:
            print(f"Error al cargar zonas desde {self.config_path}: {e}")
            self.zones_by_camera = {}

    def get_zones_for_camera(self, camera_key="camara_0"):
        """Obtiene la lista de zonas para una cámara dada."""
        # Normalizar clave (0 -> camara_0)
        key = self._normalize_camera_key(camera_key)
        # Si no existe la clave exacta, probar con camara_0 por defecto
        return self.zones_by_camera.get(key, self.zones_by_camera.get("camara_0", []))

    def _normalize_camera_key(self, cam):
        if isinstance(cam, int) or (isinstance(cam, str) and cam.isdigit()):
            return f"camara_{cam}"
        if isinstance(cam, str) and cam.startswith("camara_"):
            return cam
        return "camara_0"

    def find_zone_for_point(self, point, camera_key="camara_0"):
        """
        Evalúa si un punto (x, y) cae dentro de alguna zona de la cámara.
        Retorna la zona (dict) o None si está fuera de toda zona (R5).
        """
        zones = self.get_zones_for_camera(camera_key)
        px, py = point

        for z in zones:
            pts = z.get("poligono", [])
            if len(pts) < 3:
                continue
            poly = np.array(pts, dtype=np.int32)
            # cv2.pointPolygonTest >= 0 significa que está dentro o en el borde
            if cv2.pointPolygonTest(poly, (float(px), float(py)), False) >= 0:
                return z

        return None

    def draw_zones(self, frame, camera_key="camara_0", alpha=0.25):
        """
        Dibuja los polígonos de zonas sobre el frame con relleno semitransparente
        y etiqueta informativa con nombre y perfil.
        """
        zones = self.get_zones_for_camera(camera_key)
        if not zones:
            return frame

        overlay = frame.copy()

        for z in zones:
            pts = z.get("poligono", [])
            if len(pts) < 3:
                continue
            poly = np.array(pts, dtype=np.int32)
            perfil = z.get("perfil", "GENERAL").upper()
            nombre = z.get("nombre", "Zona")

            border_color, fill_color = PROFILE_COLORS.get(perfil, DEFAULT_COLOR)

            # Relleno tenue en overlay
            cv2.fillPoly(overlay, [poly], fill_color)

            # Borde nítido en el frame original
            cv2.polylines(frame, [poly], isClosed=True, color=border_color, thickness=2, lineType=cv2.LINE_AA)

            # Etiqueta de cabecera de la zona
            x_min = int(np.min(poly[:, 0]))
            y_min = int(np.min(poly[:, 1]))
            label = f"{nombre} [{perfil}]"

            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                frame,
                (x_min, max(0, y_min - lh - 8)),
                (x_min + lw + 10, y_min),
                border_color,
                -1
            )
            cv2.putText(
                frame,
                label,
                (x_min + 5, max(12, y_min - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # Aplicar transparencia del relleno
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame
