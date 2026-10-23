"""
Paso 6 - Zonas con poligonos
============================
Objetivo: saber en que ZONA esta una persona usando el punto de sus PIES.

Igual que en el paso 5, percepcion y razonamiento van separados:
aqui el "pies" lo pone el mouse (clic); en el Guardian real vendra de
la caja de YOLO: ((x1 + x2) // 2, y2).

Uso:
    python demo/paso6_zonas.py

Controles:
    clic izq  colocar el punto de los pies
    s         salir

Referencia: src/zones.py (ZoneManager)
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

BASE = Path(__file__).resolve().parent
RUTA_ZONAS = BASE / "zones_demo.json"
VENTANA = "Paso 6 - Zonas con poligonos"
ANCHO, ALTO = 900, 600

# colores BGR
BLANCO = (255, 255, 255)
ROJO = (0, 0, 255)
FONDO = (30, 30, 30)


# ---------------------------------------------------------------------------
# 1. Carga de zonas desde JSON
# ---------------------------------------------------------------------------
def cargar_zonas(ruta):
    """Lee el JSON y devuelve una lista de dicts:
    {"nombre": str, "color": tupla BGR, "poligono": np.array int32 (N, 2)}

    El poligono se convierte a np.int32 porque las funciones de OpenCV
    (fillPoly, polylines, pointPolygonTest) trabajan con arrays NumPy,
    no con listas de Python.
    """
    if not ruta.exists():
        sys.exit(f"No existe el archivo de zonas: {ruta}")

    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    zonas = []
    for z in datos["zonas"]:
        zonas.append({
            "nombre": z["nombre"],
            "color": tuple(z["color"]),
            "poligono": np.array(z["poligono"], dtype=np.int32),
        })
    return zonas


# ---------------------------------------------------------------------------
# 2. Dibujo: relleno tenue + borde + nombre
# ---------------------------------------------------------------------------
def dibujar_zonas(vis, zonas, alpha=0.25):
    """Relleno semitransparente con addWeighted (como ZoneManager.draw_zones).

    Truco: se dibuja el relleno en una COPIA (overlay) y luego se mezcla
    con el original: resultado = overlay*alpha + vis*(1-alpha).
    La mezcla se hace una sola vez para todas las zonas.
    """
    overlay = vis.copy()
    for z in zonas:
        cv2.fillPoly(overlay, [z["poligono"]], z["color"])
    cv2.addWeighted(overlay, alpha, vis, 1 - alpha, 0, vis)

    # borde y nombre van encima, ya sin transparencia
    for z in zonas:
        cv2.polylines(vis, [z["poligono"]], True, z["color"], 2)
        x, y = z["poligono"][0]  # primer vertice: ancla del texto
        cv2.putText(vis, z["nombre"], (int(x) + 6, int(y) + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, z["color"], 2)


# ---------------------------------------------------------------------------
# 3. Pertenencia: punto dentro de poligono
# ---------------------------------------------------------------------------
def zona_de_punto(zonas, punto):
    """Devuelve la PRIMERA zona (orden del JSON) que contiene el punto,
    o None si esta fuera de todas.

    cv2.pointPolygonTest(poligono, punto, False) devuelve:
        +1.0 dentro, 0.0 exactamente sobre el borde, -1.0 fuera
    Con '>= 0' el borde cuenta como dentro.
    """
    pt = (float(punto[0]), float(punto[1]))
    for z in zonas:
        if cv2.pointPolygonTest(z["poligono"], pt, False) >= 0:
            return z
    return None


# ---------------------------------------------------------------------------
# 4. Programa principal
# ---------------------------------------------------------------------------
def main():
    zonas = cargar_zonas(RUTA_ZONAS)
    if not zonas:
        sys.exit("No hay zonas cargadas.")

    print("Zonas cargadas:")
    for z in zonas:
        print(f"  {z['nombre']}: {len(z['poligono'])} vertices")
    print()

    estado = {"pies": None}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            estado["pies"] = (x, y)

    cv2.namedWindow(VENTANA)
    cv2.setMouseCallback(VENTANA, on_mouse)

    firma_previa = None
    while True:
        vis = np.full((ALTO, ANCHO, 3), 40, dtype=np.uint8)
        dibujar_zonas(vis, zonas)

        texto = "clic: colocar pies   [s] salir"
        if estado["pies"] is not None:
            zona = zona_de_punto(zonas, estado["pies"])
            nombre = zona["nombre"] if zona else "FUERA (ignorar)"
            color = zona["color"] if zona else ROJO
            cv2.circle(vis, estado["pies"], 7, color, -1)
            cv2.circle(vis, estado["pies"], 9, BLANCO, 1)
            texto = f"pies {estado['pies']} -> {nombre}"

            # imprimir solo cuando cambia el veredicto
            if texto != firma_previa:
                print(texto)
                firma_previa = texto

        cv2.rectangle(vis, (0, 0), (ANCHO, 34), FONDO, -1)
        cv2.putText(vis, texto, (10, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, BLANCO, 1)

        cv2.imshow(VENTANA, vis)
        if cv2.waitKey(30) & 0xFF == ord("s"):
            break
        if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()