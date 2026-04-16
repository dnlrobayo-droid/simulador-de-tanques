"""
tests/test_simulator.py
========================
Pruebas unitarias para simulator.py.
Ejecutar con:  python -m pytest tests/ -v
"""

import pytest
from simulator import simular, CAP_DEFAULT


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
            niv_prin=10.0,   # muy bajo
            q_ptar=0.0, q_ptap=0.0,
            entrada_acueducto_comp=0.0,
        )
        hist = simular(3, cfg)
        # Al menos la primera hora debe estar en emergencia
        assert hist[1]["modo_emergencia"] is True

    def test_consumo_reducido_en_emergencia(self):
        """En emergencia el consumo de áreas debe ser <= 50 % del normal."""
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


# ── Tests de validación de entradas ──────────────────────────────────────────

class TestValidacion:
    def test_horas_cero_lanza_error(self):
        with pytest.raises(ValueError):
            simular(0, config_base())

    def test_horas_negativas_lanza_error(self):
        with pytest.raises(ValueError):
            simular(-5, config_base())

    def test_capacidad_cero_no_lanza_excepcion(self):
        """La función debe resistir capacidades=0 sin lanzar ZeroDivisionError.
        Internamente las clampea a 0.001 para evitar la división por cero."""
        caps = {"aux": 0.0, "cald": 0.0, "comp": 0.0, "prin": 0.0}
        try:
            simular(2, config_base(niv_aux=0, niv_cald=0, niv_comp=0, niv_prin=0),
                    capacidades=caps)
        except ZeroDivisionError:
            pytest.fail("simular() lanzó ZeroDivisionError con capacidad=0")
