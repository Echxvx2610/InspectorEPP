import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
print("Clases: ", model.names)

cap = cv2.VideoCapture(0)
while True:
    ok, frame = cap.read()
    if not ok:
        break
    # percepcion del modelo
    # confidence = umbral minimo de confianza para detectar objetos
    # verbose = si es True, muestra informacion del modelo
    results = model(frame,conf=0.5,verbose=False) # con conf en 0.8 no me entregara la lectura ya que el suitcase reporta 0.60 max
    boxes = results[0].boxes # detecciones del frame
    cls = results[0].names   
    for box in boxes:
        cls_id = int(box.cls[0].item())       # id de la clase
        conf = float(box.conf[0].item())      # confianza 0..1
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        nombre = model.names[cls_id]          # id -> texto                                                     
        if nombre !="suitcase": # si no es una maleta, que continue
            continue
        
        color = (0, 255, 0)                                               
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)                                                      
        cv2.putText(frame, f"{nombre} {conf:.2f}", (x1, y1 - 10),                                               
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        pies = ((x1 + x2) // 2, y2)  # punto de los pies
        cv2.circle(frame, pies, 8, (255, 0, 0), -1)
    cv2.imshow("Paso 3 - YOLO", frame)
    
    if cv2.waitKey(1) & 0xFF == ord("s"):
        break

cap.release()
cv2.destroyAllWindows()
