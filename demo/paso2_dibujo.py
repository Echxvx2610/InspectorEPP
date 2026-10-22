import cv2
import time

cap = cv2.VideoCapture(0) # 0: webcam por defecto, 1: camara usb

#animar el rectangulo
x = 500 # variable para animacion

# calcular fps reales
t_prev = time.time()

while True:
    ok,frame = cap.read()
    ahora = time.time()
    fps_real = 1.0 / max(ahora - t_prev, 1e-6)
    t_prev = ahora
    if not ok:
        print("No se pudo leer el frame")
        break
    
    #frame = cv2.flip(frame, 1) # espejo
    alto, ancho = frame.shape[:2]
    x = x + 10 
    if x > ancho:
        x = 0
     # 1. dibujar rectangulo formato (x1,y1,x2,y2)
    x1,y1,x2,y2 = x,200,x + 300,500
    # rectangle(frame,coord,color,thickness)
    cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),-1) # -1 para rellenar las figuras
    # etiqueta para el rectangulo
    cv2.putText(frame,"dummy",(x1,y1 -10),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)
    # punto de los pies para determinar donde esta la persona
    pies = ((x1 + x2) // 2, y2)
    cv2.circle(frame,pies,8,(255,0,0),-1)

    # contador de frames
    #fps = cap.get(cv2.CAP_PROP_FPS) # obtener fps de la camara ( declarado por el driver de la camara)
    #print(fps)
    
    cv2.putText(frame,f"FPS: {fps_real:.0f}",(10,30), cv2.FONT_HERSHEY_PLAIN,1,(0,0,255),2)

    cv2.imshow("Paso 2 - dibujo", frame)
    if cv2.waitKey(1) & 0xFF == ord("s"):
        break 
    
cap.release() # libera la camara 
cv2.destroyAllWindows() # cierra todas las ventanas