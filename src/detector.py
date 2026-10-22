"""
Módulo Detector + Tracker (Conexionista).
Inferencia YOLO con seguimiento ByteTrack para asignación de IDs estables por persona
y extracción de detecciones de implementos de seguridad (EPP).
"""

import os
from ultralytics import YOLO


class PPEDetector:
    def __init__(self, model_path="models/ppe_best.pt"):
        self.model_path = model_path
        self.model = None
        self._next_fallback_id = 1

        # Buscar modelos disponibles en orden de prioridad
        candidate_paths = [
            model_path,
            "models/ppe_yolov8.pt",
            "models/ppe_best.pt",
            "yolov8n.pt"
        ]

        loaded_path = None
        for path in candidate_paths:
            if path and os.path.exists(path):
                loaded_path = path
                break

        if loaded_path:
            self.model = YOLO(loaded_path)
            self.model_path = loaded_path
        else:
            # Si no existe localmente, ultralytics descarga yolov8n.pt
            self.model = YOLO("yolov8n.pt")
            self.model_path = "yolov8n.pt"

    def detect_and_track(self, frame, conf=0.35):
        """
        Ejecuta detección y tracking persistente sobre el frame.

        Returns:
            persons (list): [{'id': int, 'bbox': [x1, y1, x2, y2], 'conf': float}]
            ppe_items (list): [{'class': str, 'bbox': [x1, y1, x2, y2], 'conf': float}]
            results: Objeto Results de Ultralytics
        """
        persons = []
        ppe_items = []

        try:
            # Inferencia con tracking persistente
            results = self.model.track(frame, persist=True, verbose=False, conf=conf)[0]
        except Exception:
            # Fallback a inferencia simple si tracking tiene problema puntual
            results = self.model(frame, verbose=False, conf=conf)[0]

        if results.boxes is None or len(results.boxes) == 0:
            return persons, ppe_items, results

        for idx, box in enumerate(results.boxes):
            cls_id = int(box.cls[0].item())
            class_name = self.model.names.get(cls_id, "").lower()
            confidence = float(box.conf[0].item())
            xyxy = [int(v) for v in box.xyxy[0].tolist()]

            # Si el modelo tiene ID de tracking asignado, usarlo
            track_id = None
            if box.id is not None:
                track_id = int(box.id[0].item())

            if class_name == "person":
                if track_id is None:
                    # Fallback ID si no hubo tracking
                    track_id = idx + 1
                persons.append({
                    "id": track_id,
                    "bbox": xyxy,
                    "conf": confidence
                })
            else:
                ppe_items.append({
                    "class": class_name,
                    "bbox": xyxy,
                    "conf": confidence
                })

        return persons, ppe_items, results

    def detect(self, frame):
        """Compatibilidad con versiones anteriores."""
        results = self.model(frame, verbose=False)[0]
        detected_classes = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            class_name = self.model.names[cls_id]
            detected_classes.append(class_name)
        return frame, detected_classes, results
