"""
Módulo Geométrico — Asociación Persona ↔ EPP.
Determina qué implementos de seguridad pertenecen a cada persona detectada
según la contención geométrica y la región anatómica esperada (cabeza, torso, pies).
"""

# Regiones anatómicas relativas al alto de la persona (de 0.0 superior a 1.0 inferior)
REGION_MAPPING = {
    # Tercio superior: cabeza y rostro
    "helmet": (0.0, 0.40),
    "welding_mask": (0.0, 0.45),
    "mask": (0.05, 0.45),
    "glasses": (0.05, 0.35),

    # Zona media: torso y extremidades superiores
    "vest": (0.15, 0.75),
    "gloves": (0.35, 0.85),

    # Tercio inferior: pies y piernas
    "boots": (0.65, 1.05),
}


class PPEAssociator:
    def __init__(self, region_mapping=None):
        self.region_mapping = region_mapping or REGION_MAPPING

    def associate(self, persons, ppe_detections):
        """
        Asocia una lista de detecciones de EPP a cada persona.

        Args:
            persons: Lista de dicts [{'id': track_id, 'bbox': [x1, y1, x2, y2], 'conf': float}]
            ppe_detections: Lista de dicts [{'class': str, 'bbox': [x1, y1, x2, y2], 'conf': float}]

        Returns:
            Dict {track_id: {'present_ppe': [class_names...], 'items': [ppe_detection_dicts...]}}
        """
        associations = {
            p["id"]: {"present_ppe": set(), "items": []}
            for p in persons
        }

        for item in ppe_detections:
            item_cls = item.get("class", "").lower()
            ix1, iy1, ix2, iy2 = item["bbox"]
            cx = (ix1 + ix2) / 2.0
            cy = (iy1 + iy2) / 2.0

            best_person_id = None
            best_person_area = float("inf")

            for person in persons:
                px1, py1, px2, py2 = person["bbox"]
                pw = px2 - px1
                ph = py2 - py1

                if pw <= 0 or ph <= 0:
                    continue

                # 1. Comprobar si el centro del EPP cae dentro de la caja de la persona (con margen horizontal)
                margin_x = pw * 0.15
                if (px1 - margin_x) <= cx <= (px2 + margin_x) and py1 <= cy <= py2:
                    # 2. Comprobar región vertical esperada
                    reg_min, reg_max = self.region_mapping.get(item_cls, (0.0, 1.0))
                    rel_y = (cy - py1) / ph

                    if reg_min <= rel_y <= reg_max:
                        # Si coincide con varias personas, asignar a la más cercana o de menor área
                        area = pw * ph
                        if area < best_person_area:
                            best_person_area = area
                            best_person_id = person["id"]

            if best_person_id is not None:
                associations[best_person_id]["present_ppe"].add(item_cls)
                associations[best_person_id]["items"].append(item)

        # Convertir sets a listas ordenadas
        for pid in associations:
            associations[pid]["present_ppe"] = sorted(list(associations[pid]["present_ppe"]))

        return associations
