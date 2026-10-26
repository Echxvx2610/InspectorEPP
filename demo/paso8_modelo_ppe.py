"""
Paso 8 — Modelo PPE real (Roboflow -> fine-tuning)
==================================================
Objetivo: pasar de COCO generico (persona, marco, maleta...) a las clases
del negocio: helmet, vest, welding_mask, gloves, boots...

Este script hace la parte LOCAL y verificable del paso:
  1. elige modelo: el PPE del proyecto (models/ppe_best.pt) si existe,
     si no el COCO de siempre (yolov8n.pt) para comparar contraste
  2. detecta en una FOTO (o video/camara) y muestra clase + confianza
  3. VERIFICA EL CONTRATO DE CLASES (la leccion mas importante del proye-
     to): los nombres de clase del modelo, classes.json y rules.json
     deben cuadrar EXACTOS. Si el modelo no conoce 'welding_mask', la
     regla R1 de SOLDADURA NUNCA se va a disparar, aunque el codigo
     este perfecto. Nada de 'casco' vs 'helmet': todo en ingles.

Uso:
    python demo/paso8_modelo_ppe.py              # foto de la carpeta demo
    python demo/paso8_modelo_ppe.py 0            # camara
    python demo/paso8_modelo_ppe.py video.mp4
    python demo/paso8_modelo_ppe.py --check      # solo el reporte del con-
                                                 # trato de clases, sin GUI

Controles (con video/camara): s o cerrar ventana para salir.

Como CONSEGUIR el modelo (fuera de este script, resumen del README):
  Roboflow Universe -> dataset PPE con licencia permisiva -> export en
  formato YOLOv8 (data.yaml con train/valid/test) -> Colab:

      from ultralytics import YOLO
      model = YOLO("yolov8s.pt")
      model.train(data="training/data.yaml", epochs=100, imgsz=640)

  -> los pesos quedan en runs/detect/train/weights/best.pt. Copiarlos a
     models/ppe_best.pt: el detector real (src/detector.py) los busca
     automaticamente.
  - Nota licencia: YOLOv8 es AGPL-3.0; para vender el sistema, revisar
    licencias cada dataset y la seccion de licencia del README.md.
"""

import sys
from pathlib import Path
import json

import cv2
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent
PROYECTO = BASE.parent
VENTANA = "Paso 8 - Modelo PPE"

PPE_CLASES = ["helmet", "vest", "mask", "glasses", "gloves",
              "welding_mask", "boots"]


# ---------------------------------------------------------------------------
# 1. Eleccion de modelo: PPE del proyecto primero, COCO despues
# ---------------------------------------------------------------------------
def elegir_modelo(ruta_arg=None):
    """Prioridad igual que src/detector.py:
    models/ppe_*.pt del proyecto -> yolov8n.pt (COCO)."""
    candidatos = []
    if ruta_arg:
        candidatos.append(Path(ruta_arg))
    candidatos += [
        PROYECTO / "models" / "ppe_best.pt",
        PROYECTO / "models" / "ppe_yolov8.pt",
        BASE / "yolov8n.pt",           # COCO (copia del demo)
        Path("yolov8n.pt"),
    ]
    for c in candidatos:
        if c and Path(c).exists():
            return Path(c)
    # ultimo recurso: ultralytics descarga yolov8n.pt automaticamente
    return Path("yolov8n.pt")


def abrir(ruta_int):
    """Carga defensiva: si el modelo no abre, se sabe aqui."""
    try:
        m = YOLO(str(ruta_int))
    except Exception as e:
        sys.exit(f"El modelo {ruta_int} no se pudo cargar: {e}")
    print(f"Modelo cargado: {ruta_int}")
    print(f"Clases conocidas ({len(m.names)}): "
          f"{sorted(set(m.names.values()))}\n")
    return m


