# Guardián de Seguridad y EPP 🛡️🥽

*Sistema neuro-simbólico para verificar en tiempo real que el personal cumple con su Equipo de Protección Personal (EPP) dentro de zonas de riesgo delimitadas.*

---

## 📌 Descripción

Guardián EPP analiza el video de una o varias cámaras, detecta personas y su EPP, determina **en qué zona** se encuentra cada persona y evalúa si cumple la **normativa de esa zona**. Si no cumple, genera alertas (pantalla, voz, relé/Arduino, mensajería) y deja un registro auditable con evidencia.

Proyecto académico (Inteligencia Artificial) con diseño orientado a convertirse en producto comercial.

**Idea central:** la visión detecta *qué hay*; las reglas deciden *qué significa*.

---

## 🧠 Arquitectura neuro-simbólica

```text
Cámara ─▶ [1] Detector + Tracker ─▶ [2] Asociación persona↔EPP ─▶ [3] Ubicación en zona
                (conexionista)              (geométrica)               (geométrica)
                                                                            │
         Alertas / Relé / Log  ◀─ [5] Temporalidad (anti-parpadeo) ◀─ [4] Motor de reglas
                                                                         (simbólico)
```

### Módulo conexionista (percepción)
- **Modelo:** detector de objetos (YOLO) con tracking (ByteTrack) para asignar un ID estable a cada persona.
- **Clases a detectar (solo elementos presentes):** `person`, `helmet`, `vest`, `mask`, `glasses`, `gloves`, `welding_mask`, `boots` (según el cliente).
- **Decisión de diseño:** NO entrenar clases del tipo "sin casco". Es más robusto detectar lo que existe y que el sistema simbólico **deduzca la ausencia**: *persona detectada Y no hay casco asociado → falta casco*.

### Módulo geométrico (puente entre ambos mundos)
1. **Asociación persona↔EPP:** un EPP pertenece a una persona si su centro cae dentro de la caja de la persona y en la región esperada (casco: tercio superior; chaleco: zona media; botas: tercio inferior).
2. **Ubicación en zona:** se toma el punto de los pies (centro inferior de la caja) y se evalúa con `cv2.pointPolygonTest` contra cada polígono de zona.

### Módulo simbólico (sistema experto)
Reglas explícitas, editables sin reentrenar nada:

```text
R1: SI persona EN zona(SOLDADURA) Y NO tiene(welding_mask) ENTONCES violación("falta careta")
R2: SI persona EN zona(SOLDADURA) Y NO tiene(vest)          ENTONCES violación("falta chaleco")
R3: SI violaciones(persona) > 0 Y duración > 2 s            ENTONCES alarma + bloquear relé
R4: SI zona sin personas durante 10 s                        ENTONCES estado = LIBRE
R5: SI persona fuera de toda zona                            ENTONCES ignorar
```

Cada decisión guarda **qué regla se disparó y con qué hechos** → explicabilidad y trazabilidad completas (clave para la materia y para auditorías del cliente).

### Módulo temporal
Una violación solo se confirma tras **N frames consecutivos** (o X segundos). Evita falsas alarmas por oclusiones o detecciones intermitentes.

---

## 🖥️ Interfaz

### Pantallas
1. **Monitoreo (principal):** video con zonas dibujadas, cajas coloreadas, semáforo de estado, checklist por zona, registro de eventos.
2. **Configuración de zonas:** el usuario hace clic sobre un frame de la cámara para dibujar polígonos, les asigna nombre y perfil de reglas.
3. **Perfiles de EPP:** editor de reglas por zona (casillas: qué EPP es obligatorio).
4. **Eventos y reportes:** historial filtrable con capturas, exportación a CSV/PDF.
5. **Ajustes:** cámaras, umbral de confianza, tiempo de gracia, voz, Arduino, notificaciones.

### Layout de monitoreo

```text
┌──────────────────────────────────────────────────────────────┐
│ 🛡️ Guardián EPP     Cámara: [Taller 1 ▼]   🟢 OK   ⚙ Config │
├────────────────────────────────────┬─────────────────────────┤
│                                    │  ZONA: SOLDADURA        │
│   VIDEO EN VIVO                    │  ┌───────────────────┐  │
│   - polígonos de zona              │  │  ❌ INCUMPLIMIENTO │  │
│   - cajas verde/rojo por persona   │  └───────────────────┘  │
│   - ID de persona                  │  Persona #3             │
│                                    │  ✅ Careta  ❌ Chaleco  │
│                                    │  REGLA: R2              │
│                                    │  Personas: 2  FPS: 28   │
├────────────────────────────────────┴─────────────────────────┤
│ 14:32:05 ⚠ #3 falta chaleco (SOLDADURA) → relé BLOQUEADO     │
└──────────────────────────────────────────────────────────────┘
```

