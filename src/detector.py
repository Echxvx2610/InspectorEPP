"""
Módulo Detector + Tracker (Conexionista).
Dos modelos: uno COCO para personas (con tracking ByteTrack y IDs estables)
y uno propio para EPP. Los nombres de clase del modelo EPP se normalizan
al contrato del proyecto (minúsculas, sin espacios).
"""

import os
from ultralytics import YOLO

from src import paths

# Nombres del modelo EPP que no coinciden con el contrato de clases
ALIASES = {"glass": "glasses"}


def normalizar(nombre: str) -> str:
    """'ESD SMOCK' -> 'esd_smock', 'GLASS' -> 'glasses', 'HELMET' -> 'helmet'."""
    n = nombre.strip().lower().replace(" ", "_")
    return ALIASES.get(n, n)


def _primer_existente(candidatos):
    for p in candidatos:
        if p and os.path.exists(p):
            return str(p)
    return None


class PPEDetector:
    def __init__(self, model_path=paths.MODELS_DIR / "ppe_best.pt"):
        self._next_fallback_id = 1

        # --- Modelo EPP (propio, YOLO26) ---
        ppe_path = _primer_existente([
            model_path,
            paths.MODELS_DIR / "ppe_best.pt",
            paths.MODELS_DIR / "ppe_yolov8.pt",
        ])
        self.ppe_model = YOLO(ppe_path) if ppe_path else None
        self.model_path = ppe_path

        # --- Modelo de personas (COCO) ---
        person_path = _primer_existente([
            paths.MODELS_DIR / "person_coco.pt",
            paths.PROJECT_ROOT / "yolov8n.pt",   # respaldo mientras no lo copies a models/
        ])
        self.person_model = YOLO(person_path) if person_path else None

        # Compatibilidad: otras partes del código pueden usar detector.model
        self.model = self.ppe_model or self.person_model

        if self.ppe_model is None:
            print("[PPEDetector] AVISO: no se encontró models/ppe_best.pt; "
                  "no habrá detecciones de EPP.")
        if self.person_model is None:
            print("[PPEDetector] AVISO: no se encontró modelo COCO de personas; "
                  "se usará la clase PERSON del modelo EPP (débil).")

    def detect_and_track(self, frame, conf=0.35, conf_ppe=0.25):
        """
        Detección de personas (con tracking) y de EPP.

        conf      -> umbral para personas
        conf_ppe  -> umbral para EPP (más bajo: BOOTS sale con ~0.4)

        Returns:
            persons (list): [{'id': int, 'bbox': [x1, y1, x2, y2], 'conf': float}]
            ppe_items (list): [{'class': str, 'bbox': [x1, y1, x2, y2], 'conf': float}]
            results: Results de Ultralytics del modelo EPP (o del de personas
                     si no hay modelo EPP)
        """
        persons = []
        ppe_items = []

        # ---- 1) Personas: modelo COCO + ByteTrack ----
        res_p = None
        if self.person_model is not None:
            try:
                res_p = self.person_model.track(
                    frame, persist=True, classes=[0], conf=conf, verbose=False
                )[0]
            except Exception:
                res_p = self.person_model(
                    frame, classes=[0], conf=conf, verbose=False
                )[0]

            if res_p.boxes is not None:
                for idx, box in enumerate(res_p.boxes):
                    track_id = int(box.id[0].item()) if box.id is not None else idx + 1
                    persons.append({
                        "id": track_id,
                        "bbox": [int(v) for v in box.xyxy[0].tolist()],
                        "conf": float(box.conf[0].item()),
                    })

        # ---- 2) EPP: modelo propio ----
        res_e = None
        if self.ppe_model is not None:
            res_e = self.ppe_model(frame, conf=conf_ppe, verbose=False)[0]

            if res_e.boxes is not None:
                for idx, box in enumerate(res_e.boxes):
                    cls_id = int(box.cls[0].item())
                    nombre = normalizar(self.ppe_model.names.get(cls_id, ""))
                    xyxy = [int(v) for v in box.xyxy[0].tolist()]
                    confidence = float(box.conf[0].item())

                    if nombre == "person":
                        # Solo se usa si no hay modelo COCO de personas
                        if self.person_model is None and confidence >= conf:
                            persons.append({"id": idx + 1, "bbox": xyxy, "conf": confidence})
                        continue

                    ppe_items.append({
                        "class": nombre,
                        "bbox": xyxy,
                        "conf": confidence,
                    })

        return persons, ppe_items, (res_e if res_e is not None else res_p)

    def detect(self, frame):
        """Compatibilidad con versiones anteriores."""
        modelo = self.ppe_model or self.person_model
        results = modelo(frame, verbose=False)[0]
        detected_classes = [modelo.names[int(b.cls[0])] for b in results.boxes]
        return frame, detected_classes, results
