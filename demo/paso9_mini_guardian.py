"""
Paso 9 — Mini-Guardián integrado (opcional)
===========================================
Une TODO el pipeline del proyecto en un solo archivo, con la misma
arquitectura neuro-simbólica:

    camara -> detectar + trackear -> asociar EPP -> zona por pies
           -> reglas -> FILTRO TEMPORAL -> alarma + evento (log)

Lección central de la integración: la PERCEPCIÓN (YOLO + geometría)
solo descubre HECHOS; el SÍMBOLO (reglas + temporalidad) decide qué
SIGNIFICAN. Si mañana cambia el modelo (COCO -> PPE entrenado), el lado
simbólico NO se toca: aquí se comprueba, porque el motor de reglas y el
filtro temporal son los MÓDULOS REALES de src/, no copias.

Dos modos según el modelo disponible:
  - models/ppe_best.pt (o ppe_yolov8.pt) existe -> EPP REAL del modelo
  - si no -> modo "concesión": las teclas 1-5 le REGALAN EPP sintético
    a TODAS las personas en su región anatómica (como paso 5). Sirve
    para probar reglas y filtro temporal sin entrenar nada.

Uso:
    python demo/paso9_mini_guardian.py                # cámara 0
    python demo/paso9_mini_guardian.py 1              # cámara 1
    python demo/paso9_mini_guardian.py video.mp4      # video
    python demo/paso9_mini_guardian.py --segundos 8   # (prueba) sale solo

Controles:
    1-5    conceder/quitar un EPP a todas las personas (modo sintético)
    z      activar/desactivar dibujo de zonas
    ENTER  cerrar el polígono (perfil: siguiente perfil con reglas)
    ESC    cancelar el polígono en trazo
    s      salir

Zonas: si config/zones.json tiene zonas para 'camara_N' (creadas en el
editor de la app) se usan; si no, dibujalas aquí con 'z'.

Referencias: src/ui/video_worker.py (pipeline real),
             src/zones.py, src/rule_engine.py, src/temporal.py,
             src/alert_system.py
"""

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

# módulos REALES del proyecto: la raíz debe estar en sys.path
BASE = Path(__file__).resolve().parent
PROYECTO = BASE.parent
if str(PROYECTO) not in sys.path:
    sys.path.insert(0, str(PROYECTO))

from src.rule_engine import RuleEngine          # noqa: E402
from src.temporal import TemporalFilter         # noqa: E402
from src.alert_system import AlertSystem        # noqa: E402

VENTANA = "Paso 9 - Mini-Guardian"
# centro relativo del EPP sintético dentro del bbox de la persona
# (regiones anatómicas: cabeza ~0.1, torso ~0.4, pies ~0.92)
REGION_CENTRO = {
    "helmet":       (0.5, 0.08),
    "welding_mask": (0.5, 0.12),
    "vest":         (0.5, 0.40),
    "gloves":       (0.35, 0.55),
    "boots":        (0.5, 0.92),
}
CLASES_TECLAS = ["helmet", "vest", "gloves", "boots", "welding_mask"]
TAM_EPP = 48           # lado del EPP sintético (px)
MIN_FRAMES_ALARM = 5   # N frames consecutivos para confirmar la alarma

BLANCO = (255, 255, 255)
VERDE = (0, 200, 0)
ROJO = (0, 0, 255)
GRIS = (160, 160, 160)
AMARILLO = (0, 220, 220)

# asociación: reutilizar la del paso 5 (los demose son librerías entre sí)
try:
    from paso5_asociacion import associate
except Exception as e:  # si se ejecuta fuera de demo/, ruta rara, etc.
    sys.exit(
        f"No puedo importar paso5_asociacion.py ({e}). "
        "Ejecuta: python demo/paso9_mini_guardian.py"
    )


# ---------------------------------------------------------------------------
# 1. Percepción: YOLO + ByteTrack (resumen educativo de los pasos 3-4)
# ---------------------------------------------------------------------------
def detectar(modelo, frame, clases_permitidas=None, conf=0.35):
    """Devuelve (persons, ppe_items) con IDs estables del tracker."""
    results = modelo.track(frame, persist=True, conf=conf,
                           classes=clases_permitidas,
                           tracker="bytetrack.yaml", verbose=False)
    persons, ppe_items = [], []
    for box in results[0].boxes:
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        nombre = modelo.names[int(box.cls[0].item())].lower()
        item = {
            "class": nombre,
            "bbox": [x1, y1, x2, y2],
            "conf": float(box.conf[0].item()),
        }
        if box.id is None:
            if nombre == "person":
                persons.append({"id": 0, "bbox": [x1, y1, x2, y2],
                                "conf": item["conf"]})
            continue
        if nombre == "person":
            item["id"] = int(box.id[0].item())
            persons.append(item)
        else:
            ppe_items.append(item)
    return persons, ppe_items


