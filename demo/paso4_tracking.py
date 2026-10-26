"""
Paso 4 - Tracking con IDs estables (ByteTrack)
==============================================
Detecion frame a frame + ID persistente por persona (model.track con
persist=True y tracker="bytetrack.yaml").

Uso (desde la raiz del proyecto):
    python demo/paso4_tracking.py

Controles:
    s   salir

Referencia: src/detector.py (PPEDetector.detect_and_track)
"""

import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent
# yolov8n.pt vive en demo/ y en la raiz; usar el primero que exista
# (asi el script funciona donde sea que este el CWD)
modelo_path = BASE / "yolov8n.pt"
if not modelo_path.exists():
    modelo_path = Path("yolov8n.pt")
model = YOLO(str(modelo_path))
# print("Clases:", model.names)

# paleta de colores para ids
PALETA = [
    (80, 220, 60), (60, 80, 255), (250, 170, 30),
    (255, 0, 200), (0, 200, 200),
]

cap = cv2.VideoCapture(0)
ids_previos = set()

# ── RETO COMPLETADO: la estela ────────────────────────────────────────────
# historias guarda la memoria del CAMINO de cada persona. Es la memoria
# temporal que despues usa src/temporal.py para confirmar violaciones:
# la alarma solo se dispara si la violacion persiste frame tras frame.
#   {track_id: [(x, y) del punto de los pies en frames pasados, ...]}
historias = {}
MAX_PUNTOS = 30  # los 30 ultimos frames (~1-2 s de video)

while True:
    ok, frame = cap.read()
    if not ok:
        break
    # percepcion del modelo
    # conf = umbral minimo de confianza para detectar objetos
    # verbose = si es True, muestra informacion del modelo
    # con conf en 0.8 no entregaria la lectura: el suitcase reporta 0.60 max
    # persist=True = mantener el tracking entre frames
    # bytetrack.yaml = sin GMC; con camaras fijas no aporta nada
    #   (ver leccion del warning "not enough matching points" en GUIA.md)
    results = model.track(frame, conf=0.3, verbose=False, persist=True,
                          tracker="bytetrack.yaml")
    boxes = results[0].boxes  # detecciones del frame
    id_actuales = set()
    for box in boxes:
        nombre = model.names[int(box.cls[0].item())]  # id -> texto
        if box.id is None:
            continue

        track_id = int(box.id[0].item())      # id del tracker
        conf = float(box.conf[0].item())      # confianza 0..1
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        id_actuales.add(track_id)
        color = PALETA[track_id % len(PALETA)]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"ID {track_id} {conf:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        pies = ((x1 + x2) // 2, y2)  # el punto que usan las zonas (paso 6)
        cv2.circle(frame, pies, 8, (255, 0, 0), -1)

        # ── estela: anclar el punto y dibujar el camino ──
        historias.setdefault(track_id, []).append(pies)
        historias[track_id] = historias[track_id][-MAX_PUNTOS:]
        # la estela hereda el color de la caja; segmentos consecutivos
        # entre puntos consecutivos de los pies
        trail = historias[track_id]
        for i in range(1, len(trail)):
            cv2.line(frame, trail[i - 1], trail[i], color, 2)

    # quien entro y quien salio vs. el frame anterior
    nuevos = id_actuales - ids_previos
    salidos = ids_previos - id_actuales
    if nuevos:
        print("Entraron: ", sorted(nuevos))
    if salidos:
        print("Salieron: ", sorted(salidos))

    # limpiar la estela de quien ya salio del cuadro para siempre
    for fin in list(historias):
        if fin not in id_actuales:
            del historias[fin]

    ids_previos = id_actuales

    cv2.imshow("Paso 4 - Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord("s"):
        break
    if cv2.getWindowProperty("Paso 4 - Tracking",
                             cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
