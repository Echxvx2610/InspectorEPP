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

Nota: hay copias de `yolov8n.pt` / `yolov8s.pt` dentro de `demo/` para que
los scripts funcionen desde cualquier carpeta; también sirven las de la
raíz. Todas las demos de ventana salen con la tecla `s` (o cerrando la
ventana). Los pasos que abren cámara caen a `demo/foto_base.jpg` si la
cámara no está disponible.

## Progreso

| Paso | Archivo | Tema | Estado |
|---|---|---|---|
| 1 | `paso1_camara.py` | Cámara y frames (NumPy) | completado |
| 2 | `paso2_dibujo.py` | Dibujo: cajas, texto, animación | completado |
| 3 | `paso3_YOLO.py` | Detección con YOLO | completado |
| 4 | `paso4_tracking.py` | Tracking con IDs (ByteTrack) + estela | completado |
| 5 | `paso5_asociacion.py` | Asociación persona <-> EPP | completado |
| 6 | `paso6_zonas.py` | Zonas con polígonos | completado |
| 7 | `paso7_reglas.py` | Mini motor de reglas (consola) | completado |
| 8 | `paso8_modelo_ppe.py` | Contrato de clases + ruta a Roboflow | completado (entrenar en Colab queda como tarea) |
| 9 | `paso9_mini_guardian.py` | Integración: mini-Guardián | completado |

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
- **RETO DE LA ESTELA — hecho.** La memoria del camino vive en un dict:

  ```python
  historias = {}                       # {track_id: [(x, y), ...]}
  # en el bucle, tras calcular los pies:
  historias.setdefault(track_id, []).append(pies)
  historias[track_id] = historias[track_id][-30:]  # max 30 puntos
  # dibujar cv2.line entre puntos consecutivos
  # y borrar la estela de quien ya salió del cuadro
  ```

  Es la memoria por persona que después usa el módulo temporal
  (`src/temporal.py`) para confirmar violaciones. Ojo: el ID del
  tracker puede ser `None` algún frame — sin ID no hay estela.

### Paso 5 — Asociación persona <-> EPP

- El modelo COCO no conoce helmet/vest: en la demo el EPP es
  **sintético** (cajas que coloca el mouse) y solo las PERSONAS las
  detecta YOLO. Percepción y razonamiento siguen desacoplados
- La asociación es geometría pura: el CENTRO del EPP debe caer dentro
  del bbox de la persona (con margen horizontal) **y** en la franja
  vertical de su clase (`REGION_MAPPING`, `rel_y` 0.0=cabeza .. 1.0=pies)
- Si dos personas compiten por un EPP, gana la de **MENOR área**
  (persona más al frente); es exactamente el criterio de
  `src/association.py`
- Trucos de la sesión:
  - `cv2.imread` falla con rutas con acentos en Windows -> leer bytes
    con `np.fromfile` + `cv2.imdecode`
  - foto estática -> IDs "estables por definición" (orden izquierda a
    derecha); el tracking de verdad se demuestra en el paso 4
  - imprimir en consola SOLO cuando cambia el veredicto (firma de
    texto distinta al anterior) para no spamear a 30 fps
- Reto hecho: dos personas compiten por un EPP

### Paso 6 — Zonas con polígonos

- El punto que decide la zona es el de los PIES (el mismo del paso 4)
- `cv2.pointPolygonTest(poly, pt, False) >= 0` = dentro (borde cuenta)
- Los polígonos deben ser `np.array(..., dtype=np.int32)`: las
  funciones de OpenCV piden NumPy, no listas de Python
- Relleno tenue: dibujar en un `overlay = vis.copy()` y mezclar una
  SOLA vez con `cv2.addWeighted` al final (así lo hace
  `ZoneManager.draw_zones`)
- FUERA de toda zona = regla **R5**: se ignora, nunca es infracción
- Reto hecho: zonas que se tocan -> gana la PRIMERA del JSON (orden
  importa)

### Paso 7 — Mini motor de reglas (consola)

- REGLA CENTRAL del módulo simbólico: las reglas son DATOS
  (`rules.json`), no código. Agregar un perfil nuevo no toca lógica
- La evaluación es una resta de conjuntos: `faltantes = requeridos -
  presentes` (cuidado: listas que conservan el ORDEN del JSON para el
  mensaje, sets solo para la pertenencia)
- Cada veredicto trae SIEMPRE `{is_safe, missing, rule_code,
  explanation}` — esa es la EXPLICABILIDAD que quiere la materia y
  que audita el cliente