# ---------------------------------------------------------------------------
# 2. EPP sintético (modo sin modelo PPE): "concesiones" del usuario
# ---------------------------------------------------------------------------
def concesiones_sinteticas(persons, concedidas):
    """Crea la caja del EPP en la región anatómica de CADA persona para
    las clases concedidas (teclas 1-5). conf=1.0: la pone el humano."""
    items = []
    for p in persons:
        px1, py1, px2, py2 = p["bbox"]
        pw, ph = px2 - px1, py2 - py1
        for clase in concedidas:
            fx, fy = REGION_CENTRO[clase]
            cx, cy = int(px1 + fx * pw), int(py1 + fy * ph)
            h = TAM_EPP // 2
            items.append({
                "class": clase,
                "bbox": [cx - h, cy - h, cx + h, cy + h],
                "conf": 1.0,
            })
    return items


# ---------------------------------------------------------------------------
# 3. Geometría: zona por punto de los pies (paso 6 / ZoneManager)
# ---------------------------------------------------------------------------
def zona_de_punto(zonas, punto):
    """PRIMERA zona (orden del JSON) que contiene el punto, o None (R5)."""
    pt = (float(punto[0]), float(punto[1]))
    for z in zonas:
        if cv2.pointPolygonTest(z["poligono"], pt, False) >= 0:
            return z
    return None


