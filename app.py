"""
app.py
======
Interfaz Streamlit del Simulador de Tanques Interconectados.
La lógica de simulación vive en simulator.py.
"""

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from simulator import simular, CAP_DEFAULT

st.set_page_config(page_title="Simulador de Tanques", layout="wide")
st.title("🚰 Simulador de Sistema de Tanques Interconectados")


def _generar_graficos(historial, caps):
    cap_aux  = caps["aux"]
    cap_cald = caps["cald"]
    cap_comp = caps["comp"]
    cap_prin = caps["prin"]

    fig, axes = plt.subplots(3, 1, figsize=(11, 13))
    ax1, ax2, ax3 = axes
    horas = [h["hora"] for h in historial if h["hora"] > 0]

    ax1.plot(horas, [h["aux_m3"]  for h in historial if h["hora"] > 0], "b-", label="Auxiliar",    linewidth=2)
    ax1.plot(horas, [h["cald_m3"] for h in historial if h["hora"] > 0], "g-", label="Calderas",    linewidth=2)
    ax1.plot(horas, [h["comp_m3"] for h in historial if h["hora"] > 0], "r-", label="Compresores", linewidth=2)
    ax1.plot(horas, [h["prin_m3"] for h in historial if h["hora"] > 0], "m-", label="Principal",   linewidth=2)

    for color, cap in [("b", cap_aux), ("g", cap_cald), ("r", cap_comp), ("m", cap_prin)]:
        ax1.axhline(y=0.9 * cap, color=color, linestyle="--", alpha=0.3)
        ax1.axhline(y=0.7 * cap, color=color, linestyle=":",  alpha=0.3)

    for h in [r["hora"] for r in historial if r.get("modo_emergencia")]:
        ax1.axvspan(h - 1, h, alpha=0.08, color="red")

    ax1.set_title("Evolucion de Niveles (--- 90%  ···70%  emergencia en rojo)")
    ax1.set_ylabel("Volumen (m3)")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.5)

    b1 = [h["mov_aux_cald"]      for h in historial if h["hora"] > 0]
    b2 = [h["mover_cald_comp"]   for h in historial if h["hora"] > 0]
    b3 = [h["mov_comp_prin"]     for h in historial if h["hora"] > 0]
    b4 = [h["agua_carrotanques"] for h in historial if h["hora"] > 0]

    ax2.bar(horas, b1, label="Aux->Cald",  color="steelblue", alpha=0.8)
    ax2.bar(horas, b2, label="Cald->Comp", color="seagreen",  alpha=0.8, bottom=b1)
    ax2.bar(horas, b3, label="Comp->Prin", color="tomato",    alpha=0.8,
            bottom=[a + b for a, b in zip(b1, b2)])
    if any(v > 0 for v in b4):
        ax2.bar(horas, b4, label="Carrotanques", color="darkorange", alpha=0.8,
                bottom=[a + b + c for a, b, c in zip(b1, b2, b3)])

    ax2.set_title("Flujos entre Tanques (m3/h)")
    ax2.set_ylabel("Caudal (m3/h)")
    ax2.legend()
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)

    entradas = [h["entrada_ptar_ptap"] + h["entrada_cald_acu"] + h["entrada_comp_acu"] + h["agua_carrotanques"]
                for h in historial if h["hora"] > 0]
    consumos = [h["consumo_areas"] + h["consumo_cald"] for h in historial if h["hora"] > 0]

    ax3.bar(horas, entradas, width=0.4, label="Entradas",  color="#2ecc71", alpha=0.85)
    ax3.bar([h + 0.4 for h in horas], consumos, width=0.4, label="Consumos", color="#e74c3c", alpha=0.85)
    ax3.set_title("Balance Hidrico (m3/h)")
    ax3.set_xlabel("Tiempo (horas)")
    ax3.set_ylabel("Caudal (m3/h)")
    ax3.legend()
    ax3.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


with st.sidebar:
    st.header("Configuracion Inicial")

    st.subheader("Capacidades de Tanques (m3)")
    cap_aux  = st.number_input("Auxiliar",    min_value=0.1, value=CAP_DEFAULT["aux"],  step=10.0)
    cap_cald = st.number_input("Calderas",    min_value=0.1, value=CAP_DEFAULT["cald"], step=10.0)
    cap_comp = st.number_input("Compresores", min_value=0.1, value=CAP_DEFAULT["comp"], step=10.0)
    cap_prin = st.number_input("Principal",   min_value=0.1, value=CAP_DEFAULT["prin"], step=10.0)

    capacidades = {"aux": cap_aux, "cald": cap_cald, "comp": cap_comp, "prin": cap_prin}

    st.subheader("Niveles Iniciales (%)")
    pct_aux  = st.slider("Auxiliar",    0, 100, 70)
    pct_cald = st.slider("Calderas",    0, 100, 70)
    pct_comp = st.slider("Compresores", 0, 100, 70)
    pct_prin = st.slider("Principal",   0, 100, 80)

