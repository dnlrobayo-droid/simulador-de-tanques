"""
simulator.py
============
Lógica central del simulador de flujo de agua entre tanques interconectados.
Separada de la interfaz Streamlit para facilitar pruebas unitarias y reutilización.

Refactorizado: funciones extraídas por responsabilidad, umbrales centralizados.
"""

import logging
from typing import Any

from config import CAP_DEFAULT, UMBRALES

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_pct(valor: float, capacidad: float) -> float:
    """Calcula el porcentaje; devuelve 0.0 si la capacidad es cero."""
    return (valor / capacidad * 100) if capacidad > 0 else 0.0


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    """Restringe un valor entre mínimo y máximo."""
    return max(minimo, min(valor, maximo))


# ── Control de bombas y válvulas ──────────────────────────────────────────────

def _evaluar_bomba_aux_cald(
    niv_cald: float, cap_cald: float, niv_aux: float, cap_aux: float,
    q_aux_cald: float, estado_actual: bool,
) -> bool:
    """Evalúa si la bomba Aux→Cald debe estar encendida."""
    umbral_on = UMBRALES["bomba_on"]
    umbral_off = UMBRALES["bomba_off"]
    reserva_aux = UMBRALES["reserva_aux"]

    if niv_cald >= umbral_off * cap_cald:
        return False
    if niv_cald <= umbral_on * cap_cald:
        estado_actual = q_aux_cald > 0
    # Corte de seguridad por nivel mínimo de Auxiliar
    if niv_aux <= reserva_aux * cap_aux:
        return False
    return estado_actual


def _evaluar_valvula_cald_comp(
    niv_comp: float, cap_comp: float, niv_cald: float, cap_cald: float,
    q_cald_comp: float, estado_actual: bool,
) -> bool:
    """Evalúa si la válvula Cald→Comp debe estar abierta."""
    umbral_on = UMBRALES["bomba_on"]
    umbral_off = UMBRALES["bomba_off"]
    reserva_cald = UMBRALES["reserva_cald"]

    if niv_comp >= umbral_off * cap_comp:
        return False
    if niv_comp <= umbral_on * cap_comp:
        estado_actual = q_cald_comp > 0
    # Corte de seguridad por nivel mínimo de Calderas
    if niv_cald <= reserva_cald * cap_cald:
        return False
    return estado_actual


def _evaluar_bomba_comp_prin(
    niv_prin: float, cap_prin: float, niv_comp: float, cap_comp: float,
    q_comp_prin: float, estado_actual: bool,
) -> bool:
    """Evalúa si la bomba Comp→Prin debe estar encendida."""
    umbral_on = UMBRALES["bomba_on"]
    umbral_off = UMBRALES["bomba_off"]
    reserva_comp = UMBRALES["reserva_comp"]

    if niv_prin >= umbral_off * cap_prin:
        return False
    if niv_prin <= umbral_on * cap_prin:
        estado_actual = (q_comp_prin > 0 and niv_comp > reserva_comp * cap_comp)
    # Corte de seguridad por nivel mínimo de Compresores
    if niv_comp <= reserva_comp * cap_comp:
        return False
    return estado_actual


# ── Flujos entre tanques ─────────────────────────────────────────────────────

def _flujo_aux_cald(
    niv_aux: float, niv_cald: float, cap_aux: float, cap_cald: float,
    q_aux_cald: float, bomba_on: bool,
) -> tuple[float, float, float]:
    """Calcula flujo Aux→Cald respetando reserva. Retorna (niv_aux, niv_cald, mov)."""
    if not bomba_on:
        return niv_aux, niv_cald, 0.0
    reserva = UMBRALES["reserva_aux"] * cap_aux
    disponible = max(0.0, niv_aux - reserva)
    espacio = max(0.0, cap_cald - niv_cald)
    mov = min(q_aux_cald, disponible, espacio)
    return niv_aux - mov, niv_cald + mov, mov


def _entrada_acueducto(niv: float, cap: float, caudal: float) -> tuple[float, float]:
    """Aplica entrada de acueducto. Retorna (niv_nuevo, entrada_real)."""
    entrada = min(caudal, max(0.0, cap - niv))
    return niv + entrada, entrada


