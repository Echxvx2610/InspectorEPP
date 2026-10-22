"""
Módulo Temporal — Filtro anti-parpadeo y confirmación de violaciones.
Una infracción solo se confirma como alarma tras persistir durante N frames consecutivos
o X segundos, evitando falsas alarmas por oclusiones o inferencias intermitentes.
"""

import time


class TemporalFilter:
    def __init__(self, grace_period_sec=1.5, min_consecutive_frames=5):
        self.grace_period_sec = grace_period_sec
        self.min_consecutive_frames = min_consecutive_frames
        # Dict {track_id: {"first_violation_time": float, "consecutive_frames": int, "confirmed": bool}}
        self.track_states = {}

    def update(self, person_id, is_violating):
        """
        Actualiza el estado temporal de una persona.

        Args:
            person_id: ID del tracker
            is_violating: True si la regla actual detectó una infracción

        Returns:
            confirmed_alarm (bool): True si la violación supera el tiempo de gracia o frames requeridos.
        """
        now = time.time()

        if not is_violating:
            # Si ya no está infringiendo, limpiar estado
            if person_id in self.track_states:
                del self.track_states[person_id]
            return False

        if person_id not in self.track_states:
            self.track_states[person_id] = {
                "first_time": now,
                "frames": 1,
                "confirmed": False
            }
        else:
            state = self.track_states[person_id]
            state["frames"] += 1

        state = self.track_states[person_id]
        duration = now - state["first_time"]

        # Confirmar alarma si supera tiempo de gracia o conteo de frames
        if duration >= self.grace_period_sec or state["frames"] >= self.min_consecutive_frames:
            state["confirmed"] = True
            return True

        return False

    def cleanup_old_tracks(self, active_track_ids):
        """Elimina del registro personas que ya no están visibles en el cuadro."""
        active_set = set(active_track_ids)
        to_remove = [pid for pid in self.track_states if pid not in active_set]
        for pid in to_remove:
            del self.track_states[pid]
