import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
#print("Clases: ", model.names)

# paleta de colores para ids
PALETA = [(80, 220, 60), (60, 80, 255), (250, 170, 30),
          (255, 0, 200), (0, 200, 200)]

cap = cv2.VideoCapture(0)
ids_previos = set()

while True:
    ok, frame = cap.read()
    if not ok:
        break
    # percepcion del modelo
    # confidence = umbral minimo de confianza para detectar objetos
    # verbose = si es True, muestra informacion del modelo
    # con conf en 0.8 no me entregara la lectura ya que el suitcase reporta 0.60 max
    # agregamos persistencia
    results = model.track(frame,conf=0.3,verbose=False,persist=True,tracker="bytetrack.yaml") 
    boxes = results[0].boxes # detecciones del frame
    id_actuales = set()
    for box in boxes:
        nombre = model.names[int(box.cls[0].item())]          # id -> texto                                                     
        # if nombre !="suitcase": # si no es una maleta, que continue
        #     continue
        
        if box.id is None:
            continue

        track_id = int(box.id[0].item())      # NUEVO: id del tracker
        conf = float(box.conf[0].item())      # confianza 0..1
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        id_actuales.add(track_id)
        color = PALETA[track_id % len(PALETA)]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)                                                      
        cv2.putText(frame, f"ID {track_id} {conf:.2f}", (x1, y1 - 10),                                               
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        pies = ((x1 + x2) // 2, y2)  # punto de los pies
        cv2.circle(frame, pies, 8, (255, 0, 0), -1)

    # quien entro y quien salio vs. el frame anterior
    nuevos = id_actuales - ids_previos
    salidos = ids_previos - id_actuales
    
    if nuevos:
        print("Entraron: ", sorted(nuevos))
    if salidos:
        print("Salieron: ", sorted(salidos))
    ids_previos = id_actuales

    cv2.imshow("Paso 4 - Tracking", frame)
    
    if cv2.waitKey(1) & 0xFF == ord("s"):
        break

cap.release()
cv2.destroyAllWindows()
