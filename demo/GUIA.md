# Guía de `demo/` — Aprendizaje progresivo del Guardián EPP

Carpeta de experimentos paso a paso para entender el sistema haciendo.
Cada paso construye sobre el anterior, igual que el pipeline real:

```
camara -> dibujo -> deteccion -> tracking -> asociacion
       -> zonas -> reglas -> modelo PPE -> integracion
```

## Cómo ejecutar

```
# desde la raiz del proyecto, con el venv activado
python demo/paso1_camara.py
```

Nota: hay una copia de `yolov8n.pt` dentro de `demo/` para que los
scripts la encuentren al correr desde cualquier carpeta; también
funciona la de la raíz. Todas las demos salen con la tecla `s`.

## Progreso

| Paso | Archivo | Tema | Estado |
|---|---|---|---|
| 1 | `paso1_camara.py` | Cámara y frames (NumPy) | completado |
| 2 | `paso2_dibujo.py` | Dibujo: cajas, texto, animación | completado |
| 3 | `paso3_YOLO.py` | Detección con YOLO | completado |
| 4 | `paso4_tracking.py` | Tracking con IDs (ByteTrack) | completado* |
| 5 | (por crear) | Asociación persona <-> EPP | pendiente |
| 6 | (por crear) | Zonas con polígonos | pendiente |
| 7 | (por crear) | Mini motor de reglas | pendiente |
| 8 | (por crear) | Modelo PPE real (Roboflow) | pendiente |
| 9 | (por crear) | Integración: mini-Guardián | opcional |

\* falta el mini-reto de la estela (ver Paso 4).

---

## Lo aprendido por paso

### Paso 1 — Cámara y frames

- `cv2.VideoCapture(0)` abre la webcam; `cap.read()` da `(ok, frame)`
- Un frame es un **array NumPy** `(alto, ancho, 3)` en formato **BGR**
- `cv2.waitKey(1)` no solo lee teclado: **refresca la ventana**
- Recortes: `frame[y1:y2, x1:x2]` — Y es vertical, X horizontal
- Retos hechos: salir con `s`, recorte del centro, efecto espejo

### Paso 2 — Dibujo sobre frames

- `cv2.rectangle / putText / circle / line`; colores en **BGR, no RGB**
- `thickness = -1` rellena la figura
- Retos hechos: colores, animación de la caja, contador de FPS
- Lecciones de la revisión:
  - `if x == ancho` es frágil (falla si el paso no divide exacto);
    usar `>=`
  - `cap.get(cv2.CAP_PROP_FPS)` es el FPS **declarado** por el driver;
    el FPS **real** se mide cronometrando con `time.time()` entre
    frames (así lo hace el monitoreo del Guardián)

### Paso 3 — Detección con YOLO

- `model(frame, conf=0.5, verbose=False)`; las detecciones están en
  `results[0].boxes`
- Por caja: `box.cls` (qué), `box.conf` (seguridad), `box.xyxy`
  (dónde); tensors -> Python con `.item()` / `.tolist()`
- `model.names[cls_id]` traduce id de clase a texto
- Subir `conf` descarta detecciones débiles (la suitcase llegaba
  a ~0.60, con conf=0.8 desaparecía)
- Retos hechos: filtro por clase (suitcase), umbral de confianza,
  punto de los pies `((x1+x2)//2, y2)`
- Opcional saltado a propósito: ajustar `conf` con teclas `+`/`-`

### Paso 4 — Tracking con IDs estables

- `model.track(frame, persist=True, ...)`; el ID viene en `box.id`
  (puede ser `None` algún frame: chequearlo)
- IDs estables y coloreados por persona; log de ENTRARON/SALIERON
  comparando sets de IDs entre frames
- **El warning `not enough matching points`:** en ultralytics 8.4.182
  el tracker por defecto usa GMC (compensación de movimiento de
  cámara vía puntos distintivos + flujo óptico). Con escena plana y
  cámara quieta encuentra <=4 puntos y avisa. No es un error: solo
  se salta esa compensación. Solución aplicada:

  ```python
  results = model.track(
      frame, persist=True, conf=0.2,
      tracker="bytetrack.yaml", verbose=False
  )
  ```

  ByteTrack no usa GMC. GMC solo aporta con cámaras en movimiento;
  en el Guardián las cámaras son fijas, así que `bytetrack.yaml` es
  la elección correcta para el proyecto
- **PENDIENTE — reto de la estela:**

  ```python
  historias = {}                       # {track_id: [(x, y), ...]}
  # en el bucle, tras calcular pies:
  historias.setdefault(track_id, []).append(pies)
  historias[track_id] = historias[track_id][-30:]  # max 30 puntos
  # dibujar la estela con cv2.line entre puntos consecutivos
  ```

  Es la memoria por persona que después usa el módulo temporal
  (`src/temporal.py`) para confirmar violaciones.

---

## Lecciones acumuladas (errores típicos ya vistos)

