# AGENTS.md — InspectorEPP (Guardián EPP)

Sistema de visión en tiempo real que verifica cumplimiento de EPP: YOLO +
ByteTrack → asociación persona↔EPP y ubicación en zona → motor de reglas
simbólico → filtro temporal (anti-parpadeo) → alertas. Python 3.11,
PySide6 + qfluentwidgets, OpenCV, Ultralytics.

Todo el contenido de usuario (UI, mensajes, comentarios) va en **español**.

## Entorno y comandos

- No hay `venv/` en el repo. En esta máquina `python3` ya resuelve a Python
  3.11.15 (pyenv `env_epp`) con las deps de `requirements.txt`. Alternativa
  limpia: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
  (en Windows: `python -m venv venv` y `venv\Scripts\activate`).
- `python3 main.py` → GUI. Entrypoint real: `src/ui/app.py:MainWindow`.
  `main.py` fija `cwd` y `sys.path` a la raíz antes de importar `src.*`.
- `python3 main.py --cli --source 0 --zone GENERAL` → loop OpenCV CLI
  (legacy: polígono fijo y busca `models/ppe_yolov8.pt` con fallback a
  `ppe_best.pt`).
- Smoke test sin pantalla ni cámara:
  `QT_QPA_PLATFORM=offscreen python3 test_run.py` → imprime
  `MainWindow initialized successfully!` y cierra el worker.
- Demos: `python3 demo/pasoN_*.py` (paso1–paso9; guía en `demo/GUIA.md`).
  Salen con la tecla `s`; sin cámara usan `demo/foto_base.jpg`.
- **No hay pytest, tests, lint, typecheck, build ni CI.** No inventar comandos.

## Arquitectura (no obvia por los nombres)

- `src/detector.py` usa **dos modelos**: `models/person_coco.pt` (COCO, solo
  clase 0 `person`, con ByteTrack para IDs estables) y `models/ppe_best.pt`
  (EPP). No es un único detector; no "simplificarlo" a uno.
- Pipeline en `src/ui/video_worker.py` (QThread): captura → dibujar zonas →
  detección/tracking → asociación (`src/association.py`, regiones por altura)
  → punto de pies en polígono (`src/zones.py`) → reglas
  (`src/rule_engine.py`) → filtro temporal (`src/temporal.py`) → alertas.
  Preservar ese orden.
- `src/alert_system.py` implementa **solo voz (pyttsx3)** con cooldown. El
  relé es simulado: `relay_blocked`/`relay` en metadata y UI; no hay código
  serial/pyserial activo.
- `src/ui/app.py` cablea las señales entre vistas y alimenta
  `EventsView.add_event` desde `meta["events"]`. `meta["raw"]` es el frame
  BGR limpio que usa el editor de zonas.

## Rutas y configuración

- **Importar siempre de `src/paths.py`** (`RULES_PATH`, `ZONES_PATH`,
  `CLASSES_PATH`, `SETTINGS_PATH`, `MODELS_DIR`...), ancladas a `__file__`,
  no al CWD. Nunca escribir `"config/rules.json"` o `"models/..."` a mano.
- `config/` de la raíz es la única fuente: `rules.json` (perfil → requeridos
  + mensaje), `zones.json` (`camara_N` → polígonos con `perfil`),
  `classes.json` (clase → nombre en español).
- `config/settings.json` **no está en git**: lo crea la vista Ajustes al
  guardar y lo lee `VideoWorker` al arrancar.
- **`src/ui/config/` es un duplicado obsoleto** (rules/settings/zones
  trackeados en git, sin importadores). No editarlo; editar `config/`.
- Renombrar un perfil en `rules_editor.py` actualiza también `zones.json`.
  Si se edita a mano, el `perfil` de cada zona debe coincidir con una clave
  de `rules.json`; si no, R0 asume "sin regla" y nunca alerta.

## Contrato de clases (verificado en los pesos)

