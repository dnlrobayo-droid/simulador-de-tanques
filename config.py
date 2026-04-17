"""
config.py
=========
Configuración centralizada del simulador de tanques.
Todos los umbrales, capacidades y valores por defecto viven aquí.
"""

from dataclasses import dataclass, field


# ── Capacidades por defecto (m³) ──────────────────────────────────────────────
CAP_DEFAULT: dict[str, float] = {
    "aux":  400.0,
    "cald":  90.0,
    "comp": 120.0,
    "prin": 500.0,
}

# ── Umbrales de control (fracción 0-1) ────────────────────────────────────────
UMBRALES = {
    "bomba_on":        0.70,   # Bomba/válvula se enciende cuando tanque destino ≤ 70%
    "bomba_off":       0.90,   # Bomba/válvula se apaga cuando tanque destino ≥ 90%
    "reserva_aux":     0.20,   # Reserva mínima Auxiliar (20%)
    "reserva_cald":    0.30,   # Reserva mínima Calderas (30%)
    "reserva_comp":    0.10,   # Reserva mínima Compresores (10%)
    "emergencia_prin": 0.30,   # Umbral de emergencia Principal (30%)
    "reduccion_emergencia": 0.50,  # Factor de reducción de consumo en emergencia
}

# ── Colores por tanque ────────────────────────────────────────────────────────
COLORES = {
    "aux":  "#2563eb",
    "cald": "#16a34a",
    "comp": "#ea580c",
    "prin": "#7c3aed",
}

LABELS = {
    "aux":  "Auxiliar",
    "cald": "Calderas",
    "comp": "Compresores",
    "prin": "Principal",
}

# ── Rangos de parámetros para la UI ───────────────────────────────────────────
RANGOS_UI = {
    "q_aux_cald":             {"min": 0.0, "max": 50.0,  "default": 15.0, "label": "Aux → Calderas (m³/h)"},
    "q_cald_comp":            {"min": 0.0, "max": 50.0,  "default": 10.0, "label": "Cald → Compresores (m³/h)"},
    "q_comp_prin":            {"min": 0.0, "max": 60.0,  "default": 20.0, "label": "Comp → Principal (m³/h)"},
    "q_ptar":                 {"min": 0.0, "max": 40.0,  "default": 5.0,  "label": "PTAR → Principal (m³/h)"},
    "q_ptap":                 {"min": 0.0, "max": 40.0,  "default": 5.0,  "label": "PTAP → Principal (m³/h)"},
    "consumo_calderas":       {"min": 0.0, "max": 50.0,  "default": 8.0,  "label": "Consumo Calderas (m³/h)"},
    "q_lav":                  {"min": 0.0, "max": 80.0,  "default": 8.0,  "label": "Lavandería (m³/h)"},
    "q_tinto":                {"min": 0.0, "max": 80.0,  "default": 6.0,  "label": "Tintorería (m³/h)"},
    "entrada_acueducto_cald": {"min": 0.0, "max": 50.0,  "default": 10.0, "label": "Acueducto → Calderas (m³/h)"},
    "entrada_acueducto_comp": {"min": 0.0, "max": 50.0,  "default": 25.0, "label": "Acueducto → Compresores (m³/h)"},
}