1. Import fantasma por autocompletado (`supervision`) -> borrar
2. Código muerto tras un `continue` (ternario que nunca es falso)
3. `==` con pasos que no dividen exacto -> usar `>=`
4. FPS declarado vs FPS real (medir, no confiar en el driver)
5. Variables sin usar (`cls = results[0].names`)
6. `cv2.flip(frame, 1)` es más seguro que `frame[:, ::-1]` cuando el
   frame entra a YOLO (array contiguo)

---

## Siguientes pasos (guía para continuar solo)

### Paso 5 — Asociación persona <-> EPP (geometría)

Objetivo: saber **de QUIÉN** es cada EPP. COCO no trae
helmet/vest: trabajar con cajas sintéticas.

- Lienzo con 1-2 "personas" (rectángulos fijos) y clic izquierdo
  que coloca un EPP (teclas 1-5 eligen la clase)
- Regla de asociación: el **centro** del EPP cae dentro de la caja
  de la persona **Y** en su región anatómica vertical:
  - tercio superior: helmet, mask, glasses, welding_mask
  - zona media: vest, gloves
  - tercio inferior: boots
- Dibujar verde = asociado, rojo = huérfano; imprimir el resultado
- Referencia: `src/association.py` (`REGION_MAPPING`,
  `PPEAssociator.associate`)
- Reto: con 2 personas que compiten por un EPP, ganará la de
  **menor área** (mismo criterio que `association.py`)

### Paso 6 — Zonas con polígonos

Objetivo: en qué **ZONA** está cada persona (punto de los pies).

- Cargar polígonos desde un JSON (puede ser `config/zones.json` o
  un `demo/zones_demo.json` con 2-3 zonas de práctica)
- Clic = punto de los pies; `cv2.pointPolygonTest(poly, pt, False)
  >= 0` significa dentro
- Dibujar zonas con relleno tenue: `cv2.addWeighted` sobre un
  overlay (así lo hace `ZoneManager.draw_zones`)
- Fuera de toda zona = regla **R5**: ignorar
- Referencia: `src/zones.py` (`ZoneManager`)
- Reto: dos zonas que se tocan — ¿cuál gana? (la primera del JSON)

### Paso 7 — Mini motor de reglas (módulo simbólico)

Objetivo: decidir si una persona cumple la normativa de su zona.

- Reglas en JSON: `{perfil: {requeridos: [...], mensaje}}`
- Faltantes = requeridos - presentes (operaciones de `set`)
- Conservar SIEMPRE la explicación: qué regla, qué hechos
  (explicabilidad = clave del sistema y de la materia)
- REPL en consola: elegir zona + escribir EPP presentes ->
  imprimir `is_safe`, `missing`, código de regla y explicación
- Referencia: `src/rule_engine.py` (`RuleEngine.evaluate_person`)
- Reto: agregar una regla "BODEGA" al JSON **sin tocar código**
  (esa es la gracia del módulo simbólico)

### Paso 8 — Modelo PPE real (Roboflow)

Objetivo: pasar de COCO genérico a `helmet`, `vest`,
`welding_mask`...

- Descargar dataset PPE de Roboflow Universe (revisar licencia)
- `data.yaml` con las **mismas** clases que `rules.json` y
  `classes.json` (evita desajustes de nombres)
- Fine-tuning partiendo de pesos preentrenados (ideal en Colab):

  ```python
  from ultralytics import YOLO

  model = YOLO("yolov8s.pt")
  model.train(data="training/data.yaml", epochs=100, imgsz=640)
  ```

- Guardar pesos en `models/ppe_best.pt`: el detector del proyecto
  (`src/detector.py`) ya los busca primero automáticamente
- Reto: comparar detecciones del paso 3 (COCO) vs modelo PPE en el
  mismo video
- Nota de licencia: YOLOv8 es **AGPL-3.0**; para uso comercial
  revisar la sección de licencias del `README.md`

### Paso 9 (opcional) — Mini-Guardián integrado

Unir todo en un solo archivo:

```
camara -> detect+track -> asociar EPP -> zona (pies)
       -> reglas -> overlay + filtro temporal + log de eventos
```

- Filtro temporal: la alarma solo se confirma tras N frames
  consecutivos (referencia `src/temporal.py`)
- Log de eventos con timestamp cuando la alarma se confirma

---

## Dónde está "la respuesta oficial"

Cada paso es una versión educativa de un módulo real del proyecto:

| Paso | Módulo real |
|---|---|
| 1, 2 | `src/camera.py` + overlay de `src/ui/monitor.py` |
| 3, 4 | `src/detector.py` (`PPEDetector`) |
| 5 | `src/association.py` (`PPEAssociator`) |
| 6 | `src/zones.py` (`ZoneManager`) |
| 7 | `src/rule_engine.py` (`RuleEngine`) |
| 8 | `training/` + `README.md` (dataset y licencias) |
| 9 | `src/ui/monitor.py` (pipeline completo) |

Ante cualquier duda, comparar tu solución con el módulo real.