def _consumo_vapor(niv_cald: float, cap_cald: float, consumo: float) -> tuple[float, float]:
    """Aplica consumo de vapor respetando reserva del 30%. Retorna (niv, consumo_real)."""
    reserva = UMBRALES["reserva_cald"] * cap_cald
    consumo_real = min(consumo, max(0.0, niv_cald - reserva))
    return niv_cald - consumo_real, consumo_real


def _flujo_cald_comp(
    niv_cald: float, niv_comp: float, cap_cald: float, cap_comp: float,
    q_cald_comp: float, valvula_abierta: bool,
) -> tuple[float, float, float]:
    """Calcula flujo Cald→Comp respetando reserva. Retorna (niv_cald, niv_comp, mov)."""
    if not valvula_abierta:
        return niv_cald, niv_comp, 0.0
    reserva = UMBRALES["reserva_cald"] * cap_cald
    disponible = max(0.0, niv_cald - reserva)
    espacio = max(0.0, cap_comp - niv_comp)
    mov = min(q_cald_comp, disponible, espacio)
    return niv_cald - mov, niv_comp + mov, mov


def _flujo_comp_prin(
    niv_comp: float, niv_prin: float, cap_comp: float, cap_prin: float,
    q_comp_prin: float, bomba_on: bool,
) -> tuple[float, float, float]:
    """Calcula flujo Comp→Prin respetando reserva. Retorna (niv_comp, niv_prin, mov)."""
    if not bomba_on:
        return niv_comp, niv_prin, 0.0
    reserva = UMBRALES["reserva_comp"] * cap_comp
    disponible = max(0.0, niv_comp - reserva)
    espacio = max(0.0, cap_prin - niv_prin)
    mov = min(q_comp_prin, disponible, espacio)
    return niv_comp - mov, niv_prin + mov, mov


def _consumo_areas(
    niv_prin: float, q_lav: float, q_tinto: float, modo_emergencia: bool,
) -> tuple[float, float]:
    """Calcula consumo de áreas. Retorna (niv_prin, consumo_real)."""
    factor = UMBRALES["reduccion_emergencia"] if modo_emergencia else 1.0
    consumo_deseado = (q_lav + q_tinto) * factor
    consumo_real = min(consumo_deseado, max(0.0, niv_prin))
    return niv_prin - consumo_real, consumo_real


def _suministro_carrotanques(
    niv_aux: float, niv_comp: float, cap_aux: float, cap_comp: float,
    sum_aux_h: float, sum_comp_h: float, usar: bool,
) -> tuple[float, float, float]:
    """Aplica carrotanques. Retorna (niv_aux, niv_comp, total_aportado)."""
    if not usar:
        return niv_aux, niv_comp, 0.0
    aporte_aux = min(sum_aux_h, max(0.0, cap_aux - niv_aux))
    niv_aux += aporte_aux
    aporte_comp = min(sum_comp_h, max(0.0, cap_comp - niv_comp))
    niv_comp += aporte_comp
    return niv_aux, niv_comp, aporte_aux + aporte_comp


# ── Registro de estado ────────────────────────────────────────────────────────

def _crear_registro(
    hora: int, niv_aux: float, niv_cald: float, niv_comp: float, niv_prin: float,
    cap_aux: float, cap_cald: float, cap_comp: float, cap_prin: float,
    mov_aux_cald: float, entrada_cald: float, consumo_cald: float,
    mover_cald_comp: float, entrada_comp: float, mover_comp_prin: float,
    entrada_ptar_ptap: float, consumo_areas: float, agua_carrotanques: float,
    modo_emergencia: bool, bomba_aux: bool, valvula_cald: bool, bomba_comp: bool,
) -> dict[str, Any]:
    """Crea un registro del historial para una hora dada."""
    return {
        "hora":              hora,
        "aux_m3":            round(niv_aux,  2),
        "cald_m3":           round(niv_cald, 2),
        "comp_m3":           round(niv_comp, 2),
        "prin_m3":           round(niv_prin, 2),
        "aux_pct":           round(_safe_pct(niv_aux,  cap_aux),  1),
        "cald_pct":          round(_safe_pct(niv_cald, cap_cald), 1),
        "comp_pct":          round(_safe_pct(niv_comp, cap_comp), 1),
        "prin_pct":          round(_safe_pct(niv_prin, cap_prin), 1),
        "mov_aux_cald":      round(mov_aux_cald,      2),
        "entrada_cald_acu":  round(entrada_cald,       2),
        "consumo_cald":      round(consumo_cald,       2),
        "mover_cald_comp":   round(mover_cald_comp,    2),
        "entrada_comp_acu":  round(entrada_comp,       2),
        "mov_comp_prin":     round(mover_comp_prin,    2),
        "entrada_ptar_ptap": round(entrada_ptar_ptap,  2),
        "consumo_areas":     round(consumo_areas,      2),
        "agua_carrotanques": round(agua_carrotanques,  2),
        "modo_emergencia":   modo_emergencia,
        "estado_bomba_aux":  bomba_aux,
        "estado_valvula_cald": valvula_cald,
        "estado_bomba_comp": bomba_comp,
    }