- Códigos de regla: `R5` (fuera de zona), `R0` (perfil sin regla o
  con `requeridos` vacío — ojo: un perfil sin requeridos es SIEMPRE
  conforme; no es un error de código sino de datos), `OK`, `VIOLACION`
- Los IDs de EPP se escriben en inglés (`helmet`...); la traducción a
  español ocurre SOLO al mostrar (texto => `PPE_ES`); aceptar el
  tecleo en ambos idiomas es fácil con un mapa de alias
- Reto hecho: perfil agregado por consola ('a' del REPL) y usado a
  continuación, sin reiniciar
- OJO para el proyecto real: el `config/rules.json` llegó un día con
  TODOS los `requeridos` en `[]` y el sistema dejaba de alarmar; el
  chequeo permite notarlo rápido

### Paso 8 — Modelo PPE real (Roboflow) + contrato de clases

- Este paso es mitad script (lo local y verificable), mitad manual
  (Roboflow/Colab — ver docstring del script y el README)
- **El chequeo de clases (`--check`) es la lección clave:** los
  nombres de clase han de cuadrar con la EXACTITUD EXACTA (un caracter
  más, un plural, 'casco'/'helmet') en tres fuentes a la vez:
  modelo (`model.names`), `classes.json` (UI), `rules.json` (perfiles)
- Consecuencias del desajuste verificadas en la demo:
  - la regla exige una clase que el modelo no detecta -> la regla
    NUNCA se dispara (infracciones silenciosas)
  - `classes.json` anuncia clases que el modelo no tiene -> la UI
    muestra etiquetas muertas
- Reto pendiente (para el usuario): entrenar en Colab con el dataset
  PPE (Roboflow), registrar comparación base vs PPE en el mismo video
  y copiar los pesos a `models/ppe_best.pt`
- Nota licencia: YOLOv8 es AGPL-3.0 (revísala antes de vender)

### Paso 9 — Mini-Guardián integrado

- La integración es ELEGANTE si se respeta la capa:
  percepción (YOLO + geometría inline) -> asociar (paso 5) -> zona
  (paso 6) -> REGLAS (real: `src/rule_engine.py`) -> TEMPORAL (real:
  `src/temporal.py`) -> alerta (real: `src/alert_system.py`)
- Con COCO el EPP se "concede" por teclas 1-5 (sintético); al día de
  que exista `models/ppe_best.pt`, el MISMO script detecta EPP real
  sin tocar nada simbólico
- **Filtro temporal — la lección del proyecto:** no basta con "falta
  EPP este frame": cuentan los frames CONSECUTIVOS (y/o un tiempo de
  gracia). Solo el evento CONFIRMADO debe dejarse en el log; si no,
  cada oclusión de 2 frames es una alarma falsa
- Log de eventos: UNA entrada por racha de violación (no por frame);
  con timestamp, persona, zona, texto de regla y `rule_code`. Se
  guarda en `demo/eventos_demo.log`
- Truco aprendido: cada ráfaga de EPP concedido reinicia el filtro
  temporal (`TemporalFilter` fresco): escenario nuevo, contador cero
- Doble modo de zonas: cargadas de `config/zones.json` (de la app) o
  dibujadas en vivo con `z` + clics + `ENTER`

---

## Lecciones acumuladas (errores típicos ya vistos)

1. Import fantasma por autocompletado (`supervision`) -> borrar
2. Código muerto tras un `continue` (ternario que nunca es falso)
3. `==` con pasos que no dividen exacto -> usar `>=`
4. FPS declarado vs FPS real (medir, no confiar en el driver)
5. Variables sin usar (`cls = results[0].names`)
6. `cv2.flip(frame, 1)` es más seguro que `frame[:, ::-1]` cuando el
   frame entra a YOLO (array contiguo)
7. `cv2.imread` falla con rutas con acentos/raros en Windows ->
   bytes + `cv2.imdecode`
8. Cámara que no abre: en Windows DSHOW es lo primero, y a veces ni
   el default funciona: paciencia con reintentos o foto estática
9. Imprimir a 30 fps: imprime SOLO cuando cambia el veredicto (firma)
10. f-strings de varias líneas dentro de `{}`: en Python 3.11 no
    compilan -> variables limpias antes de formatear

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
| 9 | `src/ui/monitor.py` + `src/ui/video_worker.py` (pipeline real) |
