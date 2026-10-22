# Plan de correcciones UI/UX — Guardián EPP

Revisión de `app.py`, `styles.py`, `events_view.py`, `rules_editor.py`, `settings_view.py`, `zone_editor.py`, `video_worker.py` y la captura del Monitoreo.

No se revisaron `monitor.py` ni `icons.py`. Lo del Monitoreo sale solo de la captura.

Criterio: UI limpia, sin emojis, solo iconos SVG consistentes.

---

## 0. Archivos entregados

| Archivo | Destino en el proyecto | Acción |
|---|---|---|
| `styles.py` | `src/ui/styles.py` | Reemplazar el actual |
| `ui_helpers.py` | `src/ui/ui_helpers.py` | Nuevo |
| `chevron-down.svg` | `assets/icons/chevron-down.svg` (raíz del proyecto) | Nuevo |
| `check.svg` | `assets/icons/check.svg` (raíz del proyecto) | Nuevo |

`ui_helpers.py` contiene: `set_role`, `set_state`, `make_label`, `tint_icon`, `nav_icon`, `StatusChip`, `Toast`.

---

## 1. Problemas encontrados

1. **Fondo gris en las labels.** `QWidget { background-color: #f3f3f3 }` se hereda en todos los `QLabel`. Solucionado en el nuevo `styles.py`: solo `QMainWindow` y `QDialog` pintan el gris.
2. **Checkboxes marcados sin palomita.** Se veían como un cuadro azul. Solucionado con `check.svg`.
3. **Combos sin flecha.** `drop-down { border: none }` ocultaba el indicador. Solucionado con `chevron-down.svg`.
4. **`btn-primary-outline` no existía en el QSS.** "Guardar zona" se veía como botón normal. Ya está definido.
5. **Títulos de sección con tres estilos distintos** (azul 13px, azul 14px, texto plano), todos inline. Ahora hay roles de texto.
6. **Demasiado azul** en títulos, nav, botones y valores. Ahora el azul queda solo para acciones y estado activo.
7. **Acentos inconsistentes.** Monitoreo dice "Cámara", el resto dice "Camara", "Deteccion", "Rele", "Sintesis", "Infraccion", "Atencion".
8. **Iconos del nav no cambian de color al activarse.** El texto se pone azul y el icono queda gris. Se resuelve con `nav_icon()`.
9. **Doble sangría en el sidebar.** Botones con `margin: 1px 8px` más el margen del layout. Quitado.
10. **Separadores `HLine` gruesos y con relieve.** Ahora son una línea de 1px.

---

## 2. Roles de texto disponibles

Se asignan con `set_role(widget, "rol")` o `widget.setProperty("role", "rol")` antes de mostrar el widget.

| Rol | Uso |
|---|---|
| `title` | Título de página (18px, bold) |
| `brand` | Nombre en el sidebar |
| `section` | Título de tarjeta o sección (14px, bold, negro) |
| `eyebrow` | Etiqueta pequeña en mayúsculas, gris |
| `field` | Etiqueta de campo ("Nombre", "Perfil") |
| `caption` | Texto auxiliar pequeño (hints, versión) |
| `muted` | Texto secundario gris |
| `value` | Números grandes (22px); con `state="ok"` o `"bad"` cambia el color |
| `value-sm` | Valor pequeño en negrita (ej. umbral de confianza) |

Estados para chips y valores: `ok`, `warn`, `bad`, `idle`.

---

## 3. Checklist por archivo

### 3.1 `app.py`

- [ ] Importar: `from PySide6.QtCore import Qt, Slot, QSize` y `from src.ui.ui_helpers import nav_icon, tint_icon, set_role`
- [ ] En `_nav()`: `btn.setIcon(nav_icon(icon))` y `btn.setIconSize(QSize(18, 18))`
- [ ] Agregar marca arriba del sidebar (icono escudo + "Guardián EPP"):