def dibujar_zonas(vis, zonas, alpha=0.25):
    """Relleno tenue con addWeighted (una mezcla para todas) + borde."""
    if not zonas:
        return
    overlay = vis.copy()
    for z in zonas:
        cv2.fillPoly(overlay, [z["poligono"]], z["color"])
    cv2.addWeighted(overlay, alpha, vis, 1 - alpha, 0, vis)
    for z in zonas:
        cv2.polylines(vis, [z["poligono"]], True, z["color"], 2)
        x, y = z["poligono"][0]
        cv2.putText(vis, z["nombre"], (int(x) + 6, int(y) + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, z["color"], 2)


def cargar_zonas_de_config(src):
    """Lee las zonas de camara_N de config/zones.json (las de la app)."""
    cam_key = f"camara_{src}" if isinstance(src, int) else "camara_0"
    ruta = PROYECTO / "config" / "zones.json"
    zonas = []
    if ruta.exists():
        try:
            datos = json.load(open(ruta, encoding="utf-8"))
            for z in datos.get(cam_key, []):
                if len(z.get("poligono", [])) >= 3:
                    zonas.append({
                        "nombre": z.get("nombre", "Zona"),
                        "perfil": (z.get("perfil") or "").upper(),
                        "color": (60, 210, 80),
                        "poligono": np.array(z["poligono"], np.int32),
                    })
        except Exception as e:
            print(f"Aviso: no pude leer zones.json: {e}")
    print(f"Zonas de {cam_key}: "
          f"{[z['nombre'] for z in zonas]}")
    if not zonas:
        print("  (ninguna: todo evaluara FUERA/R5 hasta dibujar con 'z')")
    return zonas


# ---------------------------------------------------------------------------
# 4. Programa principal
# ---------------------------------------------------------------------------
def abrir_fuente(src):
    """Misma secuencia que src/ui/video_worker._open_capture: en Windows
    hay que probar CAP_DSHOW primero — con el backend default algunas
    webcams no abren por indice y dan 'Camera index out of range'."""
    if isinstance(src, int) or (isinstance(src, str) and src.isdigit()):
        cap = cv2.VideoCapture(int(src), cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(int(src))
        return cap
    return cv2.VideoCapture(str(src))


def main():
    args = sys.argv[1:]
    # --segundos N: para pruebas automáticas; sale a los N segundos
    segundos = None
    if "--segundos" in args:
        i = args.index("--segundos")
        segundos = float(args[i + 1]) if i + 1 < len(args) else 8.0
        args = args[:i] + args[i + 2:]
    fuente = args[0] if args else "0"
    src = int(fuente) if fuente.isdigit() else fuente

    # ── modelo: PPE del proyecto primero; si no, COCO + concesiones ──
    candidatos = [
        PROYECTO / "models" / "ppe_best.pt",
        PROYECTO / "models" / "ppe_yolov8.pt",
        BASE / "yolov8n.pt",
        PROYECTO / "yolov8n.pt",
    ]
    ruta_modelo = next((r for r in candidatos if r.exists()),
                       "yolov8n.pt")
    modo_real = Path(str(ruta_modelo)).name.startswith("ppe_")
    modelo = YOLO(str(ruta_modelo))
    print(f"Modelo: {ruta_modelo} -> "
          f"{'EPP REAL' if modo_real else 'COCO: teclas 1-5 conceden EPP'}")

    # ── el lado SIMBÓLICO es el de VERDAD (módulos reales de src/) ──
    def construir_simbolico():
        reglas = RuleEngine(
            config_path=str(PROYECTO / "config" / "rules.json"))
        temporal = TemporalFilter(grace_period_sec=1.0,
                                  min_consecutive_frames=MIN_FRAMES_ALARM)
        return reglas, temporal, set()  # logueados: eventos por racha

    reglas, temporal, logueados = construir_simbolico()
    alertas = AlertSystem()   # voz con cooldown de 4 s
    eventos = []              # log auditable en memoria

    perfiles_con_reglas = [
        r for r in reglas.rules if reglas.rules[r].get("requeridos")
    ]
    print(f"Perfiles con EPP exigido: "
          f"{perfiles_con_reglas or ['NINGUNA — revisa rules.json']}")

    zonas = cargar_zonas_de_config(src)
    perfiles_para_dibujo = list(reglas.rules) or ["GENERAL"]

    # ── estado de la sesion ──
    concedidas = set()    # EPP sintético activo (1-5)
    modo_dibujo = False
    dibujando = []        # vertices del polígono en trazo
    idx_perfil = 0        # próximo perfil al cerrar un polígono
    firma_previa = None   # anti-spam de consola

    def on_mouse(event, x, y, flags, param):
        # solo agrega vértices si el modo dibujo está activo
        if modo_dibujo and event == cv2.EVENT_LBUTTONDOWN:
            dibujando.append((x, y))

    cap = None
    for intento in range(10):
        cap = abrir_fuente(src)
        if cap and cap.isOpened():
            print(f"Fuente abierta al intento {intento + 1}.")
            break
        # las webcams (DSHOW) tardan en levantar: reintentar con paciencia
        time.sleep(1.0)

    # FOTO como respaldo (igual que el paso 5): si no hay camara, se
    # procesa demo/foto_base.jpg en loop. Sirve para probar zonas/reglas
    # temporal y alertas SIN hardware.
    foto_estatica = None
    if cap is None or not cap.isOpened():
        ruta_foto = BASE / "foto_base.jpg"
        if not ruta_foto.exists():
            sys.exit(
                f"No hay camara ni foto de respaldo ({ruta_foto}).\n"
                "Pasa una foto o video como argumento:\n"
                "  python demo/paso9_mini_guardian.py video.mp4"
            )
        datos = np.fromfile(str(ruta_foto), dtype=np.uint8)
        foto_estatica = cv2.imdecode(datos, cv2.IMREAD_COLOR)
        if foto_estatica is None:
            sys.exit("No pude leer la foto de respaldo.")
        print(f"Sin camara: fuente estatica = {ruta_foto.name} "
              "(el tracker mantiene IDs sobre una imagen fija).")
        cap = None

    cv2.namedWindow(VENTANA)
    cv2.setMouseCallback(VENTANA, on_mouse)

    t_inicio = time.time()
    while True:
        if segundos and time.time() - t_inicio > segundos:
            print("Tiempo de prueba agotado (--segundos). Saliendo.")
            break
        if foto_estatica is not None:
            # fuente estatica: el mismo frame vuelve en cada iteracion
            frame = foto_estatica.copy()
        else:
            ok, frame = cap.read()
            if not ok:
                if isinstance(src, str):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # video: loop
                    ok, frame = cap.read()
                    if not ok:
                        break
                else:
                    cap.release()
                    cap = abrir_fuente(src)  # camara: reintentar
                    continue

        # 1) percepción: detectar + trackear
        persons, ppe_items = detectar(
            modelo, frame,
            clases_permitidas=None if modo_real else [0],  # COCO: personas
        )
        # 2) EPP: real del modelo, o sintético según concesiones
        if not modo_real:
            ppe_items += concesiones_sinteticas(persons, concedidas)
        # 3) asociación persona <-> EPP (paso 5)
        associations, _orphans = associate(persons, ppe_items)

        vis = frame.copy()
        dibujar_zonas(vis, zonas)
        lineas = []

        # 4) por persona: zona por pies -> reglas -> temporal
        for p in persons:
            x1, y1, x2, y2 = p["bbox"]
            pies = ((x1 + x2) // 2, y2)
            zona = zona_de_punto(zonas, pies)
            perfil = zona["perfil"] if zona else None
            zona_nombre = zona["nombre"] if zona else "FUERA"

            present_ppe = associations.get(p["id"], {}).get("present_ppe", [])
            res = reglas.evaluate_person(present_ppe, perfil, zona_nombre)
            # 5) filtro temporal: la alarma SOLO se confirma tras N frames
            alarma = temporal.update(p["id"], not res["is_safe"])

            color = VERDE if res["is_safe"] else ROJO
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cv2.circle(vis, pies, 6,
                       zona["color"] if zona else GRIS, -1)
            estado = "OK" if res["is_safe"] else (
                f"FALTA {','.join(res['missing'])}"
                + ("  ALERTA" if alarma else " (contando...)"))
            cv2.putText(vis, f"#{p['id']} {zona_nombre}: {estado}",
                        (x1, max(18, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            lineas.append(f"#{p['id']} @{zona_nombre}"
                          f"[{perfil or 'R5'}] {estado}")

            # 6) evento auditable + alerta hablada, UNA vez por racha
            if alarma and (p["id"], zona_nombre) not in logueados:
                logueados.add((p["id"], zona_nombre))
                ts = time.strftime("%H:%M:%S")
                evento = (f"{ts} | #{p['id']} | {zona_nombre} | "
                          f"{res['explanation']} | rule={res['rule_code']}")
                eventos.append(evento)
                alertas.trigger_alert(
                    f"Infracción en {zona_nombre}. {res['explanation']}"
                )
                print(f"  [EVENTO] {evento}")
            if res["is_safe"]:
                logueados.discard((p["id"], zona_nombre))

        # polígono en construcción (modo z)
        if modo_dibujo:
            for pt in dibujando:
                cv2.circle(vis, pt, 4, AMARILLO, -1)
            for a, b in zip(dibujando, dibujando[1:]):
                cv2.line(vis, a, b, AMARILLO, 2)
            if dibujando:
                perfil_sig = perfiles_para_dibujo[
                    idx_perfil % len(perfiles_para_dibujo)]
                cv2.putText(vis, f"siguiente perfil: {perfil_sig}",
                            (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 220, 220), 1)

        # barra de ayuda superior (sin f-strings multilínea: Python 3.11)
        if modo_dibujo:
            estado_epp = "DIBUJANDO"
        else:
            estado_epp = "EPP: " + (','.join(sorted(concedidas)) or 'nada')
        ayuda = (f"{estado_epp}   personas: {len(persons)}   "
                 "[1-5] EPP  [z] zona  [ENTER] cerrar  [s] salir")
        cv2.rectangle(vis, (0, 0), (vis.shape[1], 30), (30, 30, 30), -1)
        cv2.putText(vis, ayuda, (10, 21),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLANCO, 1)

        # consola sin spam: solo cuando cambia el resumen
        firma = " | ".join(lineas)
        if firma != firma_previa and lineas:
            print(firma)
            firma_previa = firma

        cv2.imshow(VENTANA, vis)
        tecla = cv2.waitKey(30) & 0xFF

        if tecla == ord("s"):
            break
        elif 0x31 <= tecla <= 0x35 and not modo_real:
            clase = CLASES_TECLAS[tecla - ord("1")]
            concedidas ^= {clase}   # toggle
            print(f"EPP concedido a todos: {sorted(concedidas) or '(nada)'}")
            # nuevo escenario: el filtro temporal y los eventos reinician
            reglas, temporal, logueados = construir_simbolico()
        elif tecla == ord("z"):
            modo_dibujo = not modo_dibujo
            dibujando.clear()
        elif tecla == 27:  # ESC: cancelar trazo
            dibujando.clear()
        elif tecla in (13, 10) and dibujando:  # ENTER: cerrar polígono
            if len(dibujando) >= 3 and perfiles_para_dibujo:
                perfil = perfiles_para_dibujo[
                    idx_perfil % len(perfiles_para_dibujo)]
                idx_perfil += 1
                zonas.append({
                    "nombre": perfil.title(),   # demo temporal de sesion
                    "perfil": perfil.upper(),   # mismo id de rules.json
                    "color": (60, 210, 80),
                    "poligono": np.array(dibujando, np.int32),
                })
                print(f"Zona '{perfil.title()}' listada con "
                      f"{len(dibujando)} vértices (perfil {perfil}).")
            dibujando.clear()

        if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:
            break

    # ── log auditable de la sesión a archivo ──
    if eventos:
        ruta_log = BASE / "eventos_demo.log"
        with open(ruta_log, "a", encoding="utf-8") as f:
            f.write("\n".join(eventos) + "\n")
        print(f"\nLog de eventos guardado en {ruta_log}")

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
