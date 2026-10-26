"""
Rutas base del proyecto — ancladas a la UBICACIÓN de este archivo,
nunca al directorio de trabajo actual (CWD).

¿Por qué existe este módulo?
    Antes, todos los módulos cargaban `"config/rules.json"`,
    `"config/zones.json"`, `"models/ppe_best.pt"`, etc. con rutas
    relativas al CWD. Eso funcionaba solo si la app se lanzaba
    SIEMPRE con cwd = raíz del proyecto. Pero al abrir VS Code con
    el workspace en `Documents/`, ejecutarla con doble clic, o
    lanzarla desde otra terminal, el CWD era otro y los JSON
    "no existían" → fallbacks silenciosos → UI vacía y cambios que
    no se reflejaban.

Regla del proyecto: NINGÚN módulo calcula rutas de configuración por
sí mismo; importa de aquí. `open()`, `os.path.exists()` y YOLO
aceptan `Path` directamente; si un API exige `str`, se usa `str(...).
"""

from pathlib import Path

# src/paths.py -> parents[1] = raíz del proyecto (InspectorEPP/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
MODELS_DIR = PROJECT_ROOT / "models"

RULES_PATH = CONFIG_DIR / "rules.json"
ZONES_PATH = CONFIG_DIR / "zones.json"
CLASSES_PATH = CONFIG_DIR / "classes.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
