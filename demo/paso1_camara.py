import cv2

cap = cv2.VideoCapture(0) # 0: webcam por defecto, 1: camara usb

while True:
    ok,frame = cap.read()
    if not ok:
        print("No se pudo leer el frame")
        break
    
    # un frame es solo un array de Numpy ( alto, ancho, canales)
    print("dimensiones (alto, ancho, canales): ", frame.shape) # 1024x1280x3

    # lectura del frame
    #cv2.imshow("frame", frame) # mostrar el frame
    
    # mostra el centro del frame
    #cv2.imshow("centro del frame: ", frame[:600, 400:1100]) #frame(y1:y2, x1:x2) Y es vertical y X es horizontal
    
    #efecto espejo
    cv2.imshow("espejo", frame[:, ::-1])

    if cv2.waitKey(1) & 0xFF == ord("s"):
        break

cap.release() # libera la camara 
cv2.destroyAllWindows() # cierra todas las ventanas