# ── Función principal ─────────────────────────────────────────────────────────

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
        Claves requeridas: niv_aux, niv_cald, niv_comp, niv_prin,
        q_aux_cald, q_cald_comp, q_comp_prin, q_ptar, q_ptap,
        q_lav, q_tinto, entrada_acueducto_cald, entrada_acueducto_comp,
        consumo_calderas.
    capacidades : dict | None
        Capacidades máximas de cada tanque en m³.
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
    # ── Validación ────────────────────────────────────────────────────────
    if horas <= 0:
        raise ValueError("El número de horas debe ser mayor a 0.")

    required_keys = {
        "niv_aux", "niv_cald", "niv_comp", "niv_prin",
        "q_aux_cald", "q_cald_comp", "q_comp_prin",
        "q_ptar", "q_ptap", "q_lav", "q_tinto",
        "entrada_acueducto_cald", "entrada_acueducto_comp", "consumo_calderas",
    }
    missing = required_keys - set(config.keys())
    if missing:
        raise ValueError(f"Faltan claves en config: {missing}")

    # ── Capacidades ───────────────────────────────────────────────────────
    cap = {**CAP_DEFAULT, **(capacidades or {})}
    cap_aux  = max(cap["aux"],  0.001)
    cap_cald = max(cap["cald"], 0.001)
    cap_comp = max(cap["comp"], 0.001)
    cap_prin = max(cap["prin"], 0.001)

    # ── Niveles iniciales ─────────────────────────────────────────────────
    niv_aux  = _clamp(config["niv_aux"],  0.0, cap_aux)
    niv_cald = _clamp(config["niv_cald"], 0.0, cap_cald)
    niv_comp = _clamp(config["niv_comp"], 0.0, cap_comp)
    niv_prin = _clamp(config["niv_prin"], 0.0, cap_prin)

    # ── Caudales y consumos ───────────────────────────────────────────────
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

    # ── Carrotanques por hora ─────────────────────────────────────────────
    sum_aux_h  = (max(0.0, carrotanque_aux)  / horas) if usar_carrotanques else 0.0
    sum_comp_h = (max(0.0, carrotanque_comp) / horas) if usar_carrotanques else 0.0

    # ── Estado inicial de bombas/válvulas ─────────────────────────────────
    bomba_aux_cald_on    = q_aux_cald  > 0
    valvula_cald_comp_ab = q_cald_comp > 0
    bomba_comp_prin_on   = q_comp_prin > 0

    # ── Historial (hora 0 = estado inicial) ───────────────────────────────
    historial: list[dict[str, Any]] = []
    historial.append(_crear_registro(
        hora=0,
        niv_aux=niv_aux, niv_cald=niv_cald, niv_comp=niv_comp, niv_prin=niv_prin,
        cap_aux=cap_aux, cap_cald=cap_cald, cap_comp=cap_comp, cap_prin=cap_prin,
        mov_aux_cald=0, entrada_cald=0, consumo_cald=0,
        mover_cald_comp=0, entrada_comp=0, mover_comp_prin=0,
        entrada_ptar_ptap=0, consumo_areas=0, agua_carrotanques=0,
        modo_emergencia=False,
        bomba_aux=bomba_aux_cald_on, valvula_cald=valvula_cald_comp_ab,
        bomba_comp=bomba_comp_prin_on,
    ))

    # ── Bucle principal ───────────────────────────────────────────────────
    for hora_actual in range(1, horas + 1):

        # 1. Control automático de bombas/válvulas
        bomba_aux_cald_on = _evaluar_bomba_aux_cald(
            niv_cald, cap_cald, niv_aux, cap_aux, q_aux_cald, bomba_aux_cald_on)
        valvula_cald_comp_ab = _evaluar_valvula_cald_comp(
            niv_comp, cap_comp, niv_cald, cap_cald, q_cald_comp, valvula_cald_comp_ab)
        bomba_comp_prin_on = _evaluar_bomba_comp_prin(
            niv_prin, cap_prin, niv_comp, cap_comp, q_comp_prin, bomba_comp_prin_on)

        # 2. Modo emergencia
        modo_emergencia = niv_prin <= UMBRALES["emergencia_prin"] * cap_prin

        # 3. Flujo Aux → Cald
        niv_aux, niv_cald, mov_aux_cald = _flujo_aux_cald(
            niv_aux, niv_cald, cap_aux, cap_cald, q_aux_cald, bomba_aux_cald_on)

        # 4. Acueducto → Cald
        niv_cald, entrada_cald = _entrada_acueducto(niv_cald, cap_cald, entrada_acueducto_cald)

        # 5. Consumo vapor calderas
        niv_cald, consumo_cald = _consumo_vapor(niv_cald, cap_cald, consumo_calderas)

        # 6. Reguardia post-vapor
        if niv_cald <= UMBRALES["reserva_cald"] * cap_cald:
            valvula_cald_comp_ab = False

        # 7. Flujo Cald → Comp
        niv_cald, niv_comp, mover_cald_comp = _flujo_cald_comp(
            niv_cald, niv_comp, cap_cald, cap_comp, q_cald_comp, valvula_cald_comp_ab)

        # 8. Acueducto → Comp
        niv_comp, entrada_comp = _entrada_acueducto(niv_comp, cap_comp, entrada_acueducto_comp)

        # 9. Flujo Comp → Prin
        niv_comp, niv_prin, mover_comp_prin = _flujo_comp_prin(
            niv_comp, niv_prin, cap_comp, cap_prin, q_comp_prin, bomba_comp_prin_on)

        # 10. PTAR + PTAP → Prin
        entrada_ptar_ptap = min(q_ptar + q_ptap, max(0.0, cap_prin - niv_prin))
        niv_prin += entrada_ptar_ptap

        # 11. Consumo áreas
        niv_prin, consumo_areas = _consumo_areas(niv_prin, q_lav, q_tinto, modo_emergencia)

        # 12. Carrotanques
        niv_aux, niv_comp, agua_carrotanques = _suministro_carrotanques(
            niv_aux, niv_comp, cap_aux, cap_comp, sum_aux_h, sum_comp_h, usar_carrotanques)

        # 13. Clamping
        niv_aux  = _clamp(niv_aux,  0.0, cap_aux)
        niv_cald = _clamp(niv_cald, 0.0, cap_cald)
        niv_comp = _clamp(niv_comp, 0.0, cap_comp)
        niv_prin = _clamp(niv_prin, 0.0, cap_prin)

        # 14. Registro
        historial.append(_crear_registro(
            hora=hora_actual,
            niv_aux=niv_aux, niv_cald=niv_cald, niv_comp=niv_comp, niv_prin=niv_prin,
            cap_aux=cap_aux, cap_cald=cap_cald, cap_comp=cap_comp, cap_prin=cap_prin,
            mov_aux_cald=mov_aux_cald, entrada_cald=entrada_cald, consumo_cald=consumo_cald,
            mover_cald_comp=mover_cald_comp, entrada_comp=entrada_comp,
            mover_comp_prin=mover_comp_prin, entrada_ptar_ptap=entrada_ptar_ptap,
            consumo_areas=consumo_areas, agua_carrotanques=agua_carrotanques,
            modo_emergencia=modo_emergencia,
            bomba_aux=bomba_aux_cald_on, valvula_cald=valvula_cald_comp_ab,
            bomba_comp=bomba_comp_prin_on,
        ))

    return historial
