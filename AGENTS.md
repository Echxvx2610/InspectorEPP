# AGENTS.md — Guardián EPP

Guía para agentes. Verificado contra el código: README.md y plan_correcion.md
están desactualizados (describen estructura y fixes aspiracionales).

## Comandos

- Instalar dependencias ANTES de nada: `pip install -r requirements.txt`.
  No hay venv en el repo; PySide6 suele venir preinstalado, pero cv2/numpy/
  ultralytics/pyttsx3/pyserial no — la app no arranca sin ellas.
- GUI (entrada principal): `python main.py`
- CLI legacy (requiere `supervision`): `python main.py --cli --source 0 --zone GENERAL`
- BUG conocido: `--source` se parsea pero se ignora en modo GUI (VideoWorker
  nace con source=0). La cámara se cambia desde el combo de Monitoreo.
- No hay tests, lint ni CI. Verificación = lanzar la GUI y observar comportamiento.
- Demos educativas: `python demo/pasoN_*.py`; salen con la tecla `s`.
  `demo/GUIA.md` mapea cada paso al módulo real de `src/`.

## Arquitectura

- `main.py` → `src/ui/app.py::MainWindow` (PySide6). Todo el procesamiento de
  video vive en `src/ui/video_worker.py` (QThread).
- Pipeline en VideoWorker, en este orden: dibujar zonas → detect+track
  (YOLO+ByteTrack) → asociar EPP → zona por punto de pies → RuleEngine →
  TemporalFilter → alertas → señal `frame_ready(frame, meta)`.
- Módulos de `src/` (camera, detector, association, zones, rule_engine,
  temporal, alert_system) son puros, sin Qt: la lógica va ahí; `src/ui/` es
  solo presentación.
- Contrato UI↔worker: solo señales Qt. El estado del worker se cambia con
  métodos protegidos por mutex (`reload_zones`, `reload_rules`,
  `apply_settings`, `set_source`). Nunca tocar cv2/VideoCapture en el hilo de UI.
- Config: `config/zones.json` (clave `camara_N`), `config/rules.json`
  (perfiles), `config/classes.json` (clase → nombre español),
  `config/settings.json` (no está en el repo; lo crea Ajustes al primer guardado).
- Las vistas que editan config emiten `zones_updated` / `rules_updated` /
  `settings_changed` y MainWindow llama a los reload del worker (ver `app.py`).
  Cualquier vista nueva que afecte config debe cablearse igual.

## Gotchas

- Fallback de modelo en `src/detector.py`: `models/ppe_best.pt` →
  `models/ppe_yolov8.pt` → `yolov8n.pt`. Solo existe `yolov8n.pt` (COCO):
  solo detecta `person`, los EPP salen siempre vacíos. El entrenamiento propio
  (fase 7 del README) no existe aún.
- Config de fábrica vacía a propósito: `rules.json` con `requeridos: []` en
  todos los perfiles y `zones.json` sin zonas → nunca se dispara una
  violación. No buscar bugs de lógica en ese estado; primero llenar config.
- Contrato de clases: los nombres de detección (minúsculas, inglés: helmet,
  vest, mask, glasses, gloves, welding_mask, boots) deben coincidir entre el
  dataset, `classes.json` y `requeridos` de `rules.json`. Renombrar en un solo
  lado rompe la asociación y las reglas.
- Asociación (`src/association.py`): el centro del EPP debe caer dentro del
  bbox de la persona (margen ±15 % en X) Y en su banda anatómica vertical
  (`REGION_MAPPING`); en empate gana la persona de menor área.
- Zonas: punto de evaluación = pies (centro-inferior del bbox);
  `cv2.pointPolygonTest(...) >= 0`; si dos zonas se solapan gana la primera
  del JSON.
- Tracking: usar `model.track(frame, persist=True, tracker="bytetrack.yaml")`,
  no el tracker por defecto (avisa "GMC" con cámara fija). `box.id` puede ser
  None en algún frame; hay fallback de ID.
- Estilos: QSS global en `src/ui/styles.py`; los widgets son transparentes por
  defecto. Usar roles con `set_role`/`set_state` (`src/ui/ui_helpers.py`) y
  repolish tras cambiar la propiedad; no meter `setStyleSheet` inline.
  `styles.py` resuelve `assets/icons/*.svg` con `parents[2]`: mantenerlo en `src/ui/`.
- Idioma: textos y comentarios en español (con acentos: Detección, Relé,
  Síntesis); identificadores y claves de config en inglés.
- Herencia Windows: `CAP_DSHOW` como primer backend y puerto `COM3` por
  defecto; en Linux DSHOW falla y cae al backend default, y los puertos son
  `/dev/tty*`.
- Git: los `.pyc` de `src/**/__pycache__` ya están trackeados, así que
  `git status` siempre los muestra sucios; no incluirlos en commits.

## Modo de trabajo — orquestador + obreros

- La sesión principal (GLM-5.3-Flash Free) actúa como ORQUESTADOR:
  recibe la petición del usuario, la descompone en tareas, las delega,
  revisa los resultados e integra la respuesta final.
- OBREROS (ejecutores, no hablan con el usuario):
  - MiniMax-M3.1-Flash → `nvidia/minimaxai/minimax-m3.1-flash`
  - DeepSeek V4.1 Flash → `nvidia/deepseek-ai/deepseek-v4.1-flash`
- Delegación con la herramienta `subagent`: `agent: "general"`,
  `model: "<id del obrero>"`. Tareas independientes → lanzarlas en
  paralelo (varias llamadas en un mismo bloque, o `background: true`).
- El prompt de cada subagente debe ser AUTOCONTENIDO (rutas, contexto,
  criterio de éxito): los subagentes arrancan con contexto fresco y no
  ven esta conversación.
- El orquestador SIEMPRE revisa la salida del obrero contra el código
  real antes de responder al usuario; nunca la reenvía sin validar.
  Para seguir iterando con el mismo obrero, pasar su `sessionID`.
- Excepción: peticiones triviales (una lectura, un cambio de una línea)
  las resuelve el orquestador directamente, sin delegar.
