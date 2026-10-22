import cv2

class CameraManager:
    def __init__(self, source=0):
        self.source = source
        self.cap = None

    def start(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise Exception(f"No se pudo abrir la cámara fuente: {self.source}")

    def read_frame(self):
        if self.cap is None:
            return False, None
        return self.cap.read()

    def stop(self):
        if self.cap:
            self.cap.release()
            
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