```python
brand = QHBoxLayout()
brand.setContentsMargins(6, 0, 0, 10)
logo = QLabel()
logo.setPixmap(tint_icon(icon_shield(), "#0078d4", 22).pixmap(22, 22))
name = QLabel("Guardián EPP")
set_role(name, "brand")
brand.addWidget(logo)
brand.addWidget(name)
brand.addStretch()
sb.addLayout(brand)
```

- [ ] Versión sin estilo inline:

```python
ver = QLabel("v1.0  MVP")
set_role(ver, "caption")
```

- [ ] Título de ventana: "Guardián EPP — Seguridad Industrial"

### 3.2 `settings_view.py`

- [ ] `_section_label` → `set_role(lbl, "section")` (quitar el estilo inline azul)
- [ ] Labels de campo ("Fuente de video", "Umbral de confianza", "Cooldown voz", "Puerto serial", etc.) → rol `field`
- [ ] `lbl_conf` → rol `value-sm` (quitar `setStyleSheet`)
- [ ] En cada grid: `g.setColumnMinimumWidth(0, 220)` y `g.setColumnStretch(1, 1)`
- [ ] Spinboxes con `setMaximumWidth(140)`
- [ ] Limitar el ancho de cada tarjeta: `cardN.setMaximumWidth(760)`
- [ ] Botón guardar alineado a la derecha, sin ocupar todo el ancho:

```python
foot = QHBoxLayout()
foot.addStretch()
foot.addWidget(btn_save)
main.addLayout(foot)
```

- [ ] Reemplazar `QMessageBox.information("Guardado")` por toast:

```python
from src.ui.ui_helpers import Toast
self.toast = Toast(self)                       # en __init__
self.toast.show_message("Ajustes guardados")   # en _save_settings
self.toast.show_message("No se pudo guardar", "bad")  # en el except
```

- [ ] Acentos: "Detección", "Temporalidad", "Frames para confirmar violación", "Síntesis de voz", "Relé serial (Arduino)", "Guardar ajustes"

### 3.3 `rules_editor.py`

- [ ] `profile_header` → rol `section` (quitar estilo inline azul)
- [ ] "Perfiles de zona" → rol `section`; "EPP obligatorio" y "Mensaje de advertencia" → rol `field`
- [ ] Quitar `sep.setStyleSheet("color: #e0e0e0;")` (el QSS global ya estiliza el separador)
- [ ] Reemplazar `QMessageBox.information` de guardado por `Toast`
- [ ] Deshabilitar el botón "Eliminar" mientras no haya perfil seleccionado
- [ ] Acentos: "Atención", "Protección", "Se mostrará y reproducirá por voz"

### 3.4 `events_view.py`

- [ ] Configurar la tabla:

```python
self.table.verticalHeader().setVisible(False)
self.table.setShowGrid(False)
self.table.setAlternatingRowColors(True)
self.table.verticalHeader().setDefaultSectionSize(34)
self.table.setFocusPolicy(Qt.NoFocus)
```

- [ ] Encabezados: "Hora", "Cámara", "Zona", "Persona", "Infracción", "Regla", "Relé"
- [ ] Reemplazar `Qt.darkRed` / `Qt.darkGreen` por la paleta de la UI:

```python
from PySide6.QtGui import QColor
STATE_COLOR = {"Bloqueado": "#d13438", "Advertencia": "#9d5d00", "Activo": "#107c10"}
color = STATE_COLOR.get(relay)
if color:
    items[4].setForeground(QColor(color))
    items[6].setForeground(QColor(color))
```

- [ ] Quitar `_load_sample_data()` o ponerlo detrás de `DEMO_DATA = False` (hoy el historial arranca con 5 eventos falsos)
- [ ] Llenar el combo de zonas desde `zones.json` en vez de tener "SOLDADURA / LABORATORIO / GENERAL" fijos
- [ ] Mostrar un texto de estado vacío cuando no hay registros

### 3.5 `zone_editor.py`

