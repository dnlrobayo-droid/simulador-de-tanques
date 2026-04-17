"""
tests/test_simulator.py
========================
Pruebas unitarias para simulator.py.
Ejecutar con:  python -m pytest tests/ -v
"""

import pytest
from simulator import simular
from config import CAP_DEFAULT


# ── Fixtures ──────────────────────────────────────────────────────────────────

def config_base(**kwargs):
    """Configuración mínima válida con valores por defecto."""
    base = {
        "niv_aux":  280.0,  # 70 %
        "niv_cald":  63.0,  # 70 %
        "niv_comp":  84.0,  # 70 %
        "niv_prin": 400.0,  # 80 %
        "q_aux_cald":  15.0,
        "q_cald_comp": 10.0,
        "q_comp_prin": 20.0,
        "q_ptar": 5.0, "q_ptap": 5.0,
        "q_lav":  8.0, "q_tinto": 6.0,
        "entrada_acueducto_cald": 10.0,
        "entrada_acueducto_comp": 25.0,
        "consumo_calderas": 8.0,
    }
    base.update(kwargs)
    return base


# ── Tests básicos ─────────────────────────────────────────────────────────────

class TestSalidaBasica:
    def test_retorna_lista(self):
        resultado = simular(1, config_base())
        assert isinstance(resultado, list)

    def test_longitud_historial(self):
        """Debe haber hora 0 + N horas = N+1 registros."""
        for n in [1, 5, 24]:
            assert len(simular(n, config_base())) == n + 1

    def test_hora_cero_es_estado_inicial(self):
        cfg = config_base()
        hist = simular(3, cfg)
        assert hist[0]["hora"] == 0
        assert hist[0]["aux_m3"] == round(cfg["niv_aux"], 2)

    def test_claves_presentes(self):
        claves_requeridas = {
            "hora", "aux_m3", "cald_m3", "comp_m3", "prin_m3",
            "aux_pct", "cald_pct", "comp_pct", "prin_pct",
            "mov_aux_cald", "mover_cald_comp", "mov_comp_prin",
            "consumo_areas", "agua_carrotanques", "modo_emergencia",
            "estado_bomba_aux", "estado_valvula_cald", "estado_bomba_comp",
        }
        hist = simular(1, config_base())
        for registro in hist:
            assert claves_requeridas.issubset(registro.keys()), \
                f"Faltan claves en hora {registro['hora']}"


# ── Tests de conservación de volumen ─────────────────────────────────────────

class TestFisica:
    def test_niveles_no_negativos(self):
        """Ningún tanque puede quedar en negativo."""
        hist = simular(48, config_base(niv_aux=5.0, niv_cald=5.0))
        for r in hist:
            assert r["aux_m3"]  >= 0, f"Auxiliar negativo en hora {r['hora']}"
            assert r["cald_m3"] >= 0, f"Calderas negativo en hora {r['hora']}"
            assert r["comp_m3"] >= 0, f"Compresores negativo en hora {r['hora']}"
            assert r["prin_m3"] >= 0, f"Principal negativo en hora {r['hora']}"

    def test_niveles_no_superan_capacidad(self):
        caps = {"aux": 400.0, "cald": 90.0, "comp": 120.0, "prin": 500.0}
        hist = simular(24, config_base(), capacidades=caps)
        for r in hist:
            assert r["aux_m3"]  <= caps["aux"]  + 0.01
            assert r["cald_m3"] <= caps["cald"]  + 0.01
            assert r["comp_m3"] <= caps["comp"]  + 0.01
            assert r["prin_m3"] <= caps["prin"]  + 0.01

    def test_porcentajes_entre_0_y_100(self):
        hist = simular(24, config_base())
        for r in hist:
            for k in ["aux_pct", "cald_pct", "comp_pct", "prin_pct"]:
                assert 0.0 <= r[k] <= 100.0, f"{k} fuera de rango en hora {r['hora']}"


# ── Tests de lógica de control ────────────────────────────────────────────────