### Tecnología sugerida
- **Prototipo académico:** PySide6 + OpenCV.
- **Versión comercial:** backend Python (FastAPI) + dashboard web (React). El video procesa en el equipo local y el navegador solo muestra resultados.

---

## 📁 Estructura del proyecto

```text
guardian-epp/
├── config/
│   ├── zones.json            # Polígonos de zonas por cámara
│   ├── rules.json            # Perfiles de EPP por zona
│   └── classes.json          # Mapeo clase del modelo → nombre en español
├── models/
│   └── ppe_best.pt           # Pesos entrenados
├── src/
│   ├── camera.py             # Captura (webcam / RTSP / archivo)
│   ├── detector.py           # Inferencia + tracking
│   ├── association.py        # Persona ↔ EPP
│   ├── zones.py              # Polígonos y punto-en-zona
│   ├── rule_engine.py        # Motor de reglas + explicación
│   ├── temporal.py           # Confirmación de violaciones
│   ├── alert_system.py       # Voz, sonido, relé, notificaciones
│   ├── storage.py            # SQLite: eventos y capturas
│   └── ui/
│       ├── monitor.py
│       └── zone_editor.py
├── training/
│   ├── data.yaml
│   ├── train.py
│   └── README_training.md
├── tests/
│   ├── test_rules.py
│   ├── test_zones.py
│   └── test_association.py
├── main.py
└── requirements.txt
```

### Ejemplo de `zones.json`

```json
{
  "camara_0": [
    {
      "nombre": "Estación de soldadura",
      "perfil": "SOLDADURA",
      "poligono": [[120, 80], [540, 90], [560, 400], [100, 390]]
    },
    {
      "nombre": "Pasillo general",
      "perfil": "GENERAL",
      "poligono": [[560, 90], [900, 100], [900, 400], [560, 400]]
    }
  ]
}
```

### Ejemplo de `rules.json` (nombres internos en inglés, mensajes en español)

```json
{
  "SOLDADURA": {
    "requeridos": ["welding_mask", "vest", "gloves"],
    "mensaje": "Se requiere careta, chaleco y guantes."
  },
  "LABORATORIO": {
    "requeridos": ["mask", "glasses"],
    "mensaje": "Se requiere mascarilla y lentes."
  },
  "GENERAL": {
    "requeridos": ["helmet", "vest"],
    "mensaje": "Se requiere casco y chaleco."
  }
}
```

> Usa los mismos identificadores (`helmet`, `vest`...) en el dataset, en `classes.json` y en `rules.json`. Así evitas el desajuste entre nombres.

---

## 📦 Dataset: de dónde obtenerlo

| Fuente | Qué ofrece | Notas |
|---|---|---|
| **Roboflow Universe** | Muchos datasets de PPE ya etiquetados, descargables en formato YOLO | Busca "PPE detection", "construction site safety", "hard hat". Revisa la **licencia** de cada uno |
| **Kaggle** | Hard Hat Workers, Safety Helmet Detection y otros | Verifica licencia y calidad de etiquetas |
| **SHWD / CHV / Pictor-PPE** | Datasets académicos de cascos y chalecos | Buenos para citar en el informe; revisa términos de uso |
| **Imágenes propias** | Fotos/video de la empresa cliente | La mejor fuente para producción |

**Importante para vender:** muchos datasets son CC BY (permiten uso comercial con atribución), pero otros son CC BY-NC o de uso solo académico. Documenta de dónde sale cada imagen. Para el producto comercial, lo ideal es tu propio dataset o los datasets con licencia permisiva, más las imágenes de cada cliente.

---

## 🏋️ Entrenamiento con imágenes propias

