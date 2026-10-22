"""
UI PROPUESTA v3 — Guardián EPP (mockup de diseño, sin backend)
==============================================================

Propuesta de rediseño para reemplazar la ventana de main.py.
Mismo stack (PySide6) y mismas 5 vistas, con concepto revisado:

  "Neutral claro, menos es más"

Decisiones de diseño (v3, tras feedback):
  - Paleta neutra a base de blanco y grises; sin neón ni colores
    fuertes. El acento único es gris carbón (#24292f), estilo
    GitHub/Vercel: la jerarquía se construye con tipografía,
    espaciado y peso, no con color.
  - El color solo aparece donde hay semántica real (estado OK,
    advertencia, alerta) y siempre en tintes suaves con texto
    apagado, nunca en rellenos saturados.
  - Visor como placeholder vacío ("Sin señal"): la vista comunica
    con el checklist de zona, los chips y el ticker, no con
    decoración sobre el video.
  - Sin emojis ni iconografía decorativa; navegación por texto.
  - Menos bordes y elementos: tarjetas blancas con borde 1px,
    filas alternas, mucho aire entre bloques.

Alcance: la navegación funciona (rail + QStackedWidget) y los
controles responden visualmente, pero no hay backend: es una
propuesta de diseño.

Ejecutar desde la raíz del proyecto:
    python demo/ui_propuesta.py
"""

import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QPushButton, QScrollArea, QSpinBox, QSlider, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

# ── Paleta neutral (única fuente de verdad del look) ─────────────
BG        = "#f7f8f9"   # fondo de app
PANEL     = "#ffffff"   # tarjetas
PANEL_2   = "#f6f8fa"   # inputs, filas, tiles
PANEL_3   = "#eef1f4"   # hover / item activo del rail
BORDER    = "#e4e7eb"
TXT       = "#1f2328"
TXT_DIM   = "#6e7781"
TXT_FNT   = "#8b949e"
CARBON    = "#24292f"   # acento único (primario / selección)
CARBON_HV = "#57606a"

# Estados: solo donde hay semántica; tintes suaves + texto apagado
OK_TXT, OK_BG, OK_BD = "#1a7f37", "#f0f7f1", "#d6e8da"
WA_TXT, WA_BG, WA_BD = "#8a6d1f", "#faf5e8", "#ede2c8"
AL_TXT, AL_BG, AL_BD = "#b04a42", "#fdf2f2", "#f0d9d7"