# ---------------------------------------------------------------------------
# 2. EL CHEQUEO DEL CONTRATO — lo que se olvida en produccion
# ---------------------------------------------------------------------------
def chequear_contrato(modelo, classes_json, rules_json):
    """
    Compara TRES fuentes y reporta desajustes:
      a. model.names (lo que realmente detecta el .pt)
      b. classes.json (id de clase -> texto en espanol para la UI)
      c. rules.json  (que clases exige cada perfil para pasar)
    Si una clase exigida por una regla NO existe en el modelo, esa regla
    es IMPOSIBLE de activar: nunca se dispara, aunque el codigo este
    perfecto. Ni 'casco' vs 'helmet': el contrato es capricioso con un
    solo caracter.
    """
    nombres = {v.lower() for v in modelo.names.values()}
    print("=" * 62)
    print(" CONTRATO DE CLASES (model.names <-> classes.json <-> rules.json)")
    print("=" * 62)
    print(f" clases del modelo : {sorted(nombres)}")

    cj = []
    if classes_json.exists():
        cj = [k.lower() for k in json.load(open(classes_json, encoding="utf-8"))]
    fk = []
    if rules_json.exists():
        reglas = json.load(open(rules_json, encoding="utf-8"))
        fk = sorted({r.lower()
                     for v in reglas.values()
                     for r in v.get("requeridos", [])})
    print(f" classes.json      : {cj or '(archivo vacio o falta)'}")
    print(f" requeridos (reglas): {fk or '(ninguno definido)'}")

    problemas = []
    if not cj:
        problemas.append("classes.json no existe o no se pudo leer.")
    if not fk:
        problemas.append("Ningun perfil exige EPP (requeridos vacios): el "
                         "sistema esta SIEMPRE CONFORME. Revisa rules.json.")
    for req in fk:
        if nombres and req not in nombres:
            problemas.append(
                f"La regla exige '{req}' y el modelo NO sabe detectarlo: "
                "esa regla nunca se disparara."
            )
    if cj and nombres:
        sin_uso = [c for c in cj if c != "person" and c not in nombres]
        if sin_uso:
            problemas.append(
                f"classes.json anuncia {sin_uso} y el modelo no tiene"
                " esas clases: la UI mostrara etiquetas muertas."
            )
    if problemas:
        print("\n DESAJUSTES:")
        for p in problemas:
            print(f"   - {p}")
    else:
        print("\n Todo cuadra: el contrato de clases esta firme.")
    print("=" * 62 + "\n")


# ---------------------------------------------------------------------------
# 3. Programa principal
# ---------------------------------------------------------------------------
def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    solo_check = "--check" in sys.argv

    model_path = elegir_modelo(
        args[0] if args and args[0].endswith(".pt") else None
    )
    modelo = abrir(model_path)
    chequear_contrato(modelo, PROYECTO / "config" / "classes.json",
                      PROYECTO / "config" / "rules.json")
    if solo_check:
        return

    # fuente: foto -> video -> camara
    fuente = next((a for a in args if not a.endswith(".pt")), None)
    if fuente is None:
        foto = BASE / "foto_base.jpg"
        if foto.exists():
            fuente = str(foto)
        else:
            fuente = "0"  # sin foto y sin args: caen a la camara

    if fuente.isdigit() or cv2.haveImageReader(fuente) is False:
        # camara o loop de video
        src = int(fuente) if fuente.isdigit() else fuente
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            sys.exit(f"No pude abrir la fuente: {fuente}")
        while True:
            ok, frame = cap.read()
            if not ok:
                if not fuente.isdigit():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop del video
                    continue
                break
            results = modelo(frame, conf=0.3, verbose=False)
            frame = results[0].plot()   # cajas/labels hechos por YOLO
            for box in results[0].boxes:
                cls = modelo.names[int(box.cls[0].item())]
                conf = float(box.conf[0].item())
                print(f"{cls:14} {conf:.2f}")
            cv2.imshow(VENTANA, frame)
            if (cv2.waitKey(1) & 0xFF == ord("s")
                    or cv2.getWindowProperty(VENTANA,
                                             cv2.WND_PROP_VISIBLE) < 1):
                break
        cap.release()
    else:
        # foto estatica: una sola inferencia y se imprime TODO
        data = open(fuente, "rb").read()
        import numpy as np
        img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8),
                           cv2.IMREAD_COLOR)
        if img is None:
            sys.exit(f"No pude leer la imagen: {fuente}")
        results = modelo(img, conf=0.3, verbose=False)
        annotated = results[0].plot()
        for box in results[0].boxes:
            cls = modelo.names[int(box.cls[0].item())]
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            print(f"{cls:14} {conf:.2f}   bbox=({x1},{y1},{x2},{y2})")
        if not len(results[0].boxes):
            print("(no encontro nada por encima de conf=0.3)")
        cv2.imshow(VENTANA, annotated)
        cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