- Clases reales de `models/ppe_best.pt`: `boots`, `esd_smock`, `glasses`,
  `gloves`, `helmet`, `person`, `vest`, `welding_mask` (ids en
  inglés/minúsculas). `detector.normalizar` mapea `glass` → `glasses`.
- Hay desajustes conocidos: `config/classes.json` no incluye `esd_smock`
  (el monitor sí lo muestra; el editor de reglas no lo ofrece) y
  `config/rules.json` exige `mask` en LABORATORIO, pero el modelo no emite
  `mask`. Revisar esto antes de "arreglar" una alarma.
- No modelar clases tipo "sin casco": la ausencia se deduce simbólicamente
  (persona ∧ EPP no asociado → falta).

## UI (qfluentwidgets free 1.11.3)

- Usar solo APIs free; no `pip install -U qfluentwidgets` a ciegas ni APIs
  Pro. Verificar atributos antes de usarlos. En free **no existen**:
  - Íconos `FIF.MAP`, `FIF.TIMER`, `FIF.CONNECTION`, `FIF.X` (usar
    `FIF.PIN`, `FIF.STOP_WATCH`, `FIF.BUS`...).
  - `SimpleListWidget`, `ListWidgetItem`, `EditLabel`, `HeaderViewMode`.
  - `TableWidget.headerView` (usar `horizontalHeader()`),
    `TableWidget.setCornerButtonVisible` (usar `setCornerButtonEnabled`).
  - `SettingCardGroup.addSettingRange`/`addSetting` (usar `addSettingCards`
    / `addSettingCard`).
  - `FluentWindow.navigation`: en free el atributo de instancia es
    `navigationInterface`.
- Enums de Qt desde la clase, no desde la instancia:
  `QAbstractItemView.NoEditTriggers`.
- `ComboBox` free: `addItem(text, icon=None, userData=None)` y
  `setItemData(index, value)` **sin rol**. Pasar `userData=` por keyword.
- Cada vista necesita `objectName` único para `addSubInterface`. La mayoría
  son `ScrollArea`, pero `EventsView` es `QWidget`; respetar el patrón actual.
- No llamar `initNavigation()` (no existe en `FluentWindow`); `addSubInterface`
  registra las vistas.
- Iconos: SVG tintados (`src/ui/icons.py`, `assets/icons/`); sin emojis.
  `src/ui/styles.py` y `src/ui/ui_helpers.py` son legado sin importadores
  (el mapa de equivalencias está en el docstring de `ui_helpers.py`); no
  reutilizar QSS.
- Los errores no capturados se escriben en `guardian_error.log` y muestran
  un diálogo (`sys.excepthook` en `src/ui/app.py`).

## Modelos y git

- Los pesos están en `models/` (`ppe_best.pt` ~20 MB, `person_coco.pt`
  ~6.5 MB) y **sí están trackeados** pese al comentario de `.gitignore`.
  `src/ui/yolov8n.pt` es una copia suelta sin uso.
- El repo git está en la raíz de `InspectorEPP` (branch `main`, ya tiene
  commits). No asumir el `.git` de `Documents`.
- Fallbacks del detector: PPE `ppe_best.pt` → `ppe_yolov8.pt`; personas
  `person_coco.pt` → `yolov8n.pt` en la raíz (no existe). Si falta el modelo
  de personas, usa la clase `person` del modelo EPP (débil).

## Cierre del worker

- Parar con `stop()` (`quit()` + `wait(10000)`). En Windows la apertura con
  `CAP_DSHOW` bloquea 2–6 s y un `wait` corto aborta el proceso con
  `-1073740791`; en Linux se usa `CAP_V4L2`.
- `frame_ready` es `Signal(object, object)`: `(frame_anotado | None,
  metadata: dict)`. Emitir por `_emit_frame` (protegido contra vistas ya
  destruidas).

## Notas

- `README.md` está desactualizado (menciona `customtkinter`, `storage.py`,
  `training/`, `tests/`). La fuente ejecutable es `requirements.txt` + este
  archivo.
- Ultralytics YOLOv8 es AGPL-3.0 (relevante si se comercializa).