class TestControlAutomatico:
    def test_sin_caudal_no_hay_flujo(self):
        cfg = config_base(q_aux_cald=0.0, q_cald_comp=0.0, q_comp_prin=0.0)
        hist = simular(5, cfg)
        for r in hist[1:]:
            assert r["mov_aux_cald"]    == 0.0
            assert r["mover_cald_comp"] == 0.0
            assert r["mov_comp_prin"]   == 0.0

    def test_emergencia_activa_cuando_principal_bajo(self):
        """Con tanque principal casi vacío debe activarse emergencia."""
        cfg = config_base(
            niv_prin=10.0,
            q_ptar=0.0, q_ptap=0.0,
            entrada_acueducto_comp=0.0,
        )
        hist = simular(3, cfg)
        assert hist[1]["modo_emergencia"] is True

    def test_consumo_reducido_en_emergencia(self):
        """En emergencia el consumo de áreas debe ser <= 50% del normal."""
        q_lav, q_tinto = 8.0, 6.0
        consumo_normal_max = q_lav + q_tinto
        cfg = config_base(
            niv_prin=10.0, q_ptar=0.0, q_ptap=0.0,
            entrada_acueducto_comp=0.0, q_lav=q_lav, q_tinto=q_tinto,
        )
        hist = simular(3, cfg)
        for r in hist[1:]:
            if r["modo_emergencia"]:
                assert r["consumo_areas"] <= consumo_normal_max * 0.5 + 0.01

    def test_bomba_off_cuando_destino_lleno(self):
        """Si Calderas está al 95%, la bomba Aux→Cald debe apagarse."""
        cfg = config_base(niv_cald=85.5)  # 95% de 90 m³
        hist = simular(1, cfg)
        assert hist[1]["estado_bomba_aux"] is False
        assert hist[1]["mov_aux_cald"] == 0.0

    def test_valvula_cierra_destino_lleno(self):
        """Si Compresores ≥ 90%, la válvula debe cerrarse."""
        cfg = config_base(niv_comp=108.0)  # 90% de 120 m³
        hist = simular(1, cfg)
        assert hist[1]["estado_valvula_cald"] is False


# ── Tests de reguardia post-vapor (bug crítico corregido) ────────────────────

class TestReguardiaPostVapor:
    def test_calderas_nunca_baja_del_30_pct(self):
        """Calderas nunca debe bajar por debajo de su reserva del 30%."""
        cfg = config_base(
            niv_cald=30.0,           # ~33% de 90 m³, justo sobre el límite
            consumo_calderas=20.0,   # consumo alto
            q_aux_cald=0.0,          # sin reposición
            entrada_acueducto_cald=0.0,
        )
        hist = simular(10, cfg)
        for r in hist:
            assert r["cald_m3"] >= 27.0 - 0.01, \
                f"Calderas bajó a {r['cald_m3']} m³ en hora {r['hora']} (mín: 27 m³)"

    def test_valvula_cierra_post_vapor(self):
        """Tras consumo de vapor, si Cald ≤ 30%, la válvula debe cerrarse."""
        cfg = config_base(
            niv_cald=28.0,           # justo sobre reserva
            consumo_calderas=5.0,
            q_aux_cald=0.0,
            entrada_acueducto_cald=0.0,
        )
        hist = simular(3, cfg)
        # En horas donde Calderas está al mínimo, la válvula debe estar cerrada
        for r in hist[1:]:
            if r["cald_m3"] <= 27.01:
                assert r["estado_valvula_cald"] is False, \
                    f"Válvula abierta con Cald={r['cald_m3']} en hora {r['hora']}"

    def test_flujo_cald_comp_limitado_por_reserva(self):
        """El flujo Cald→Comp no debe sacar agua por debajo de la reserva."""
        cfg = config_base(
            niv_cald=30.0,
            q_cald_comp=50.0,        # intentar sacar mucho
            consumo_calderas=0.0,
            q_aux_cald=0.0,
            entrada_acueducto_cald=0.0,
        )
        hist = simular(5, cfg)
        for r in hist:
            assert r["cald_m3"] >= 27.0 - 0.01


# ── Tests de tanque destino casi lleno ────────────────────────────────────────

