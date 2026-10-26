"""
Paso 7 — Mini motor de reglas (modulo simbolico)
================================================
Objetivo: decidir si una persona CUMPLE la normativa de su zona.

Este paso NO usa camara ni YOLO: es el lado RAZONADOR del sistema.
Las reglas viven en datos (config/rules.json), no en codigo: agregar
una regla nueva no toca ni una linea de logica.

Contrato de cada evaluacion (igual que RuleEngine.evaluate_person):
    devuelve {is_safe, missing, rule_code, explanation}
El rule_code y la explanation SIEMPRE se conservan: eso es EXPLICABILIDAD
(y es lo que pide la materia).

Uso:
    python demo/paso7_reglas.py            # usa config/rules.json real
    python demo/paso7_reglas.py ruta.json  # usa otro archivo de reglas

REPL (se escribe en la consola, la ventana de video no existe):
    numero)  elegir zona (SOLDADURA, LABORATORIO, ...)
    e        evaluar: se piden los EPP presentes separados por comas
    m        mostrar el JSON de reglas crudo
    r        recargar reglas (prove que el JSON se ve sin reiniciar)
    a        agregar un perfil nuevo escribiendo en consola -> guarda en
             el JSON (reto BODEGA, sin tocar codigo)
    s        salir

RETO (GUIA): agregar la regla "BODEGA" (con 'a') y comprobar que la
evaluacion la usa de inmediato. Esa es la gracia del modulo simbolico.

Referencia: src/rule_engine.py (RuleEngine.evaluate_person)
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
# la raiz del proyecto: aqui vive config/rules.json del Guardian real
PROYECTO = BASE.parent
VENTANA = None  # paso de consola: sin OpenCV

# nombres legibles en espanol (igual que PPE_ES_NAMES de rule_engine.py)
PPE_ES = {
    "helmet": "casco",
    "vest": "chaleco",
    "welding_mask": "careta de soldadura",
    "glasses": "lentes de seguridad",
    "gloves": "guantes",
    "mask": "mascarilla",
    "boots": "botas de seguridad",
}

# alias ES -> EN para que el usuario pueda teclear en cualquiera de los dos
ALIAS_ES_EN = {v: k for k, v in PPE_ES.items()}
ALIAS_ES_EN["casco de seguridad"] = "helmet"
ALIAS_ES_EN["chaleco reflectante"] = "vest"
ALIAS_ES_EN["careta"] = "welding_mask"


# ---------------------------------------------------------------------------
# 1. Carga de reglas (datos, no codigo)
# ---------------------------------------------------------------------------
def cargar_reglas(ruta):
    """Devuelve el dict del perfil -> {'requeridos': [...], 'mensaje': ...}.
    Un perfil SIN clave 'requeridos' o vacio = no exige nada (R0)."""
    if not ruta.exists():
        sys.exit(
            f"No existe {ruta}.\n"
            "Ejecuta desde la raiz del proyecto: python demo/paso7_reglas.py"
        )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. EL EVALUADOR — version propia y comentada de evaluate_person
# ---------------------------------------------------------------------------
def evaluar(reglas, perfil, presentes, zona_nombre=None):
    """
    reglas:    dict cargado del JSON
    perfil:    zona de la persona (ej. 'SOLDADURA'); None/'' = fuera de zona
    presentes: lista de clases EPP que SI se detectaron en la persona

    Lógica de sets: faltantes = requeridos - presentes.
    set diferencia = lo que exije el perfil y NO trae la persona.
    """
    # R5: fuera de toda zona delimitada -> se IGNORA (siempre conforme)
    if not perfil:
        return {
            "is_safe": True, "missing": [], "rule_code": "R5",
            "explanation": "Fuera de zona delimitada (se ignora)."
        }

    perfil = perfil.upper()
    regla = reglas.get(perfil)
    if not regla:
        # R0: persona EN una zona con perfil desconocido -> sin restriccion
        return {
            "is_safe": True, "missing": [], "rule_code": "R0",
            "explanation": f"Sin reglas configuradas para '{perfil}'."
        }

    requeridos = regla.get("requeridos", [])
    if not requeridos:
        return {
            "is_safe": True, "missing": [], "rule_code": "R0",
            "explanation": f"'{perfil}' no exige EPP (requeridos vacio)."
        }

    presentes_set = set(presentes)
    faltantes = [r for r in requeridos if r not in presentes_set]
    lugar = zona_nombre.upper() if zona_nombre else perfil

    if not faltantes:
        return {
            "is_safe": True, "missing": [], "rule_code": "OK",
            "explanation": f"Normativa cumplida en {lugar}."
        }
    faltantes_es = [PPE_ES.get(m, m) for m in faltantes]
    return {
        "is_safe": False, "missing": faltantes, "rule_code": "VIOLACION",
        "explanation": f"Falta {', '.join(faltantes_es)} en {lugar}."
    }


# ---------------------------------------------------------------------------
# 3. Entrada del usuario: nombres ES o EN -> ids internos EN
#    (regla de oro del proyecto: los ids internos SIEMPRE en ingles)
# ---------------------------------------------------------------------------
def parsear_presentes(texto):
    partes = [p.strip().lower() for p in texto.split(",") if p.strip()]
    return [ALIAS_ES_EN.get(p, p) for p in partes]


# ---------------------------------------------------------------------------
# 4. REPL
# ---------------------------------------------------------------------------
def pedir(texto, defecto=None):
    v = input(texto).strip()
    return v or defecto


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        PROYECTO / "config" / "rules.json"
    reglas = cargar_reglas(ruta)

    activo = None
    print("=" * 62)
    print(" Mini motor de reglas — Guardián EPP (paso 7)")
    print("=" * 62)
    print("Perfiles en el JSON:")
    for i, nombre in enumerate(reglas, 1):
        print(f"  {i}) {nombre:12} requiere: "
              f"{', '.join(reglas[nombre].get('requeridos', [])) or '(nada)'}")
    print()
    print("Comandos: <numero> elegir zona  |  e evaluar  |  m ver JSON"
          "  |  r recargar  |  a agregar perfil  |  s salir")

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            cmd = "s"
        if not cmd:
            continue

        if cmd == "s":
            break

        if cmd == "r":
            reglas = cargar_reglas(ruta)  # recoger cambios del JSON
            print(f"Reglas recargadas de {ruta}")
            continue

        if cmd == "m":
            print(json.dumps(reglas, indent=2, ensure_ascii=False))
            continue

        if cmd == "a":
            nombre = pedir("Nombre del perfil (ej. BODEGA): ").upper()
            if not nombre:
                print("Nombre vacio: no se guardo nada.")
                continue
            presentes_lbl = pedir(
                "EPP requeridos separados por coma "
                f"({', '.join(PPE_ES)}): "
            )
            requeridos = [p for p in parsear_presentes(presentes_lbl) if p]
            mensaje = pedir("Mensaje de advertencia: ",
                            f"Se requiere {', '.join(PPE_ES.get(p, p) for p in requeridos)}.")
            reglas[nombre] = {
                "requeridos": requeridos,
                "mensaje": mensaje,
                "mensaje_error": mensaje,
            }
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(reglas, f, indent=2, ensure_ascii=False)
            print(f"Perfil '{nombre}' guardado EN DATOS, sin tocar codigo.")
            continue

        if cmd == "e":
            if activo is None:
                print("Primero elige zona con su numero.")
                continue
            presentes = parsear_presentes(pedir("EPP presentes: "))
            res = evaluar(reglas, activo, presentes)
            print(f"  is_safe    : {res['is_safe']}")
            print(f"  missing    : {res['missing']}")
            print(f"  rule_code  : {res['rule_code']}")
            print(f"  explanation: {res['explanation']}")
            continue

        if cmd.isdigit():
            nombre = list(reglas)[int(cmd) - 1] \
                if 0 < int(cmd) <= len(reglas) else None
            if nombre is None:
                print("Numero fuera de rango.")
                continue
            activo = nombre
            print(f"Zona activa: {activo}  "
                  f"(escribe 'e' para evaluar una persona)")
            continue

        print("Comando no reconocido ...")

    print("Hecho.")


if __name__ == "__main__":
    main()
