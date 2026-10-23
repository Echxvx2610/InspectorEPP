"""
Paso 5 — Asociacion persona <-> EPP (geometria)
===============================================
Objetivo: saber DE QUIEN es cada EPP, sin depender de que el modelo lo
detecte (COCO no conoce helmet/vest).

La idea clave del paso: los EPP se colocan con el mouse (cajas SINTETICAS)
sobre una FOTO ESTATICA. Las personas si las detecta YOLO (clase "person"),
con IDs manuales asignados por orden izquierda -> derecha.

Por que una foto y no video/camara:
  - El tracking (paso 4) necesita tiempo: los IDs estables existen ENTRE
    frames. En una imagen estatica no hay dimension temporal.
  - La asociacion solo necesita {id, bbox} de personas y {class, bbox} de
    EPPs; le da igual de donde vengan. Percepcion y razonamiento geometrico
    estan desacoplados (igual que en el Guardian real).

Uso:
    python demo/paso5_asociacion.py ruta/foto.jpg
    python demo/paso5_asociacion.py          # usa demo/foto_base.jpg;
                                             # si no existe, captura UN frame
                                             # de la webcam y lo guarda

Controles:
    1-5       elegir clase de EPP (helmet, vest, gloves, boots, welding_mask)
    clic izq  colocar el EPP seleccionado
    clic der  borrar el ultimo EPP
    c         limpiar todos los EPP
    s         salir

RETO (GUIA): coloca un EPP en un punto donde DOS personas compitan
(el centro dentro de ambas cajas y en la franja correcta de ambas).
Ganara la de MENOR AREA. Es exactamente el criterio de src/association.py.

Referencia: src/association.py (REGION_MAPPING, PPEAssociator.associate)
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent  # carpeta demo/ (rutas validas desde cualquier CWD)
VENTANA = "Paso 5 - Asociacion persona <-> EPP"

# ---------------------------------------------------------------------------
# 1. REGION_MAPPING — franja vertical donde se ESPERA cada clase de EPP.
#    rel_y: 0.0 = cabeza, 1.0 = pies. Copia educativa de src/association.py.
#    (El demo usa 5 clases con las teclas 1-5; mask y glasses quedan fuera.)
# ---------------------------------------------------------------------------
REGION_MAPPING = {
    # Tercio superior: cabeza y rostro
    "helmet": (0.0, 0.40),
    "welding_mask": (0.0, 0.45),
    "mask": (0.05, 0.45),
    "glasses": (0.05, 0.35),

    # Zona media: torso y extremidades superiores
    "vest": (0.15, 0.75),
    "gloves": (0.35, 0.85),

    # Tercio inferior: pies y piernas
    "boots": (0.65, 1.05),
}

CLASES_TECLAS = ["helmet", "vest", "gloves", "boots", "welding_mask"]
TAM_EPP = 56       # lado de la caja sintetica del EPP (px)
MARGEN_X = 0.15    # tolerancia horizontal: 15% del ancho de la persona

# colores BGR (¡no RGB!)
VERDE = (0, 200, 0)
ROJO = (0, 0, 255)
AMARILLO = (0, 220, 220)
BLANCO = (255, 255, 255)
AZUL = (255, 0, 0)
FONDO = (30, 30, 30)


# ---------------------------------------------------------------------------
# 2. EL ASOCIADOR — version propia y comentada del PPEAssociator.real
# ---------------------------------------------------------------------------
def associate(persons, ppe_items, region_mapping=REGION_MAPPING):
    """
    Asocia cada EPP a la persona cuyo bbox lo "contiene".

    Para cada EPP:
      1. se reduce a su CENTRO (cx, cy): el resto de la caja no importa
      2. es candidato de una persona si:
         - el centro cae dentro de su caja (con margen horizontal MARGEN_X)
         - rel_y = (cy - py1) / ph cae dentro de la franja de su clase
      3. si varias personas son candidatas -> gana la de MENOR AREA
         (caja mas pequena = persona mas cerca de la camara / al frente)

    Args:
        persons:   [{'id': int, 'bbox': [x1, y1, x2, y2], 'conf': float}]
        ppe_items: [{'class': str, 'bbox': [x1, y1, x2, y2], 'conf': float}]

    Returns:
        (associations, orphans)
        associations: {id: {'present_ppe': [clases...], 'items': [dicts...]}}
        orphans:      lista de EPPs que no pertenecen a nadie (rojos)
    """
    associations = {
        p["id"]: {"present_ppe": set(), "items": []}
        for p in persons
    }
    orphans = []

    for item in ppe_items:
        item_cls = item["class"].lower()
        ix1, iy1, ix2, iy2 = item["bbox"]
        cx = (ix1 + ix2) / 2.0
        cy = (iy1 + iy2) / 2.0

        best_person_id = None
        best_area = float("inf")

        for person in persons:
            px1, py1, px2, py2 = person["bbox"]
            pw = px2 - px1
            ph = py2 - py1
            if pw <= 0 or ph <= 0:
                continue

            # 1) contencion horizontal con margen (el brazo con guante puede
            #    salirse un poco de la caja) y vertical estricta
            margen = pw * MARGEN_X
            if not ((px1 - margen) <= cx <= (px2 + margen) and py1 <= cy <= py2):
                continue

            # 2) region anatomica vertical esperada para esa clase
            reg_min, reg_max = region_mapping.get(item_cls, (0.0, 1.0))
            rel_y = (cy - py1) / ph  # 0.0 arriba (cabeza) -> 1.0 abajo (pies)
            if not (reg_min <= rel_y <= reg_max):
                continue

            # 3) desempate: si dos personas compiten, gana la de menor area
            area = pw * ph
            if area < best_area:
                best_area = area
                best_person_id = person["id"]

        if best_person_id is not None:
            associations[best_person_id]["present_ppe"].add(item_cls)
            associations[best_person_id]["items"].append(item)
        else:
            orphans.append(item)

    # los sets se convierten a listas ordenadas para poder comparar/imprimir
    for pid in associations:
        associations[pid]["present_ppe"] = sorted(associations[pid]["present_ppe"])

    return associations, orphans


# ---------------------------------------------------------------------------
# 3. Carga de imagen y deteccion de personas
# ---------------------------------------------------------------------------
def cargar_imagen():
    """Devuelve (img, ruta). Orden: argumento -> foto_base.jpg -> webcam 1 frame."""
    if len(sys.argv) > 1:
        ruta = Path(sys.argv[1])
        if not ruta.exists():
            sys.exit(f"No existe la imagen: {ruta}")
        return decodificar(ruta), ruta

    ruta = BASE / "foto_base.jpg"
    if ruta.exists():
        print(f"Usando foto guardada: {ruta.name} (bórrala para recapturar)")
        return decodificar(ruta), ruta

    # fallback: usar la webcam UNA sola vez y guardar el frame
    print("No hay imagen: capturando 1 frame de la webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("No hay imagen ni camara. Pasa una foto: "
                 "python demo/paso5_asociacion.py mi_foto.jpg")
    ok, frame = cap.read()
    for _ in range(10):  # las primeras frames suelen salir oscuras
        ok, frame = cap.read()
    cap.release()
    if not ok:
        sys.exit("La camara no entrego ningun frame.")
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        sys.exit("No pude codificar el frame como JPG.")
    buf.tofile(str(ruta))  # guardar sin problemas de unicode en Windows
    print(f"Foto guardada en {ruta}")
    return frame, ruta


def decodificar(ruta):
    """cv2.imread falla con rutas con acentos/esparias en Windows;
    leemos los bytes y decodificamos manualmente (truco habitual)."""
    data = np.fromfile(str(ruta), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"No pude leer la imagen: {ruta}")
    return img


def detectar_personas(model, img, conf=0.6):
    """YOLO detecta SOLO la clase 'person' (id 0 en COCO).
    El id 'de verdad' lo daria el tracker (paso 4); aqui lo asignamos por
    posicion: ordenados de izquierda a derecha -> ID 1, 2, ... En una foto
    el orden no cambia nunca, asi que el id es estable por definicion."""
    results = model(img, conf=conf, classes=[0], verbose=False)
    persons = []
    for box in results[0].boxes:
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        persons.append({
            "id": 0,  # temporal, se reasigna abajo
            "bbox": [x1, y1, x2, y2],
            "conf": float(box.conf[0].item()),
        })
    persons.sort(key=lambda p: p["bbox"][0])
    for i, p in enumerate(persons, start=1):
        p["id"] = i
    return persons


# ---------------------------------------------------------------------------
# 4. Dibujo
# ---------------------------------------------------------------------------
def dibujar_ayuda(vis, clase_idx, n_items):
    """Barra superior con la clase seleccionada y los controles."""
    clase = CLASES_TECLAS[clase_idx]
    cv2.rectangle(vis, (0, 0), (vis.shape[1], 34), FONDO, -1)
    texto = (f"[1-5] clase: {clase}   [clic izq] colocar ({n_items})   "
             f"[clic der] borrar   [c] limpiar   [s] salir")
    cv2.putText(vis, texto, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLANCO, 1)


def dibujar_bandas(vis, persons, clase_idx):
    """Dibuja la franja vertical DONDE SE ESPERA la clase seleccionada.
    Asi se 've' el REGION_MAPPING antes de colocar el EPP."""
    clase = CLASES_TECLAS[clase_idx]
    reg_min, reg_max = REGION_MAPPING[clase]
    for p in persons:
        px1, py1, px2, py2 = p["bbox"]
        ph = py2 - py1
        for frac in (reg_min, reg_max):
            y = int(py1 + frac * ph)
            cv2.line(vis, (px1, y), (px2, y), AMARILLO, 1)
    cv2.putText(vis, f"franja de '{clase}': rel_y {reg_min}-{reg_max}",
                (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, AMARILLO, 1)


def dibujar_personas(vis, persons):
    for p in persons:
        x1, y1, x2, y2 = p["bbox"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), BLANCO, 2)
        cv2.putText(vis, f"ID {p['id']}", (x1 + 4, y1 + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, BLANCO, 2)
        pies = ((x1 + x2) // 2, y2)  # el punto que usa el paso 6 para las zonas
        cv2.circle(vis, pies, 6, AZUL, -1)


def dibujar_epps(vis, associations, orphans):
    """Verde = asociado (con etiqueta de dueno). Rojo = huerfano.
    El puntito marca el CENTRO del EPP: es lo unico que mira el algoritmo."""
    for pid, info in associations.items():
        for item in info["items"]:
            x1, y1, x2, y2 = item["bbox"]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.rectangle(vis, (x1, y1), (x2, y2), VERDE, 2)
            cv2.circle(vis, (cx, cy), 3, VERDE, -1)
            cv2.putText(vis, f"{item['class']} -> ID {pid}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, VERDE, 2)
    for item in orphans:
        x1, y1, x2, y2 = item["bbox"]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.rectangle(vis, (x1, y1), (x2, y2), ROJO, 2)
        cv2.circle(vis, (cx, cy), 3, ROJO, -1)
        cv2.putText(vis, f"{item['class']} HUERFANO", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, ROJO, 2)


def resumen(associations, orphans):
    """Firma de texto del veredicto actual; se imprime solo cuando cambia."""
    partes = []
    for pid in sorted(associations):
        ppe = associations[pid]["present_ppe"]
        partes.append(f"ID {pid}: {', '.join(ppe) if ppe else '(sin EPP)'}")
    if orphans:
        clases = sorted(i["class"] for i in orphans)
        partes.append(f"HUERFANOS: {len(orphans)} {clases}")
    else:
        partes.append("HUERFANOS: 0")
    return " | ".join(partes)


# ---------------------------------------------------------------------------
# 5. Programa principal
# ---------------------------------------------------------------------------
def main():
    img, ruta = cargar_imagen()

    # pantalla comoda: maximo 1280 px de ancho (mantiene el aspecto)
    h, w = img.shape[:2]
    if w > 1280:
        escala = 1280 / w
        img = cv2.resize(img, (1280, int(h * escala)))

    img_base = img.copy()  # original intocable; cada frame se redibuja encima

    # yolov8n.pt vive en demo/ y en la raiz; usar el primero que exista
    modelo_path = BASE / "yolov8s.pt"
    if not modelo_path.exists():
        modelo_path = Path("yolov8s.pt")
    model = YOLO(str(modelo_path))

    #persons = detectar_personas(model, img)
    # crear una lista de personas hardcodeada para pruebas
    persons = [
        {"id": 1, "bbox": [151, 205, 226, 373], "conf": 0.89},
        {"id": 2, "bbox": [170, 200, 250, 370], "conf": 0.82},
    ]
    if not persons:
        sys.exit("YOLO no encontro personas en la foto. Prueba con otra imagen.")

    print("\nPersonas detectadas (de izquierda a derecha):")
    for p in persons:
        x1, y1, x2, y2 = p["bbox"]
        area = (x2 - x1) * (y2 - y1)
        print(f"  ID {p['id']}: bbox={p['bbox']}  area={area}  conf={p['conf']:.2f}")
    print("Si dos personas compiten por un EPP, gana la de MENOR area.\n")

    # estado compartido con el mouse: clase elegida + EPPs colocados
    estado = {"clase_idx": 0, "items": []}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            h = TAM_EPP // 2
            clase = CLASES_TECLAS[estado["clase_idx"]]
            estado["items"].append({
                "class": clase,
                "bbox": [x - h, y - h, x + h, y + h],
                "conf": 1.0,  # EPP sintetico: confianza total, la pone el humano
            })
        elif event == cv2.EVENT_RBUTTONDOWN and estado["items"]:
            estado["items"].pop()

    cv2.namedWindow(VENTANA)
    cv2.setMouseCallback(VENTANA, on_mouse)

    firma_previa = None
    while True:
        vis = img_base.copy()

        associations, orphans = associate(persons, estado["items"])

        dibujar_bandas(vis, persons, estado["clase_idx"])
        dibujar_personas(vis, persons)
        dibujar_epps(vis, associations, orphans)
        dibujar_ayuda(vis, estado["clase_idx"], len(estado["items"]))

        # imprimir solo cuando cambia el veredicto (evitar spam en consola)
        firma = resumen(associations, orphans)
        if firma != firma_previa:
            print(firma)
            firma_previa = firma

        cv2.imshow(VENTANA, vis)
        tecla = cv2.waitKey(30) & 0xFF
        if tecla == ord("s"):
            break
        if tecla == ord("c"):
            estado["items"].clear()
        if ord("1") <= tecla <= ord("5"):
            estado["clase_idx"] = tecla - ord("1")

        if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