class TestTanqueDestinoLleno:
    def test_flujo_limitado_por_espacio_destino(self):
        """Si Calderas tiene poco espacio, el flujo debe limitarse a ese espacio."""
        cfg = config_base(
            niv_cald=88.0,       # solo 2 m³ de espacio
            q_aux_cald=50.0,     # quiere enviar 50
        )
        hist = simular(1, cfg)
        # El flujo no puede ser mayor al espacio disponible (2 m³)
        assert hist[1]["mov_aux_cald"] <= 2.01

    def test_principal_no_desborda_con_muchas_entradas(self):
        """Principal no debe superar capacidad aunque reciba por múltiples fuentes."""
        cfg = config_base(
            niv_prin=490.0,      # casi lleno
            q_ptar=20.0, q_ptap=20.0,
            q_comp_prin=40.0,
        )
        caps = {"aux": 400.0, "cald": 90.0, "comp": 120.0, "prin": 500.0}
        hist = simular(5, cfg, capacidades=caps)
        for r in hist:
            assert r["prin_m3"] <= 500.01


# ── Tests de carrotanques ─────────────────────────────────────────────────────

class TestCarrotanques:
    def test_sin_carrotanques_no_aporta(self):
        hist = simular(5, config_base(), usar_carrotanques=False)
        for r in hist:
            assert r["agua_carrotanques"] == 0.0

    def test_con_carrotanques_aporta_agua(self):
        hist = simular(10, config_base(niv_aux=0.0),
                       usar_carrotanques=True,
                       carrotanque_aux=100.0)
        total = sum(r["agua_carrotanques"] for r in hist)
        assert total > 0.0

    def test_carrotanques_no_supera_capacidad(self):
        caps = {"aux": 400.0, "cald": 90.0, "comp": 120.0, "prin": 500.0}
        hist = simular(5, config_base(),
                       capacidades=caps,
                       usar_carrotanques=True,
                       carrotanque_aux=9999.0)
        for r in hist:
            assert r["aux_m3"] <= caps["aux"] + 0.01

    def test_carrotanques_con_acueducto_simultaneo(self):
        """Carrotanques + acueducto simultáneo no debe superar capacidad."""
        caps = {"aux": 400.0, "cald": 90.0, "comp": 120.0, "prin": 500.0}
        cfg = config_base(
            niv_comp=100.0,
            entrada_acueducto_comp=50.0,
        )
        hist = simular(10, cfg, capacidades=caps,
                       usar_carrotanques=True, carrotanque_comp=500.0)
        for r in hist:
            assert r["comp_m3"] <= caps["comp"] + 0.01


# ── Tests de validación de entradas ──────────────────────────────────────────

class TestValidacion:
    def test_horas_cero_lanza_error(self):
        with pytest.raises(ValueError):
            simular(0, config_base())

    def test_horas_negativas_lanza_error(self):
        with pytest.raises(ValueError):
            simular(-5, config_base())

    def test_capacidad_cero_no_lanza_excepcion(self):
        """La función debe resistir capacidades=0 sin lanzar ZeroDivisionError."""
        caps = {"aux": 0.0, "cald": 0.0, "comp": 0.0, "prin": 0.0}
        try:
            simular(2, config_base(niv_aux=0, niv_cald=0, niv_comp=0, niv_prin=0),
                    capacidades=caps)
        except ZeroDivisionError:
            pytest.fail("simular() lanzó ZeroDivisionError con capacidad=0")

    def test_config_incompleta_lanza_error(self):
        """Si faltan claves en config, debe lanzar ValueError con mensaje claro."""
        config_parcial = {"niv_aux": 100.0, "niv_cald": 50.0}
        with pytest.raises(ValueError, match="Faltan claves"):
            simular(1, config_parcial)

    def test_config_vacia_lanza_error(self):
        with pytest.raises(ValueError, match="Faltan claves"):
            simular(1, {})


# ── Tests de funciones extraídas ──────────────────────────────────────────────

class TestFuncionesExtraidas:
    def test_safe_pct_capacidad_cero(self):
        from simulator import _safe_pct
        assert _safe_pct(50.0, 0.0) == 0.0

    def test_safe_pct_normal(self):
        from simulator import _safe_pct
        assert _safe_pct(45.0, 90.0) == 50.0

    def test_clamp(self):
        from simulator import _clamp
        assert _clamp(-5.0, 0.0, 100.0) == 0.0
        assert _clamp(150.0, 0.0, 100.0) == 100.0
        assert _clamp(50.0, 0.0, 100.0) == 50.0