### Flujo recomendado
1. **Capturar:** graba video de las cámaras reales del cliente (distintos turnos, iluminación, ángulos, personas, EPP de distintos colores y marcas).
2. **Extraer frames:** 1 cada 1–2 segundos para evitar imágenes casi idénticas.
3. **Etiquetar:** Roboflow, CVAT o Label Studio. Dibuja cajas para `person` y cada EPP.
4. **Dividir:** 70 % entrenamiento / 20 % validación / 10 % prueba (sin mezclar frames del mismo video entre conjuntos).
5. **Entrenar** partiendo de pesos preentrenados (fine-tuning):

```python
from ultralytics import YOLO

model = YOLO("yolov8s.pt")
model.train(data="training/data.yaml", epochs=100, imgsz=640, batch=16)
```

6. **Evaluar:** revisa precisión, recall y mAP por clase, y la matriz de confusión.
7. **Mejorar:** guarda automáticamente los frames de baja confianza o los errores reportados por el usuario, etiquétalos y reentrena (ciclo de mejora continua).

### Cantidad de imágenes (orientativa)
- Mínimo para una demo: ~200–300 imágenes por clase.
- Para producción por cliente: 1,000+ imágenes con variedad real.
- Si el cliente usa EPP muy particular (uniformes, cascos de color), añade ejemplos específicos.

### Hardware
- Entrenar: Google Colab (GPU gratuita) o Roboflow Train.
- Ejecutar: mini PC con CPU decente para 1 cámara; NVIDIA Jetson o GPU dedicada para varias cámaras.

---

## ⚖️ Licencias (crítico si lo vas a vender)

- **Ultralytics YOLOv8** usa licencia **AGPL-3.0**: si distribuyes un producto comercial que lo usa, debes liberar tu código o comprar una **licencia empresarial** de Ultralytics.
- **Alternativas con licencia permisiva** (Apache 2.0/MIT): YOLOX, RT-DETR, y otros detectores abiertos. Verifica siempre la licencia vigente antes de decidir.
- Para la materia no hay problema; para comercializar, decide esto desde el principio.

---

## 🗺️ Plan de acción por fases

| Fase | Objetivo | Entregable |
|---|---|---|
| **1. Base** | Detección con modelo preentrenado de Roboflow + OpenCV | Video con cajas de EPP |
| **2. Simbólico** | Motor de reglas + asociación persona↔EPP | Decisiones con explicación; pruebas unitarias |
| **3. Zonas** | Polígonos, punto-en-zona, reglas por zona | `zones.json` + editor de zonas |
| **4. Robustez** | Tracking, temporalidad, anti-falsos positivos | Estados estables por persona |
| **5. UI** | Pantallas de monitoreo y configuración | Aplicación de escritorio |
| **6. Alertas y registro** | Voz, relé, SQLite, capturas | Historial auditable |
| **7. Entrenamiento propio** | Dataset propio + fine-tuning | Modelo comparado con el base |
| **8. Producto** | Multicámara, dashboard web, reportes, notificaciones | Piloto con un cliente |

**Para la entrega de la materia:** fases 1–6, más una comparación en fase 7 (modelo base vs. modelo ajustado con tus imágenes). Eso demuestra el enfoque híbrido con evidencia.

---

## 💼 Ideas para comercializarlo

- **Modelo de negocio:** suscripción mensual por cámara + instalación y entrenamiento personalizado.
- **Diferenciadores:** reglas editables por zona sin reentrenar, explicabilidad de cada alerta, funcionamiento local (sin enviar video a la nube).
- **Extras valorados:** reportes de cumplimiento para auditorías, alertas por WhatsApp/Telegram, integración con torniquetes o relés, panel multi-sede.
- **Consideraciones legales:** aviso de videovigilancia a los trabajadores, política de retención de video, y cumplimiento de la ley de protección de datos aplicable (en México, la LFPDPPP). Considera no guardar rostros: guarda solo el evento y una captura difuminada.
- **Validación:** antes de vender, haz un piloto gratuito en un taller real y mide falsos positivos y negativos con datos reales.

---

## 🚀 Instalación rápida

```bash
git clone https://github.com/tu-usuario/guardian-epp.git
cd guardian-epp
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python main.py --source 0
```

`requirements.txt`:

```text
ultralytics>=8.0.0
opencv-python>=4.8.0
numpy
pyttsx3>=2.90
pyserial>=3.5
customtkinter>=5.2.0
```

---

## 📄 Créditos

Proyecto de la materia de **Inteligencia Artificial**.
Modelos y datasets: Roboflow Universe / Ultralytics YOLOv8 (revisar licencias de cada uno).