- [ ] En `ZoneCanvas.__init__`: reemplazar el `setStyleSheet` inline por `self.setObjectName("ZoneCanvas")`
- [ ] Texto vacío del lienzo: "Sin imagen de referencia. Conecta una cámara en Monitoreo." (el actual menciona una simulación que ya no existe)
- [ ] `hint` → rol `caption`; `lbl_points` → rol `field` (quitar estilos inline)
- [ ] Labels "Cámara", "Zonas guardadas", "Nombre", "Perfil" → rol `field`
- [ ] Color por perfil en las zonas guardadas:

```python
PROFILE_COLORS = {
    "SOLDADURA":   (209, 52, 56),
    "LABORATORIO": (16, 124, 16),
    "GENERAL":     (0, 120, 212),
}
r, g, b = PROFILE_COLORS.get(zone.get("perfil"), (0, 120, 212))
painter.setBrush(QBrush(QColor(r, g, b, 40)))
painter.setPen(QPen(QColor(r, g, b), 2, Qt.SolidLine))
```

- [ ] Opcional: al seleccionar una zona en la lista, resaltarla en el lienzo

### 3.6 Monitoreo (`monitor.py`, pendiente de revisar)

- [ ] Reemplazar el texto suelto "-- fps  Sin señal  Relé inactivo" por tres `StatusChip`:

```python
from src.ui.ui_helpers import StatusChip
self.chip_signal.set_status("Sin señal", "bad")
self.chip_signal.set_status("Transmisión activa", "ok")
self.chip_relay.set_status("Relé inactivo", "idle")
self.chip_relay.set_status("Relé bloqueado", "bad")
```

- [ ] Quitar el cuadro blanco vacío debajo de "Sin señal" si no es intencional
- [ ] "Personas" / "Infracciones": etiquetas con rol `caption`, números con rol `value`; `state="bad"` cuando infracciones > 0
- [ ] Lista de "Eventos recientes": texto de estado vacío ("Sin eventos recientes", rol `muted`)
- [ ] Nombres de EPP (Careta, Chaleco, Guantes, Casco): sin fondo gris, con el icono de estado alineado

---

## 4. Detalles funcionales detectados

- [ ] `EventsView.add_event()` no se llama desde ningún lado: el historial no recibe infracciones reales del `VideoWorker`. Conectar las alertas de `meta["alerts"]` a `add_event`.
- [ ] `SettingsView.settings_changed` no está conectado, y `video_worker` usa `conf=0.30` fijo: el slider de confianza no tiene efecto.
- [ ] `temporal` en `video_worker` usa `grace_period_sec=1.5, min_consecutive_frames=4` fijos: el ajuste "Frames para confirmar violación" tampoco se aplica.

---

## 5. Orden sugerido de aplicación

1. Copiar `styles.py`, `ui_helpers.py` y los dos SVG. Ejecutar la app y comprobar que ya no hay fondos grises en las labels.
2. Aplicar los cambios de `app.py` (nav con iconos de dos estados y marca).
3. Aplicar roles y acentos en `settings_view.py`, `rules_editor.py` y `zone_editor.py`.
4. Ajustar la tabla de `events_view.py` y quitar los datos de ejemplo.
5. Pasar `monitor.py` e `icons.py` para cerrar el Monitoreo con chips.
6. Conectar eventos y ajustes (sección 4).

---

## 6. Notas técnicas

- Los selectores de propiedad (`[role="..."]`, `[class="..."]`) requieren que la propiedad esté asignada antes de mostrar el widget, o llamar a `set_role` / `set_state`, que repulen el estilo.
- `nav_icon` y `tint_icon` asumen iconos de un solo color. Si algún icono SVG usa varios colores, se perderán al teñir.
- Las rutas de `chevron-down.svg` y `check.svg` se calculan desde `styles.py` (`parents[2]`). Si `styles.py` no está en `src/ui/`, ajusta ese índice en `_ICONS`.