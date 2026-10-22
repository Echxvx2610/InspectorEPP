import pyttsx3
import threading
import time

class AlertSystem:
    def __init__(self):
        self.engine = None
        try:
            self.engine = pyttsx3.init()
        except Exception as e:
            print(f"Aviso TTS: No se pudo inicializar motor de voz: {e}")
        self.is_speaking = False
        self.last_alert_time = 0
        self.cooldown = 4.0 # Segundos entre alertas repetidas

    def _speak(self, message):
        if not self.engine:
            return
        try:
            self.is_speaking = True
            self.engine.say(message)
            self.engine.runAndWait()
        except Exception:
            pass
        finally:
            self.is_speaking = False

    def trigger_alert(self, message):
        """
        Lanza la alerta en un hilo separado para no bloquear el procesamiento de video.
        Aplica un cooldown para evitar que repita el mismo mensaje sin parar.
        """
        current_time = time.time()
        
        # Evitar sobreposición y spam de voz
        if not self.is_speaking and (current_time - self.last_alert_time > self.cooldown):
            self.last_alert_time = current_time
            print(f"ALERTA: {message}")
            threading.Thread(target=self._speak, args=(message,), daemon=True).start()
