"""
Motor de Reglas Simbólico (Sistema Experto).
Aplica reglas explícitas de EPP por zona delimitada con explicabilidad completa.
"""

import json
import os

from src import paths


# Nombres legibles en español
PPE_ES_NAMES = {
    "helmet": "casco",
    "vest": "chaleco",
    "welding_mask": "careta de soldadura",
    "glasses": "lentes de seguridad",
    "gloves": "guantes",
    "mask": "mascarilla",
    "boots": "botas de seguridad"
}


class RuleEngine:
    def __init__(self, config_path=paths.RULES_PATH, zone="GENERAL"):
        self.config_path = str(config_path)
        self.zone = zone
        self.rules = {}
        self.reload()

    def reload(self):
        """Recarga las reglas desde el archivo de configuración."""
        if not os.path.exists(self.config_path):
            self.rules = {
                "GENERAL": {
                    "requeridos": ["helmet", "vest"],
                    "mensaje": "Se requiere casco y chaleco."
                }
            }
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.rules = json.load(f)
            except Exception as e:
                print(f"Error cargando reglas desde {self.config_path}: {e}")

        self.current_rule = self.rules.get(self.zone, {})

    def set_zone(self, zone):
        self.zone = zone
        self.current_rule = self.rules.get(zone, {})

    def evaluate_person(self, present_ppe, zone_profile, zone_name=None):
        """
        Evalúa el cumplimiento de una persona en una zona específica.

        Args:
            present_ppe: Lista/set de implementos detectados en la persona (ej: ['vest', 'helmet'])
            zone_profile: Perfil de la zona (ej: 'SOLDADURA', 'SMT', 'LABORATORIO', 'GENERAL')
            zone_name: Nombre asignado a la zona (ej: 'PCBA', 'Estacion 1')

        Returns:
            dict con:
                - is_safe (bool)
                - missing (list de str)
                - rule_code (str)
                - explanation (str)
        """
        # R5: Si la persona está fuera de toda zona delimitada, se ignora
        if not zone_profile:
            return {
                "is_safe": True,
                "missing": [],
                "rule_code": "R5",
                "explanation": "Fuera de zona delimitada."
            }

        profile_upper = zone_profile.upper()
        rule = self.rules.get(profile_upper)

        if not rule:
            # Si no hay regla específica definida para este perfil, se asume sin restricción
            return {
                "is_safe": True,
                "missing": [],
                "rule_code": "R0",
                "explanation": f"Sin reglas configuradas para el perfil {profile_upper}."
            }

        required = rule.get("requeridos", [])
        present_set = set(present_ppe or [])
        missing = [req for req in required if req not in present_set]

        display_name = zone_name or profile_upper

        if not missing:
            return {
                "is_safe": True,
                "missing": [],
                "rule_code": "OK",
                "explanation": f"Normativa cumplida en {display_name}."
            }
        else:
            missing_es = [PPE_ES_NAMES.get(m, m) for m in missing]
            return {
                "is_safe": False,
                "missing": missing,
                "rule_code": "NO CUMPLE",
                "explanation": f"Falta {', '.join(missing_es)} en {display_name}."
            }

    def evaluate(self, detected_classes):
        """Compatibilidad con modo CLI: evalúa clases globales en zona actual."""
        if not self.current_rule:
            return True, "No hay reglas definidas para esta zona."

        requeridos = self.current_rule.get("requeridos", [])
        faltantes = [req for req in requeridos if req not in detected_classes]

        if faltantes:
            faltantes_es = [PPE_ES_NAMES.get(f, f) for f in faltantes]
            mensaje = f"Faltan requeridos: {', '.join(faltantes_es)}"
            return False, mensaje

        return True, "Cumple normativa."
