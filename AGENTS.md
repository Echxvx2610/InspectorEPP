# AGENTS.md — InspectorEPP (Guardián EPP)

Sistema de visión en tiempo real que verifica cumplimiento de EPP: YOLO +
ByteTrack (conexionista) → asociación persona↔EPP y ubicación en zona
(geométrico) → motor de reglas simbólico → filtro temporal (anti-parpadeo) →
alertas (voz, relé/Arduino). Python 3.11, PySide6, OpenCV, supervision.

Todo el contenido de usuario (UI, mensajes, comentarios) va en **español**.

## Requisitos

- Usar el venv local (Python 3.11): en PowerShell
  `.\venv\Scripts\Activate.ps1`; en cmd `venv\Scripts\activate.bat`.

## Ejecución (siempre desde la raíz del proyecto)

- `python main.py` → app GUI PySide6 (entrypoint real: `src/ui/app.py` `MainWindow`).
- `python main.py --cli --source 0 --zone GENERAL` → loop OpenCV CLI.
- Verificación más rápida de que la app arranca: `python test_run.py`.
- Demos de aprendizaje: `python demo/paso1_camara.py` …
  (paso1–paso9, con `demo/GUIA.md` como guía y bitácora; los pasos
  5–9 son versiones educativas de los módulos reales; salen con la
  tecla `s`, y sin cámara usan `demo/foto_base.jpg`).
- **No hay pytest ni suite de tests** (ni `tests/` ni `training/`);
  no inventar comandos de test/lint/build.

## Gotchas críticos

- **Rutas de config SIEMPRE de `src/paths.py`**: ninguna parte calcula
  rutas relativas (`"config/rules.json"`, `"models/ppe_best.pt"`).
  Importar de `src/paths.py` (PROJECT_ROOT / CONFIG_DIR / MODELS_DIR +
  RULES_PATH, ZONES_PATH, CLASSES_PATH, SETTINGS_PATH), ancladas a
  `__file__`, no al CWD. Ya lo usan: `detector`, `rule_engine`,
  `zones`, `video_worker`, `main.py` (CLI), `rules_editor`,
  `zone_editor`, `settings_view`, `events_view`. `main.py` además fija
  cwd = raíz como red de seguridad. Síntoma de ruta relativa suelta:
  fallback silencioso (JSON "no existe") → UI vacía y cambios no
  reflejados según desde dónde se abra la app.
- (histórico, antes de paths.py) Estas rutas eran relativas al CWD y
  solo funcionaban ejecutando con cwd = raíz del proyecto.
- **No existe la carpeta `models/`**: `PPEDetector` (`src/detector.py`) cae por
  defecto a `yolov8n.pt` de la raíz (COCO, sin clases EPP → las reglas nunca
  pasan). Un modelo PPE entrenado va en `models/ppe_best.pt` o
  `models/ppe_yolov8.pt` (orden de búsqueda en el constructor).
- **Contrato de clases**: usar siempre los mismos ids en inglés/minúsculas
  (`helmet`, `vest`, `gloves`, `welding_mask`, `mask`, `glasses`, `boots`) en
  dataset, `config/classes.json` y `config/rules.json`, y en el código.
  Nunca modelar clases tipo "sin casco": la ausencia se deduce simbólicamente
  (persona detectada ∧ sin EPP asociado → violación).
- **Pipeline completo en `src/ui/video_worker.py`** (QThread): orden
  cámara → zonas → detección+tracking → asociación → zona → reglas →
  temporal → alertas. Preservar ese orden y el contrato de la señal
  `frame_ready(object, dict)`; parar con `stop()` (quit + wait(10000);
  el `wait` debe superar el bloqueo de apertura CAP_DSHOW ~2-6 s,
  si es más corto el proceso muere con -1073740791 al salir).
  `meta` incluye `"raw"`: frame BGR sin anotaciones (base para el
  editor de zonas).
- `AlertSystem` reproduce voz (pyttsx3) y activa el relé serial
  (pyserial/Arduino). Al correr sin hardware, verificar que estén
  deshabilitados en la vista Ajustes.
- **Repo git**: el `.git` real está en la carpeta `Documents` (branch
  `master`, sin commits); `InspectorEPP` es una subcarpeta. Al hacer commit
  incluir solo esta subcarpeta (`git add .` desde aquí) y cuidar `*.pt`
  (no ignorados, 6–20 MB cada uno).
- **`plan_correcion.md` es un checklist vivo** de refactor UI/UX: leerlo
  antes de tocar `src/ui/` (problemas conocidos: eventos no conectados a
  `EventsView.add_event`, estilos heredados en QLabel, etc.).

## Configuración

- `config/zones.json` — polígonos por cámara (perfil por zona).
- `config/rules.json` — perfil → EPP requerido + mensaje.
- `config/classes.json` — mapeo clase del modelo → nombre en español.
- `config/settings.json` — lo escribe la vista Ajustes y el worker lo
  aplica en caliente (`apply_settings`).

## UI (PySide6)

- Se usa **qfluentwidgets versión free (1.11.3)**. NO usar APIs de la versión
  Pro (ni de PyQt5-Fluent/otras variantes) ni llamar `pip install -U
  qfluentwidgets` a ciegas; verificar que el atributo exista antes de usarlo.
  Cosas que NO existen en free (halladas en producción):
  - Íconos: `FIF.MAP`, `FIF.TIMER`, `FIF.CONNECTION`, `FIF.X` — usar
    `FIF.PIN`, `FIF.STOP_WATCH`, `FIF.BUS` o equivalentes.
  - `SimpleListWidget`, `ListWidgetItem`, `EditLabel`, `HeaderViewMode`.
  - `TableWidget.headerView` (usar `horizontalHeader()` nativo),
    `TableWidget.setCornerButtonVisible` (usar `setCornerButtonEnabled`).
  - Enums por instancia (`self.table.NoEditTriggers`) — usar
    `QAbstractItemView.NoEditTriggers`.
  - `SettingCardGroup.addSettingRange/addSetting` — usar
    `addSettingCards` / `addSettingCard`.
  - `FluentWindow.navigation` — en free es `navigationInterface`.
- Formas de armar vistas: cada vista es `ScrollArea` con `objectName`
  único (requisito de `FluentWindow.addSubInterface`).
- Estilos/QSS previos en `src/ui/styles.py`; los roles `set_role`,
  `StatusChip`, `Toast` fueron reemplazados por labels Fluent,
  `InfoBadge` e `InfoBar` (ver mapa de equivalencias en
  `src/ui/ui_helpers.py`).
- Iconos: SVG tintados de un solo color (`nav_icon`, `tint_icon`,
  `assets/icons/`). Sin emojis en la UI (usar iconos SVG).
- `README.md` está desactualizado (menciona `customtkinter`,
  `storage.py`, `training/` y `tests/` que no existen). La fuente
  confiable de dependencias es `requirements.txt`.
  Nota: Ultralytics YOLOv8 es AGPL-3.0 (relevante si se comercializa).