# ── Tema QSS global ──────────────────────────────────────────────
LIGHT_QSS = f"""
QWidget {{
    background-color: {BG}; color: {TXT};
    font-family: 'Segoe UI'; font-size: 13px;
}}
QMainWindow {{ background-color: {BG}; }}

/* ── Barra superior ── */
#Header {{ background-color: {PANEL};
           border-bottom: 1px solid {BORDER}; }}
#Brand    {{ font-size: 15px; font-weight: 700; }}
#BrandSub {{ color: {TXT_FNT}; font-size: 10px; }}

/* ── Chips de estado (tinte suave + texto apagado) ── */
QLabel[chip="ok"] {{
    background: {OK_BG}; color: {OK_TXT};
    border: 1px solid {OK_BD}; border-radius: 10px;
    padding: 2px 10px; font-size: 11px; font-weight: 600;
}}
QLabel[chip="warn"] {{
    background: {WA_BG}; color: {WA_TXT};
    border: 1px solid {WA_BD}; border-radius: 10px;
    padding: 2px 10px; font-size: 11px; font-weight: 600;
}}
QLabel[chip="alert"] {{
    background: {AL_BG}; color: {AL_TXT};
    border: 1px solid {AL_BD}; border-radius: 10px;
    padding: 2px 10px; font-size: 11px; font-weight: 600;
}}
QLabel[chip="dim"] {{
    background: {PANEL_2}; color: {TXT_DIM};
    border: 1px solid {BORDER}; border-radius: 10px;
    padding: 2px 10px; font-size: 11px; font-weight: 600;
}}

/* ── Rail de navegación (texto, sin iconos) ── */
#Rail {{ background-color: {PANEL};
         border-right: 1px solid {BORDER}; }}
QPushButton[rail="true"] {{
    background: transparent; color: {TXT_DIM};
    border: none; border-radius: 6px;
    text-align: left; padding: 9px 14px;
    font-size: 13px; font-weight: 600; margin: 2px 10px;
}}
QPushButton[rail="true"]:hover {{ background: {PANEL_2};
                                  color: {TXT}; }}
QPushButton[rail="true"]:checked {{
    background: {PANEL_3}; color: {TXT};
}}

/* ── Tarjetas y tiles ── */
#Card {{ background-color: {PANEL};
         border: 1px solid {BORDER}; border-radius: 8px; }}
#Tile {{ background-color: {PANEL_2};
         border: 1px solid {BORDER}; border-radius: 8px; }}
#CardTitle {{ color: {TXT_DIM}; font-size: 11px;
              font-weight: 600; }}
#Placeholder {{ background-color: {PANEL_2};
                border: 1px solid {BORDER}; border-radius: 8px; }}
#PlaceholderMsg {{ color: {TXT_DIM}; font-size: 14px;
                   font-weight: 600; background: transparent; }}
#PlaceholderSub {{ color: {TXT_FNT}; font-size: 11px;
                   background: transparent; }}

/* ── Botones ── */
QPushButton {{
    background-color: {PANEL}; color: {TXT};
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 6px 14px; font-weight: 600; font-size: 12px;
}}
QPushButton:hover {{ border-color: {CARBON_HV};
                     background-color: {PANEL_2}; }}
QPushButton[primary="true"] {{
    background-color: {CARBON}; border: none; color: {PANEL};
}}
QPushButton[primary="true"]:hover {{
    background-color: {CARBON_HV};
}}
QPushButton[danger="true"] {{
    background: {PANEL}; border: 1px solid {AL_BD};
    color: {AL_TXT};
}}
QPushButton[danger="true"]:hover {{ background: {AL_BG}; }}

/* ── Ticker de eventos ── */
#Ticker {{ background-color: {PANEL};
           border-top: 1px solid {BORDER}; }}
#DotAlert {{ background: {AL_TXT}; border-radius: 4px; }}

/* ── Controles de formulario ── */
QComboBox, QLineEdit, QSpinBox {{
    background-color: {PANEL}; color: {TXT};
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 5px 10px;
}}
QComboBox:hover, QLineEdit:focus, QSpinBox:focus {{
    border-color: {CARBON_HV};
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL}; color: {TXT};
    border: 1px solid {BORDER};
    selection-background-color: {PANEL_3};
}}
QCheckBox {{ spacing: 8px; color: {TXT}; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {BORDER}; background: {PANEL};
}}
QCheckBox::indicator:hover {{ border-color: {CARBON_HV}; }}
QCheckBox::indicator:checked {{
    background: {CARBON}; border-color: {CARBON};
}}
QSlider::groove:horizontal {{ height: 4px;
    background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {CARBON};
    border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {PANEL};
    border: 1px solid {BORDER}; width: 13px; height: 13px;
    margin: -5px 0; border-radius: 7px; }}

/* ── Tablas ── */
QTableWidget {{
    background-color: {PANEL}; border: 1px solid {BORDER};
    border-radius: 8px; gridline-color: {BORDER};
    alternate-background-color: {PANEL_2};
}}
QHeaderView::section {{
    background-color: {PANEL_2}; color: {TXT_DIM};
    border: none; border-bottom: 1px solid {BORDER};
    padding: 7px 10px; font-weight: 600; font-size: 11px;
}}
QTableWidget::item {{ padding: 6px 10px; }}
QTableWidget::item:selected {{ background: {PANEL_3};
    color: {TXT}; }}

/* ── Scroll ── */
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {BORDER};
    border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{ background: {BORDER};
    border-radius: 4px; min-width: 24px; }}
"""


# ── Utilidades visuales ──────────────────────────────────────────
def chip(text, kind="dim"):
    """Etiqueta de estado tipo píldora sobria."""
    lbl = QLabel(text)
    lbl.setProperty("chip", kind)
    return lbl