tab1, tab2, tab3 = st.tabs(["Flujos", "Consumos y Entradas", "Carrotanques"])

with tab1:
    st.subheader("Caudales entre tanques")
    c1, c2 = st.columns(2)
    with c1:
        q_aux_cald  = st.number_input("Caudal Aux->Cald (m3/h)",  min_value=0.0, value=15.0)
        q_cald_comp = st.number_input("Caudal Cald->Comp (m3/h)", min_value=0.0, value=10.0)
        q_comp_prin = st.number_input("Caudal Comp->Prin (m3/h)", min_value=0.0, value=20.0)
    with c2:
        q_ptar           = st.number_input("Caudal PTAR (m3/h)",     min_value=0.0, value=5.0)
        q_ptap           = st.number_input("Caudal PTAP (m3/h)",     min_value=0.0, value=5.0)
        consumo_calderas = st.number_input("Consumo Calderas (m3/h)", min_value=0.0, value=8.0)

with tab2:
    st.subheader("Consumos y entradas de acueducto")
    c1, c2 = st.columns(2)
    with c1:
        q_lav   = st.number_input("Consumo Lavanderia (m3/h)", min_value=0.0, value=8.0)
        q_tinto = st.number_input("Consumo Tintoreria (m3/h)", min_value=0.0, value=6.0)
    with c2:
        entrada_acueducto_cald = st.number_input("Acueducto -> Calderas (m3/h)",    min_value=0.0, value=10.0)
        entrada_acueducto_comp = st.number_input("Acueducto -> Compresores (m3/h)", min_value=0.0, value=25.0)

with tab3:
    st.subheader("Suministro extra por carrotanques")
    usar_carrotanques = st.checkbox("Activar carrotanques")
    if usar_carrotanques:
        carrotanque_aux  = st.number_input("Volumen para Auxiliar (m3)",    min_value=0.0, value=0.0)
        carrotanque_comp = st.number_input("Volumen para Compresores (m3)", min_value=0.0, value=0.0)
    else:
        carrotanque_aux = carrotanque_comp = 0.0

horas_simulacion = st.slider("Horas a simular", 1, 72, 24)

config = {
    "niv_aux":  pct_aux  / 100 * cap_aux,
    "niv_cald": pct_cald / 100 * cap_cald,
    "niv_comp": pct_comp / 100 * cap_comp,
    "niv_prin": pct_prin / 100 * cap_prin,
    "q_aux_cald": q_aux_cald, "q_cald_comp": q_cald_comp, "q_comp_prin": q_comp_prin,
    "q_ptar": q_ptar, "q_ptap": q_ptap, "q_lav": q_lav, "q_tinto": q_tinto,
    "entrada_acueducto_cald": entrada_acueducto_cald,
    "entrada_acueducto_comp": entrada_acueducto_comp,
    "consumo_calderas": consumo_calderas,
}

if st.button("Ejecutar Simulacion", type="primary"):
    with st.spinner("Simulando..."):
        resultados = simular(
            horas_simulacion, config,
            capacidades=capacidades,
            usar_carrotanques=usar_carrotanques,
            carrotanque_aux=carrotanque_aux,
            carrotanque_comp=carrotanque_comp,
        )

    st.success("Simulacion completada")

    horas_emergencia = [r["hora"] for r in resultados if r.get("modo_emergencia")]
    if horas_emergencia:
        st.warning(
            f"Modo emergencia activado en las horas: {horas_emergencia}. "
            "Consumos de lavanderia y tintoreria reducidos al 50%."
        )

    ultimo = resultados[-1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Auxiliar Final",    f"{ultimo['aux_m3']:.1f} m3",  f"{ultimo['aux_pct']:.1f}%")
    with col2:
        st.metric("Calderas Final",    f"{ultimo['cald_m3']:.1f} m3", f"{ultimo['cald_pct']:.1f}%")
    with col3:
        st.metric("Compresores Final", f"{ultimo['comp_m3']:.1f} m3", f"{ultimo['comp_pct']:.1f}%")
    with col4:
        st.metric("Principal Final",   f"{ultimo['prin_m3']:.1f} m3", f"{ultimo['prin_pct']:.1f}%")

    _generar_graficos(resultados, capacidades)

    st.subheader("Resultados hora a hora")
    df = pd.DataFrame(resultados)
    df_display = df[["hora", "aux_m3", "aux_pct", "cald_m3", "cald_pct",
                      "comp_m3", "comp_pct", "prin_m3", "prin_pct",
                      "consumo_areas", "agua_carrotanques", "modo_emergencia"]].copy()
    df_display.columns = [
        "Hora", "Aux (m3)", "Aux (%)", "Cald (m3)", "Cald (%)",
        "Comp (m3)", "Comp (%)", "Prin (m3)", "Prin (%)",
        "Consumo Areas", "Carrotanques", "Emergencia",
    ]
    st.dataframe(df_display, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar resultados CSV", csv, "resultados_simulacion.csv", "text/csv")
