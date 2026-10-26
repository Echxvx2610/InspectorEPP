import sys
import os

# La raíz del proyecto: imprescindible ANTES de importar src.* y para
# asegurar que `python main.py` funcione con cualquier CWD.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

import argparse
import cv2
import numpy as np

from src import paths

def run_gui():
    from PySide6.QtWidgets import QApplication
    from src.ui.app import MainWindow

    # Configuración de escalado para pantallas de alta densidad (HiDPI)
    app = QApplication(sys.argv)
    app.setApplicationName("Guardián EPP")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

def run_cli(args):
    import supervision as sv
    from src.camera import CameraManager
    from src.detector import PPEDetector
    from src.rule_engine import RuleEngine
    from src.alert_system import AlertSystem

    print(f"Iniciando Guardián de Seguridad (Modo CLI) - Zona: {args.zone}")

    detector = PPEDetector(model_path=str(paths.MODELS_DIR / "ppe_yolov8.pt"))
    rule_engine = RuleEngine(config_path=str(paths.RULES_PATH), zone=args.zone)
    alert_system = AlertSystem()

    cam_source = int(args.source) if args.source.isdigit() else args.source

    ZONE_POLYGON = np.array([
        [100, 100],
        [540, 100],
        [540, 380],
        [100, 380]
    ])

    polygon_zone = sv.PolygonZone(polygon=ZONE_POLYGON)
    zone_annotator = sv.PolygonZoneAnnotator(
        zone=polygon_zone, 
        color=sv.Color.ROSE, 
        thickness=2, 
        text_thickness=1, 
        text_scale=0.5
    )
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)

    with CameraManager(source=cam_source) as camera:
        print("Presiona 'q' para salir.")
        while True:
            ret, frame = camera.read_frame()
            if not ret:
                print("Error al capturar el frame.")
                break

            _, detected_classes_names, results = detector.detect(frame)
            detections = sv.Detections.from_ultralytics(results)
            is_inside_zone = polygon_zone.trigger(detections=detections)
            
            classes_in_zone = []
            for i, in_zone in enumerate(is_inside_zone):
                if in_zone:
                    class_id = detections.class_id[i]
                    class_name = results.names[class_id]
                    classes_in_zone.append(class_name)

            annotated_frame = box_annotator.annotate(scene=frame.copy(), detections=detections)
            annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections)
            annotated_frame = zone_annotator.annotate(scene=annotated_frame)

            if len(classes_in_zone) > 0:
                unique_classes = set(classes_in_zone)
                is_safe, alert_msg = rule_engine.evaluate(list(unique_classes))

                if not is_safe:
                    alert_system.trigger_alert(alert_msg)
                    cv2.putText(annotated_frame, "ALERTA EN ZONA DE RIESGO", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                else:
                    cv2.putText(annotated_frame, "Zona Segura", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(annotated_frame, "Zona Vacia", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow("Guardian EPP (CLI)", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()
    print("Sistema detenido correctamente.")

def main():
    parser = argparse.ArgumentParser(description="Guardián de Seguridad y EPP")
    parser.add_argument("--cli", action="store_true", help="Ejecutar en modo clásico de consola OpenCV")
    parser.add_argument("--zone", type=str, default="GENERAL", help="Zona activa en modo CLI (ej: SOLDADURA, LABORATORIO)")
    parser.add_argument("--source", type=str, default="0", help="Fuente de video (ej: 0, rtsp://...)")
    args, unknown = parser.parse_known_args()

    if args.cli:
        run_cli(args)
    else:
        run_gui()

if __name__ == "__main__":
    main()