def card(title=None):
    """Tarjeta blanca con título opcional."""
    frame = QFrame()
    frame.setObjectName("Card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    if title:
        t = QLabel(title)
        t.setObjectName("CardTitle")
        lay.addWidget(t)
    return frame, lay


def placeholder(msg, sub):
    """Visor vacío: rectángulo gris con mensaje centrado."""
    frame = QFrame()
    frame.setObjectName("Placeholder")
    lay = QVBoxLayout(frame)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setSpacing(4)
    m = QLabel(msg)
    m.setObjectName("PlaceholderMsg")
    m.setAlignment(Qt.AlignmentFlag.AlignCenter)
    s = QLabel(sub)
    s.setObjectName("PlaceholderSub")
    s.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(m)
    lay.addWidget(s)
    return frame


def persona_row(pid, epp_ok, epp_missing, regla="R2"):
    """Fila de checklist: ID + chips de EPP + regla aplicada."""
    row = QHBoxLayout()
    row.setSpacing(6)
    name = QLabel(f"Persona #{pid}")
    name.setStyleSheet("font-weight: 600; background: transparent;")
    row.addWidget(name)
    row.addStretch()
    for e in epp_ok:
        row.addWidget(chip(f"{e}: ok", "ok"))
    for e in epp_missing:
        row.addWidget(chip(f"{e}: falta", "alert"))
    row.addWidget(chip(f"regla {regla}", "dim"))
    wrap = QWidget()
    wrap.setLayout(row)
    return wrap


def tile(label, value):
    """Mini-tarjeta de estadística (Personas, FPS...)."""
    frame = QFrame()
    frame.setObjectName("Tile")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(2)
    lbl = QLabel(label)
    lbl.setObjectName("CardTitle")
    val = QLabel(value)
    f = val.font()
    f.setPointSize(15)
    f.setBold(True)
    val.setFont(f)
    lay.addWidget(lbl)
    lay.addWidget(val)
    return frame


# ── VISTA 1: Monitoreo ───────────────────────────────────────────
class MonitorView(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(12)

        body = QHBoxLayout()
        body.setSpacing(14)

        # -- visor: placeholder vacío, sin decoración --
        visor = placeholder("Sin señal",
                            "Conecte una fuente para iniciar el "
                            "monitoreo")
        body.addWidget(visor, stretch=3)

        # -- panel derecho: estado de la zona --
        panel, pl = card("Zona · Estación de soldadura")
        panel.setMaximumWidth(340)
        pl.addWidget(chip("Incumplimiento", "alert"))
        pl.addWidget(persona_row(3, ["careta"], [], regla="R1"))
        pl.addWidget(persona_row(7, ["careta"], ["chaleco"],
                                 regla="R2"))

        stats = QGridLayout()
        stats.setSpacing(8)
        stats.addWidget(tile("Personas", "2"), 0, 0)
        stats.addWidget(tile("FPS", "28"), 0, 1)
        stats.addWidget(tile("Objetos", "5"), 1, 0)
        stats.addWidget(tile("Cámara", "OK"), 1, 1)
        pl.addLayout(stats)

        pl.addWidget(chip("Reglas activas: R1, R2, R3, R4", "dim"))
        pl.addStretch()

        btns = QHBoxLayout()
        btns.addWidget(QPushButton("Silenciar voz 30 s"))
        btn_rel = QPushButton("Desbloquear relé")
        btn_rel.setProperty("danger", "true")
        btns.addWidget(btn_rel)
        pl.addLayout(btns)

        body.addWidget(panel)
        root.addLayout(body, stretch=1)

        # -- ticker: trazabilidad siempre visible --
        ticker = QFrame()
        ticker.setObjectName("Ticker")
        tl = QHBoxLayout(ticker)
        tl.setContentsMargins(20, 8, 20, 8)
        tl.setSpacing(10)
        dot = QLabel()
        dot.setObjectName("DotAlert")
        dot.setFixedSize(8, 8)
        tl.addWidget(dot)
        ev = QLabel("14:32:05   P#7 falta chaleco (SOLDADURA)"
                    "   regla R2   relé bloqueado")
        ev.setStyleSheet("font-family: Consolas; font-size: 12px;")
        tl.addWidget(ev)
        tl.addStretch()
        ver = QPushButton("Ver historial")
        ver.setFlat(True)
        tl.addWidget(ver)
        root.addWidget(ticker)


# ── VISTA 2: Configuración de zonas ──────────────────────────────
class ZonasView(QWidget):
    def __init__(self):
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        left, ll = card("Lienzo de zonas")
        canvas = placeholder("Frame sin fuente",
                             "Al haber señal, haga clic para "
                             "colocar vértices")
        ll.addWidget(canvas, stretch=1)
        bar = QHBoxLayout()
        b1 = QPushButton("Dibujar zona")
        b1.setProperty("primary", "true")
        bar.addWidget(b1)
        bar.addWidget(QPushButton("Editar"))
        bar.addWidget(QPushButton("Eliminar"))
        bar.addStretch()
        bar.addWidget(QPushButton("Guardar zonas"))
        ll.addLayout(bar)
        root.addWidget(left, stretch=3)

        right, rl = card("Zonas de CAM-01")
        right.setMaximumWidth(300)
        for nombre, perfil, verts in [
                ("Estación de soldadura", "SOLDADURA", 4),
                ("Pasillo general", "GENERAL", 4),
                ("Área de pruebas", "LABORATORIO", 6)]:
            z = QWidget()
            zl = QHBoxLayout(z)
            zl.setContentsMargins(0, 6, 0, 6)
            zl.setSpacing(8)
            n = QLabel(nombre)
            n.setStyleSheet("background: transparent;")
            zl.addWidget(n)
            zl.addStretch()
            zl.addWidget(chip(perfil.lower(), "dim"))
            zl.addWidget(chip(f"{verts} v", "dim"))
            rl.addWidget(z)
        rl.addStretch()
        hint = QLabel("Consejo: cierre el polígono con doble clic "
                      "para terminarlo.")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color: {0}; font-size: 11px;".format(TXT_FNT))
        rl.addWidget(hint)
        root.addWidget(right)


# ── VISTA 3: Perfiles de EPP (matriz perfil x EPP) ───────────────
class PerfilesView(QWidget):
    EPPS = ["helmet", "vest", "welding_mask", "mask",
            "glasses", "gloves", "boots"]
    MATRIZ = {   # espejo de config/rules.json
        "SOLDADURA":   {"welding_mask", "vest", "gloves"},
        "SMT":         {"glasses", "boots"},
        "LABORATORIO": {"mask", "glasses"},
        "GENERAL":     {"helmet", "vest"},
        "BODEGA":      set(),
    }

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        head, hl = card("Perfiles de EPP por zona")
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        grid.addWidget(QLabel(""), 0, 0)
        for c, epp in enumerate(self.EPPS, start=1):
            h = QLabel(epp)
            h.setObjectName("CardTitle")
            grid.addWidget(h, 0, c)

        for r, (perfil, reqs) in enumerate(self.MATRIZ.items(),
                                           start=1):
            lbl = QLabel(perfil)
            lbl.setStyleSheet("font-weight: 600;")
            grid.addWidget(lbl, r, 0)
            for c, epp in enumerate(self.EPPS, start=1):
                cb = QCheckBox()
                cb.setChecked(epp in reqs)
                wrap = QWidget()
                wl = QHBoxLayout(wrap)
                wl.setContentsMargins(0, 0, 0, 0)
                wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                wl.addWidget(cb)
                grid.addWidget(wrap, r, c)
        hl.addLayout(grid)
        root.addWidget(head, stretch=1)

        foot = QHBoxLayout()
        foot.addWidget(chip("Los cambios aplican sin reentrenar "
                            "el modelo", "dim"))
        foot.addStretch()
        btn_guardar = QPushButton("Guardar perfiles")
        btn_guardar.setProperty("primary", "true")
        foot.addWidget(btn_guardar)
        foot.addWidget(QPushButton("Restaurar"))
        root.addLayout(foot)


# ── VISTA 4: Eventos y reportes ──────────────────────────────────
class EventosView(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        filtros = QHBoxLayout()
        filtros.setSpacing(8)
        cb_z = QComboBox()
        cb_z.addItems(["Todas las zonas", "SOLDADURA", "GENERAL",
                       "LABORATORIO"])
        cb_t = QComboBox()
        cb_t.addItems(["Todos", "Violación", "Alarma",
                       "Liberación"])
        buscar = QLineEdit()
        buscar.setPlaceholderText(
            "Buscar por persona o regla...")
        buscar.setMaximumWidth(220)
        btn = QPushButton("Filtrar")
        btn.setProperty("primary", "true")
        filtros.addWidget(cb_z)
        filtros.addWidget(cb_t)
        filtros.addWidget(buscar)
        filtros.addWidget(btn)
        filtros.addStretch()
        filtros.addWidget(chip("1,284 eventos · 30 días", "dim"))
        root.addLayout(filtros)

        tabla = QTableWidget(5, 6)
        tabla.setHorizontalHeaderLabels(
            ["Hora", "Zona", "Persona", "Detalle", "Regla",
             "Evidencia"])
        datos = [
            ["14:32:05", "SOLDADURA", "P#7", "Falta chaleco",
             "R2", "captura_1432.png"],
            ["14:31:44", "SOLDADURA", "P#3", "Falta careta",
             "R1", "captura_1431.png"],
            ["14:30:02", "GENERAL", "P#2", "Cumple",
             "OK", "-"],
            ["14:28:57", "SOLDADURA", "P#7", "Zona liberada",
             "R4", "-"],
            ["14:27:31", "LABORATORIO", "P#5", "Falta mascarilla",
             "R1", "captura_1427.png"],
        ]
        for r, fila in enumerate(datos):
            for c, texto in enumerate(fila):
                item = QTableWidgetItem(texto)
                if c == 0:
                    item.setForeground(QColor(TXT_FNT))
                tabla.setItem(r, c, item)
        tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        tabla.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        root.addWidget(tabla, stretch=1)

        foot = QHBoxLayout()
        foot.addWidget(QPushButton("Exportar CSV"))
        foot.addWidget(QPushButton("Exportar PDF"))
        foot.addStretch()
        foot.addWidget(QPushButton("Ver captura..."))
        root.addLayout(foot)


# ── VISTA 5: Ajustes ─────────────────────────────────────────────
class AjustesView(QWidget):
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        contenido = QWidget()
        root = QVBoxLayout(contenido)
        root.setSpacing(12)

        c1, l1 = card("Cámaras")
        fila1 = QHBoxLayout()
        fila1.setSpacing(10)
        combo = QComboBox()
        combo.addItems(["CAM-01 · webcam (0)",
                        "CAM-02 · RTSP rtsp://...",
                        "Archivo de video..."])
        fila1.addWidget(QLabel("Fuente activa:"))
        fila1.addWidget(combo)
        fila1.addStretch()
        fila1.addWidget(QCheckBox("Reconexión automática"))
        l1.addLayout(fila1)
        root.addWidget(c1)

        c2, l2 = card("Detección")
        g2 = QGridLayout()
        g2.setHorizontalSpacing(12)
        g2.setVerticalSpacing(10)
        g2.addWidget(QLabel("Umbral de confianza"), 0, 0)
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(5, 95)
        sl.setValue(35)
        val = QLabel("0.35")
        g2.addWidget(sl, 0, 1)
        g2.addWidget(val, 0, 2)
        g2.addWidget(QLabel("Tiempo de gracia (s)"), 1, 0)
        g2.addWidget(QSpinBox(), 1, 1)
        g2.addWidget(QLabel("Frames para confirmar"), 2, 0)
        g2.addWidget(QSpinBox(), 2, 1)
        g2.setColumnStretch(1, 1)
        l2.addLayout(g2)
        root.addWidget(c2)

        c3, l3 = card("Alertas")
        g3 = QGridLayout()
        g3.setHorizontalSpacing(24)
        g3.setVerticalSpacing(10)
        g3.addWidget(QCheckBox("Voz (aviso hablado)"), 0, 0)
        g3.addWidget(QCheckBox("Sonido"), 0, 1)
        g3.addWidget(QCheckBox("WhatsApp"), 1, 0)
        g3.addWidget(QCheckBox("Telegram"), 1, 1)
        g3.addWidget(QCheckBox("Relé / Arduino"), 2, 0)
        g3.addWidget(QCheckBox("Guardar captura"), 2, 1)
        l3.addLayout(g3)
        fila3 = QHBoxLayout()
        fila3.setSpacing(10)
        fila3.addWidget(QLabel("Puerto serial:"))
        puerto = QLineEdit("/dev/ttyUSB0")
        puerto.setMaximumWidth(140)
        fila3.addWidget(puerto)
        fila3.addStretch()
        fila3.addWidget(QPushButton("Probar relé"))
        l3.addLayout(fila3)
        root.addWidget(c3)

        c4, l4 = card("Sistema")
        fila4 = QHBoxLayout()
        fila4.addWidget(
            QCheckBox("Procesar solo localmente (sin nube)"))
        fila4.addStretch()
        fila4.addWidget(QPushButton("Exportar configuración"))
        fila4.addWidget(QPushButton("Restaurar default"))
        l4.addLayout(fila4)
        ver = QLabel("Guardián EPP · propuesta UI v3 · "
                     "mockup sin backend")
        ver.setStyleSheet(
            "color: {0}; font-size: 11px;".format(TXT_FNT))
        l4.addWidget(ver)
        root.addWidget(c4)
        root.addStretch()

        scroll.setWidget(contenido)
        outer.addWidget(scroll)


# ── Ventana principal: header + rail + stack ─────────────────────
class MainWindow(QMainWindow):
    VISTAS = ["Monitoreo", "Zonas", "Perfiles", "Eventos",
              "Ajustes"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardián EPP — Propuesta de UI v3")
        self.resize(1280, 800)
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(LIGHT_QSS)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._header())

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self._rail())
        self.stack = QStackedWidget()
        for vista in (MonitorView, ZonasView, PerfilesView,
                      EventosView, AjustesView):
            self.stack.addWidget(vista())
        cuerpo.addWidget(self.stack, stretch=1)
        root.addLayout(cuerpo, stretch=1)

        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)
        self._switch(0)
        self._tick()

    def _header(self):
        h = QFrame()
        h.setObjectName("Header")
        h.setFixedHeight(56)
        lay = QHBoxLayout(h)
        lay.setContentsMargins(20, 8, 20, 8)
        lay.setSpacing(10)

        marca = QVBoxLayout()
        marca.setSpacing(0)
        t = QLabel("Guardián EPP")
        t.setObjectName("Brand")
        s = QLabel("Seguridad industrial")
        s.setObjectName("BrandSub")
        marca.addWidget(t)
        marca.addWidget(s)
        lay.addLayout(marca)
        lay.addSpacing(24)
        lay.addWidget(chip("Incumplimiento", "alert"))
        lay.addWidget(chip("1 zona en alerta", "warn"))
        lay.addStretch()

        self.hora = QLabel()
        self.hora.setStyleSheet(
            "font-family: Consolas; font-size: 14px;"
            "color: {0};".format(TXT_DIM))
        lay.addWidget(self.hora)
        lay.addWidget(QPushButton("Silenciar"))
        emer = QPushButton("Emergencia")
        emer.setProperty("danger", "true")
        lay.addWidget(emer)
        return h

    def _rail(self):
        rail = QFrame()
        rail.setObjectName("Rail")
        rail.setFixedWidth(190)
        lay = QVBoxLayout(rail)
        lay.setContentsMargins(8, 16, 8, 16)
        lay.setSpacing(2)
        self.botones = []
        for i, nombre in enumerate(self.VISTAS):
            b = QPushButton(nombre)
            b.setProperty("rail", "true")
            b.setCheckable(True)
            b.clicked.connect(
                lambda _=False, idx=i: self._switch(idx))
            lay.addWidget(b)
            self.botones.append(b)
        lay.addStretch()
        ver = QLabel("propuesta v3")
        ver.setStyleSheet(
            "color: {0}; font-size: 10px; padding: 6px;"
            .format(TXT_FNT))
        lay.addWidget(ver)
        return rail

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.botones):
            b.setChecked(i == idx)

    def _tick(self):
        self.hora.setText(datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    if "--smoke" in sys.argv:  # prueba headless sin abrir ventana
        from PySide6.QtCore import QTimer as _T
        app = QApplication(sys.argv)
        w = MainWindow()
        w.show()
        _T.singleShot(500, app.quit)
        sys.exit(app.exec())
    app = QApplication(sys.argv)
    app.setApplicationName("Guardián EPP — Propuesta UI")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