# ── Presets / escenarios predefinidos ─────────────────────────────────────────
PRESETS: dict[str, dict] = {
    "Personalizado": {},
    "Operación normal": {
        "niv_aux": 70, "niv_cald": 70, "niv_comp": 70, "niv_prin": 80,
        "q_aux_cald": 15.0, "q_cald_comp": 10.0, "q_comp_prin": 20.0,
        "q_ptar": 5.0, "q_ptap": 5.0, "consumo_calderas": 8.0,
        "q_lav": 8.0, "q_tinto": 6.0,
        "entrada_acueducto_cald": 10.0, "entrada_acueducto_comp": 25.0,
        "horas": 24,
    },
    "Sequía (sin acueducto)": {
        "niv_aux": 80, "niv_cald": 60, "niv_comp": 50, "niv_prin": 70,
        "q_aux_cald": 15.0, "q_cald_comp": 10.0, "q_comp_prin": 20.0,
        "q_ptar": 0.0, "q_ptap": 0.0, "consumo_calderas": 8.0,
        "q_lav": 8.0, "q_tinto": 6.0,
        "entrada_acueducto_cald": 0.0, "entrada_acueducto_comp": 0.0,
        "horas": 48,
    },
    "Emergencia (tanques bajos)": {
        "niv_aux": 25, "niv_cald": 35, "niv_comp": 15, "niv_prin": 20,
        "q_aux_cald": 15.0, "q_cald_comp": 10.0, "q_comp_prin": 20.0,
        "q_ptar": 5.0, "q_ptap": 5.0, "consumo_calderas": 8.0,
        "q_lav": 12.0, "q_tinto": 10.0,
        "entrada_acueducto_cald": 10.0, "entrada_acueducto_comp": 25.0,
        "horas": 36,
    },
    "Mantenimiento calderas": {
        "niv_aux": 70, "niv_cald": 90, "niv_comp": 70, "niv_prin": 80,
        "q_aux_cald": 0.0, "q_cald_comp": 0.0, "q_comp_prin": 20.0,
        "q_ptar": 10.0, "q_ptap": 10.0, "consumo_calderas": 0.0,
        "q_lav": 5.0, "q_tinto": 3.0,
        "entrada_acueducto_cald": 0.0, "entrada_acueducto_comp": 30.0,
        "horas": 24,
    },
    "Alta demanda industrial": {
        "niv_aux": 90, "niv_cald": 80, "niv_comp": 80, "niv_prin": 90,
        "q_aux_cald": 30.0, "q_cald_comp": 25.0, "q_comp_prin": 40.0,
        "q_ptar": 15.0, "q_ptap": 15.0, "consumo_calderas": 25.0,
        "q_lav": 50.0, "q_tinto": 40.0,
        "entrada_acueducto_cald": 20.0, "entrada_acueducto_comp": 30.0,
        "horas": 48,
    },
}


@dataclass
class SimConfig:
    """Configuración validada para una ejecución de simulación."""
    niv_aux: float = 280.0
    niv_cald: float = 63.0
    niv_comp: float = 84.0
    niv_prin: float = 400.0
    q_aux_cald: float = 15.0
    q_cald_comp: float = 10.0
    q_comp_prin: float = 20.0
    q_ptar: float = 5.0
    q_ptap: float = 5.0
    q_lav: float = 8.0
    q_tinto: float = 6.0
    entrada_acueducto_cald: float = 10.0
    entrada_acueducto_comp: float = 25.0
    consumo_calderas: float = 8.0

    def to_dict(self) -> dict[str, float]:
        """Convierte a diccionario compatible con simular()."""
        return {
            "niv_aux": self.niv_aux,
            "niv_cald": self.niv_cald,
            "niv_comp": self.niv_comp,
            "niv_prin": self.niv_prin,
            "q_aux_cald": max(0.0, self.q_aux_cald),
            "q_cald_comp": max(0.0, self.q_cald_comp),
            "q_comp_prin": max(0.0, self.q_comp_prin),
            "q_ptar": max(0.0, self.q_ptar),
            "q_ptap": max(0.0, self.q_ptap),
            "q_lav": max(0.0, self.q_lav),
            "q_tinto": max(0.0, self.q_tinto),
            "entrada_acueducto_cald": max(0.0, self.entrada_acueducto_cald),
            "entrada_acueducto_comp": max(0.0, self.entrada_acueducto_comp),
            "consumo_calderas": max(0.0, self.consumo_calderas),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SimConfig":
        """Crea instancia desde diccionario, validando claves requeridas."""
        required = {
            "niv_aux", "niv_cald", "niv_comp", "niv_prin",
            "q_aux_cald", "q_cald_comp", "q_comp_prin",
            "q_ptar", "q_ptap", "q_lav", "q_tinto",
            "entrada_acueducto_cald", "entrada_acueducto_comp",
            "consumo_calderas",
        }
        missing = required - set(d.keys())
        if missing:
            raise ValueError(f"Faltan claves en config: {missing}")
        return cls(**{k: d[k] for k in required})
