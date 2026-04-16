"""
simulator.py
============
Lógica central del simulador de flujo de agua entre tanques interconectados.
Separada de la interfaz Streamlit para facilitar pruebas unitarias y reutilización.
"""

import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ── Capacidades por defecto (m³) ──────────────────────────────────────────────
CAP_DEFAULT = {
    "aux":  400.0,
    "cald":  90.0,
    "comp": 120.0,
    "prin": 500.0,
}


def _safe_pct(valor: float, capacidad: float) -> float:
    """Calcula el porcentaje; devuelve 0.0 si la capacidad es cero."""
    return (valor / capacidad * 100) if capacidad > 0 else 0.0


def simular(
    horas: int,
    config: dict[str, Any],
    capacidades: dict[str, float] | None = None,
    usar_carrotanques: bool = False,
    carrotanque_aux: float = 0.0,
    carrotanque_comp: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Simula el sistema de tanques interconectados hora a hora.

    Parámetros
    ----------
    horas : int
        Número de horas a simular.
    config : dict
        Caudales, consumos y niveles iniciales en m³.
    capacidades : dict | None
        Capacidades máximas de cada tanque en m³.
        Si es None se usan los valores por defecto.
    usar_carrotanques : bool
        Si True, distribuye el agua de carrotanques a lo largo de la simulación.
    carrotanque_aux : float
        Volumen total (m³) a inyectar al tanque Auxiliar.
    carrotanque_comp : float
        Volumen total (m³) a inyectar al tanque Compresores.

    Retorna
    -------
    list[dict]
        Historial con un registro por hora (hora 0 = estado inicial).
    """
    # ── Validación básica ────────────────────────────────────────────────────
    if horas <= 0:
        raise ValueError("El número de horas debe ser mayor a 0.")

    # ── Capacidades ──────────────────────────────────────────────────────────
    cap = {**CAP_DEFAULT, **(capacidades or {})}
    cap_aux  = max(cap["aux"],  0.001)   # evitar división por cero
    cap_cald = max(cap["cald"], 0.001)
    cap_comp = max(cap["comp"], 0.001)
    cap_prin = max(cap["prin"], 0.001)

    # ── Niveles iniciales ────────────────────────────────────────────────────
    niv_aux  = max(0.0, min(config["niv_aux"],  cap_aux))
    niv_cald = max(0.0, min(config["niv_cald"], cap_cald))
    niv_comp = max(0.0, min(config["niv_comp"], cap_comp))
    niv_prin = max(0.0, min(config["niv_prin"], cap_prin))

    # ── Caudales y consumos ──────────────────────────────────────────────────
    q_aux_cald             = max(0.0, config["q_aux_cald"])
    q_cald_comp            = max(0.0, config["q_cald_comp"])
    q_comp_prin            = max(0.0, config["q_comp_prin"])
    q_ptar                 = max(0.0, config["q_ptar"])
    q_ptap                 = max(0.0, config["q_ptap"])
    q_lav                  = max(0.0, config["q_lav"])
    q_tinto                = max(0.0, config["q_tinto"])
    entrada_acueducto_cald = max(0.0, config["entrada_acueducto_cald"])
    entrada_acueducto_comp = max(0.0, config["entrada_acueducto_comp"])
    consumo_calderas       = max(0.0, config["consumo_calderas"])

    # ── Suministro carrotanques distribuido por hora ─────────────────────────
    sum_aux_h  = (max(0.0, carrotanque_aux)  / horas) if usar_carrotanques else 0.0
    sum_comp_h = (max(0.0, carrotanque_comp) / horas) if usar_carrotanques else 0.0

    # ── Estado inicial de bombas/válvulas ────────────────────────────────────
    bomba_aux_cald_on       = q_aux_cald  > 0
    valvula_cald_comp_ab    = q_cald_comp > 0
    bomba_comp_prin_on      = q_comp_prin > 0

    # ── Historial ────────────────────────────────────────────────────────────
    historial: list[dict[str, Any]] = []
    historial.append({
        "hora":           0,
        "aux_m3":         round(niv_aux,  2),
        "cald_m3":        round(niv_cald, 2),
        "comp_m3":        round(niv_comp, 2),
        "prin_m3":        round(niv_prin, 2),
        "aux_pct":        round(_safe_pct(niv_aux,  cap_aux),  1),
        "cald_pct":       round(_safe_pct(niv_cald, cap_cald), 1),
        "comp_pct":       round(_safe_pct(niv_comp, cap_comp), 1),
        "prin_pct":       round(_safe_pct(niv_prin, cap_prin), 1),
        "mov_aux_cald":   0, "entrada_cald_acu": 0, "consumo_cald":   0,
        "mover_cald_comp":0, "entrada_comp_acu": 0, "mov_comp_prin":  0,
        "entrada_ptar_ptap": 0, "consumo_areas": 0, "agua_carrotanques": 0,
        "modo_emergencia": False,
        "estado_bomba_aux":  bomba_aux_cald_on,
        "estado_valvula_cald": valvula_cald_comp_ab,
        "estado_bomba_comp": bomba_comp_prin_on,
    })

    # ── Bucle principal ──────────────────────────────────────────────────────
    for hora_actual in range(1, horas + 1):

        # ── 1. Control automático por niveles (umbrales 70 % / 90 %) ────────

        # Bomba Aux → Cald
        if niv_cald >= 0.9 * cap_cald:
            bomba_aux_cald_on = False
        elif niv_cald <= 0.7 * cap_cald:
            bomba_aux_cald_on = q_aux_cald > 0

        # Válvula Cald → Comp
        if niv_comp >= 0.9 * cap_comp:
            valvula_cald_comp_ab = False
        elif niv_comp <= 0.7 * cap_comp:
            valvula_cald_comp_ab = q_cald_comp > 0

        # Bomba Comp → Prin
        if niv_prin >= 0.9 * cap_prin:
            bomba_comp_prin_on = False
        elif niv_prin <= 0.7 * cap_prin:
            bomba_comp_prin_on = (q_comp_prin > 0 and niv_comp > 0.1 * cap_comp)

        # ── 2. Cortes de seguridad por niveles mínimos críticos ──────────────
        if niv_aux  <= 0.2 * cap_aux:
            bomba_aux_cald_on    = False
        if niv_cald <= 0.3 * cap_cald:
            valvula_cald_comp_ab = False
        if niv_comp <= 0.1 * cap_comp:
            bomba_comp_prin_on   = False

        # ── 3. Modo emergencia tanque principal ──────────────────────────────
        modo_emergencia = niv_prin <= 0.3 * cap_prin
        if modo_emergencia:
            q_lav_h   = q_lav   * 0.5
            q_tinto_h = q_tinto * 0.5
            logging.warning(
                f"Hora {hora_actual}: EMERGENCIA – tanque principal al "
                f"{_safe_pct(niv_prin, cap_prin):.1f}%. Consumos reducidos al 50 %."
            )
        else:
            q_lav_h   = q_lav
            q_tinto_h = q_tinto

        # ── 4. Cálculo secuencial de flujos ──────────────────────────────────

        # Aux → Cald
        mov_aux_cald = (
            min(q_aux_cald, niv_aux, cap_cald - niv_cald)
            if bomba_aux_cald_on else 0.0
        )
        niv_aux  -= mov_aux_cald
        niv_cald += mov_aux_cald

        # Acueducto → Cald
        entrada_cald = min(entrada_acueducto_cald, cap_cald - niv_cald)
        niv_cald += entrada_cald

        # Consumo calderas (vapor)
        consumo_cald = min(consumo_calderas, niv_cald)
        niv_cald -= consumo_cald

        # Cald → Comp
        mover_cald_comp = (
            min(q_cald_comp, niv_cald, cap_comp - niv_comp)
            if valvula_cald_comp_ab else 0.0
        )
        niv_cald -= mover_cald_comp
        niv_comp += mover_cald_comp

        # Acueducto → Comp
        entrada_comp = min(entrada_acueducto_comp, cap_comp - niv_comp)
        niv_comp += entrada_comp

        # Comp → Prin
        mover_comp_prin = (
            min(q_comp_prin, niv_comp, cap_prin - niv_prin)
            if bomba_comp_prin_on else 0.0
        )
        niv_comp -= mover_comp_prin
        niv_prin += mover_comp_prin

        # PTAR + PTAP → Prin
        entrada_ptar_ptap = min(q_ptar + q_ptap, cap_prin - niv_prin)
        niv_prin += entrada_ptar_ptap

        # Consumo áreas (lavandería + tintorería)
        consumo_areas = min(q_lav_h + q_tinto_h, niv_prin)
        niv_prin -= consumo_areas

        # ── 5. Suministro carrotanques ────────────────────────────────────────
        agua_carrotanques = 0.0
        if usar_carrotanques:
            aporte_aux  = min(sum_aux_h,  cap_aux  - niv_aux)
            niv_aux    += aporte_aux
            aporte_comp = min(sum_comp_h, cap_comp - niv_comp)
            niv_comp   += aporte_comp
            agua_carrotanques = aporte_aux + aporte_comp

        # ── 6. Clamping – ningún nivel puede ser negativo ni superar capacidad ─
        niv_aux  = max(0.0, min(niv_aux,  cap_aux))
        niv_cald = max(0.0, min(niv_cald, cap_cald))
        niv_comp = max(0.0, min(niv_comp, cap_comp))
        niv_prin = max(0.0, min(niv_prin, cap_prin))

        # ── 7. Registro ──────────────────────────────────────────────────────
        historial.append({
            "hora":              hora_actual,
            "aux_m3":            round(niv_aux,  2),
            "cald_m3":           round(niv_cald, 2),
            "comp_m3":           round(niv_comp, 2),
            "prin_m3":           round(niv_prin, 2),
            "aux_pct":           round(_safe_pct(niv_aux,  cap_aux),  1),
            "cald_pct":          round(_safe_pct(niv_cald, cap_cald), 1),
            "comp_pct":          round(_safe_pct(niv_comp, cap_comp), 1),
            "prin_pct":          round(_safe_pct(niv_prin, cap_prin), 1),
            "mov_aux_cald":      round(mov_aux_cald,      2),
            "entrada_cald_acu":  round(entrada_cald,      2),
            "consumo_cald":      round(consumo_cald,      2),
            "mover_cald_comp":   round(mover_cald_comp,   2),
            "entrada_comp_acu":  round(entrada_comp,      2),
            "mov_comp_prin":     round(mover_comp_prin,   2),
            "entrada_ptar_ptap": round(entrada_ptar_ptap, 2),
            "consumo_areas":     round(consumo_areas,     2),
            "agua_carrotanques": round(agua_carrotanques, 2),
            "modo_emergencia":   modo_emergencia,
            "estado_bomba_aux":  bomba_aux_cald_on,
            "estado_valvula_cald": valvula_cald_comp_ab,
            "estado_bomba_comp": bomba_comp_prin_on,
        })

    return historial
