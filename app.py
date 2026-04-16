"""
app.py — Simulador de Tanques Interconectados
Interfaz Streamlit con diseño moderno y tanques animados.
"""

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from simulator import simular, CAP_DEFAULT

st.set_page_config(page_title="Simulador de Tanques", layout="wide", page_icon="🚰")

# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.block-container { padding-top: 1.5rem; padding-bottom: 3rem; }

/* Tarjetas de tanque */
.tank-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 16px 14px 12px;
    border: 1.5px solid #e2ddd6;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}
.tank-title {
    font-size: 11px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; font-family: 'DM Mono', monospace;
    margin-bottom: 6px;
}
.tank-pct {
    font-size: 32px; font-weight: 700;
    font-family: 'DM Mono', monospace;
    line-height: 1;
}
.tank-m3 {
    font-size: 13px; font-weight: 500;
    font-family: 'DM Mono', monospace;
    color: #57534e; margin-top: 2px;
}
.pump-badge {
    display: inline-block;
    font-size: 10px; font-family: 'DM Mono', monospace;
    padding: 3px 9px; border-radius: 20px;
    border: 1px solid; margin-top: 8px; font-weight: 500;
}
.badge-on    { color: #16a34a; border-color: #16a34a; background: rgba(22,163,74,.08); }
.badge-off   { color: #a8a29e; border-color: #d6d3d1; background: transparent; }
.badge-alarm { color: #dc2626; border-color: #dc2626; background: rgba(220,38,38,.08); }

/* Stat cards */
.stat-card {
    background: #ffffff;
    border-radius: 12px; padding: 14px 16px;
    border: 1px solid #e2ddd6;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    margin-bottom: 8px;
}
.stat-label { font-size: 11px; color: #a8a29e; font-family: 'DM Mono', monospace; margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; font-family: 'DM Mono', monospace; }

/* Alerta emergencia */
.alert-box {
    background: #fef2f2; border: 1.5px solid #dc2626;
    border-radius: 10px; padding: 12px 18px;
    color: #dc2626; font-weight: 600; font-size: 14px;
    margin-bottom: 16px;
}

/* Sección header */
.section-header {
    font-size: 11px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; color: #a8a29e;
    font-family: 'DM Mono', monospace;
    margin-bottom: 12px; margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)


# ── Función de gráficos ───────────────────────────────────────────────────────
def generar_graficos(historial, caps):
    colores = {'aux': '#2563eb', 'cald': '#16a34a', 'comp': '#ea580c', 'prin': '#7c3aed'}
    labels  = {'aux': 'Auxiliar', 'cald': 'Calderas', 'comp': 'Compresores', 'prin': 'Principal'}

    fig, axes = plt.subplots(3, 1, figsize=(11, 12))
    fig.patch.set_facecolor('#f4f1ec')
    for ax in axes:
        ax.set_facecolor('#ffffff')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#e2ddd6')
        ax.spines['bottom'].set_color('#e2ddd6')
        ax.tick_params(colors='#a8a29e', labelsize=9)
        ax.grid(True, linestyle='--', alpha=0.5, color='#e2ddd6')

    horas = [h['hora'] for h in historial if h['hora'] > 0]
    ax1, ax2, ax3 = axes

    # Gráfico 1: Niveles %
    for k in ['aux', 'cald', 'comp', 'prin']:
        vals = [h[f'{k}_pct'] for h in historial if h['hora'] > 0]
        ax1.plot(horas, vals, color=colores[k], linewidth=2.2, label=labels[k])
        ax1.axhline(y=90, color='#e2ddd6', linestyle='--', linewidth=0.8)
        ax1.axhline(y=70, color='#e2ddd6', linestyle=':',  linewidth=0.8)

    # Sombrear horas de emergencia
    for r in historial:
        if r.get('modo_emergencia') and r['hora'] > 0:
            ax1.axvspan(r['hora']-1, r['hora'], alpha=0.07, color='#dc2626')

    ax1.set_ylabel('Nivel (%)', color='#57534e', fontsize=10)
    ax1.set_title('Evolución de Niveles', fontsize=12, fontweight='600', color='#1c1917', pad=10)
    ax1.legend(fontsize=9, framealpha=0.8, edgecolor='#e2ddd6')
    ax1.set_ylim(0, 105)

    # Gráfico 2: Flujos apilados
    b1 = [h['mov_aux_cald']      for h in historial if h['hora'] > 0]
    b2 = [h['mover_cald_comp']   for h in historial if h['hora'] > 0]
    b3 = [h['mov_comp_prin']     for h in historial if h['hora'] > 0]
    b4 = [h['agua_carrotanques'] for h in historial if h['hora'] > 0]
    b5 = [h['entrada_ptar_ptap'] for h in historial if h['hora'] > 0]

    ax2.bar(horas, b1, label='Aux→Cald',    color='#2563eb', alpha=0.8)
    ax2.bar(horas, b2, label='Cald→Comp',   color='#16a34a', alpha=0.8, bottom=b1)
    ax2.bar(horas, b3, label='Comp→Prin',   color='#ea580c', alpha=0.8,
            bottom=[a+b for a,b in zip(b1,b2)])
    ax2.bar(horas, b5, label='PTAR+PTAP',   color='#0891b2', alpha=0.8,
            bottom=[a+b+c for a,b,c in zip(b1,b2,b3)])
    if any(v > 0 for v in b4):
        ax2.bar(horas, b4, label='Carrotanques', color='#7c3aed', alpha=0.8,
                bottom=[a+b+c+d for a,b,c,d in zip(b1,b2,b3,b5)])
    ax2.set_ylabel('Caudal (m³/h)', color='#57534e', fontsize=10)
    ax2.set_title('Flujos entre Tanques', fontsize=12, fontweight='600', color='#1c1917', pad=10)
    ax2.legend(fontsize=9, framealpha=0.8, edgecolor='#e2ddd6')

    # Gráfico 3: Balance hídrico
    entradas = [h['entrada_ptar_ptap']+h['entrada_cald_acu']+h['entrada_comp_acu']+h['agua_carrotanques']
                for h in historial if h['hora'] > 0]
    consumos = [h['consumo_areas']+h['consumo_cald'] for h in historial if h['hora'] > 0]
    ax3.bar(horas, entradas, width=0.4, label='Entradas',  color='#16a34a', alpha=0.85)
    ax3.bar([h+0.4 for h in horas], consumos, width=0.4, label='Consumos', color='#ea580c', alpha=0.85)
    ax3.set_xlabel('Tiempo (horas)', color='#57534e', fontsize=10)
    ax3.set_ylabel('Caudal (m³/h)',  color='#57534e', fontsize=10)
    ax3.set_title('Balance Hídrico', fontsize=12, fontweight='600', color='#1c1917', pad=10)
    ax3.legend(fontsize=9, framealpha=0.8, edgecolor='#e2ddd6')

    plt.tight_layout(pad=2.5)
    st.pyplot(fig)
    plt.close(fig)


def tank_html(key, label, color, pct, m3, cap, pump_label, pump_class):
    bar = f"""
    <div style="width:100%;height:90px;background:#f4f1ec;border-radius:8px;
                border:1px solid #cdc7be;position:relative;overflow:hidden;margin:10px 0 8px">
      <div style="position:absolute;bottom:0;left:0;right:0;height:{pct}%;
                  background:linear-gradient(to top,{color}cc,{color}44);
                  border-radius:0 0 7px 7px;transition:height 1s ease"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;
                  justify-content:center;font-size:22px;font-weight:700;
                  font-family:'DM Mono',monospace;color:{color};
                  text-shadow:0 1px 6px rgba(255,255,255,.8)">{pct}%</div>
    </div>"""
    return f"""
    <div class="tank-card">
      <div class="tank-title" style="color:{color}">{label}</div>
      {bar}
      <div class="tank-m3">{m3:.1f} m³ / {int(cap)} m³</div>
      <div class="pump-badge {pump_class}">{pump_label}</div>
    </div>"""


def stat_html(label, value, color):
    return f"""
    <div class="stat-card">
      <div class="stat-label">{label}</div>
      <div class="stat-value" style="color:{color}">{value}</div>
    </div>"""


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#fff;border:1px solid #e2ddd6;border-radius:16px;
            padding:18px 24px;margin-bottom:20px;
            box-shadow:0 1px 4px rgba(0,0,0,.07);
            display:flex;align-items:center;gap:14px">
  <div style="width:44px;height:44px;background:linear-gradient(135deg,#2563eb,#7c3aed);
              border-radius:12px;display:flex;align-items:center;
              justify-content:center;font-size:22px;flex-shrink:0">🚰</div>
  <div>
    <div style="font-size:18px;font-weight:700;color:#1c1917">Simulador de Tanques</div>
    <div style="font-size:12px;color:#a8a29e;font-family:'DM Mono',monospace">
      flujo de agua entre tanques interconectados</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">Capacidades (m³)</div>', unsafe_allow_html=True)
    cap_aux  = st.number_input("Auxiliar",    min_value=0.1, value=CAP_DEFAULT["aux"],  step=10.0)
    cap_cald = st.number_input("Calderas",    min_value=0.1, value=CAP_DEFAULT["cald"], step=10.0)
    cap_comp = st.number_input("Compresores", min_value=0.1, value=CAP_DEFAULT["comp"], step=10.0)
    cap_prin = st.number_input("Principal",   min_value=0.1, value=CAP_DEFAULT["prin"], step=10.0)
    capacidades = {"aux": cap_aux, "cald": cap_cald, "comp": cap_comp, "prin": cap_prin}

    st.divider()
    st.markdown('<div class="section-header">Niveles iniciales (%)</div>', unsafe_allow_html=True)
    pct_aux  = st.slider("Auxiliar",    0, 100, 70, key="s_aux")
    pct_cald = st.slider("Calderas",    0, 100, 70, key="s_cald")
    pct_comp = st.slider("Compresores", 0, 100, 70, key="s_comp")
    pct_prin = st.slider("Principal",   0, 100, 80, key="s_prin")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Caudales", "🏭 Consumos y Entradas", "🚛 Carrotanques", "⏱ Simulación"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        q_aux_cald  = st.number_input("Aux → Calderas (m³/h)",   min_value=0.0, value=15.0)
        q_cald_comp = st.number_input("Cald → Compresores (m³/h)",min_value=0.0, value=10.0)
        q_comp_prin = st.number_input("Comp → Principal (m³/h)",  min_value=0.0, value=20.0)
    with c2:
        q_ptar = st.number_input("PTAR → Principal (m³/h)", min_value=0.0, value=5.0)
        q_ptap = st.number_input("PTAP → Principal (m³/h)", min_value=0.0, value=5.0)
        consumo_calderas = st.number_input("Consumo Calderas (m³/h)", min_value=0.0, value=8.0)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        q_lav   = st.number_input("Lavandería (m³/h)",  min_value=0.0, max_value=80.0, value=8.0)
        q_tinto = st.number_input("Tintorería (m³/h)",  min_value=0.0, max_value=80.0, value=6.0)
    with c2:
        ent_cald = st.number_input("Acueducto → Calderas (m³/h)",    min_value=0.0, value=10.0)
        ent_comp = st.number_input("Acueducto → Compresores (m³/h)", min_value=0.0, value=25.0)

with tab3:
    usar_carrotanques = st.checkbox("Activar carrotanques")
    if usar_carrotanques:
        c1, c2 = st.columns(2)
        with c1:
            carro_aux  = st.number_input("Volumen para Auxiliar (m³)",    min_value=0.0, value=0.0)
        with c2:
            carro_comp = st.number_input("Volumen para Compresores (m³)", min_value=0.0, value=0.0)
    else:
        carro_aux = carro_comp = 0.0

with tab4:
    horas_sim = st.slider("Horas a simular", 1, 72, 24)

# ── CONFIG ────────────────────────────────────────────────────────────────────
config = {
    "niv_aux":  pct_aux  / 100 * cap_aux,
    "niv_cald": pct_cald / 100 * cap_cald,
    "niv_comp": pct_comp / 100 * cap_comp,
    "niv_prin": pct_prin / 100 * cap_prin,
    "q_aux_cald": q_aux_cald, "q_cald_comp": q_cald_comp, "q_comp_prin": q_comp_prin,
    "q_ptar": q_ptar, "q_ptap": q_ptap,
    "q_lav": q_lav, "q_tinto": q_tinto,
    "entrada_acueducto_cald": ent_cald,
    "entrada_acueducto_comp": ent_comp,
    "consumo_calderas": consumo_calderas,
}

# ── BOTÓN ─────────────────────────────────────────────────────────────────────
col_btn, col_space = st.columns([1, 3])
with col_btn:
    ejecutar = st.button("▶ Ejecutar Simulación", type="primary", use_container_width=True)

if ejecutar:
    with st.spinner("Simulando..."):
        resultados = simular(
            horas_sim, config,
            capacidades=capacidades,
            usar_carrotanques=usar_carrotanques,
            carrotanque_aux=carro_aux,
            carrotanque_comp=carro_comp,
        )

    # ── ALERTA EMERGENCIA ────────────────────────────────────────────────────
    horas_em = [r['hora'] for r in resultados if r.get('modo_emergencia')]
    if horas_em:
        st.markdown(
            f'<div class="alert-box">⚠️ Modo emergencia en horas: {horas_em} '
            f'— Consumos reducidos al 50%</div>', unsafe_allow_html=True)

    ultimo = resultados[-1]

    # ── TANQUES ANIMADOS ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:8px">Estado final de tanques</div>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    def pump_info(on, lbl_on, lbl_off, alarm=False):
        if alarm: return lbl_on, "badge-alarm"
        return (lbl_on, "badge-on") if on else (lbl_off, "badge-off")

    with col1:
        pct = round(ultimo['aux_pct'])
        lbl, cls = pump_info(ultimo['estado_bomba_aux'], "Bomba ON", "Bomba OFF")
        st.markdown(tank_html("aux","AUXILIAR","#2563eb", pct,
            ultimo['aux_m3'], cap_aux, lbl, cls), unsafe_allow_html=True)

    with col2:
        pct = round(ultimo['cald_pct'])
        lbl, cls = pump_info(ultimo['estado_valvula_cald'], "Válvula abierta", "Válvula cerrada")
        st.markdown(tank_html("cald","CALDERAS","#16a34a", pct,
            ultimo['cald_m3'], cap_cald, lbl, cls), unsafe_allow_html=True)

    with col3:
        pct = round(ultimo['comp_pct'])
        lbl, cls = pump_info(ultimo['estado_bomba_comp'], "Bomba ON", "Bomba OFF")
        st.markdown(tank_html("comp","COMPRESORES","#ea580c", pct,
            ultimo['comp_m3'], cap_comp, lbl, cls), unsafe_allow_html=True)

    with col4:
        pct = round(ultimo['prin_pct'])
        alarm = ultimo.get('modo_emergencia', False)
        lbl = "⚠ Emergencia" if alarm else "Normal"
        cls = "badge-alarm" if alarm else "badge-on"
        st.markdown(tank_html("prin","PRINCIPAL","#7c3aed", pct,
            ultimo['prin_m3'], cap_prin, lbl, cls), unsafe_allow_html=True)

    # ── STATS HORA A HORA ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:16px">Estadísticas hora a hora</div>',
                unsafe_allow_html=True)

    hora_sel = st.slider("Explorar hora", 0, len(resultados)-1, len(resultados)-1)
    rec = resultados[hora_sel]

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    with s1: st.markdown(stat_html("Consumo Áreas", f"{rec['consumo_areas']:.1f} m³","#ea580c"), unsafe_allow_html=True)
    with s2: st.markdown(stat_html("Flujo Aux→Cald", f"{rec['mov_aux_cald']:.1f} m³","#2563eb"), unsafe_allow_html=True)
    with s3: st.markdown(stat_html("Flujo Comp→Prin", f"{rec['mov_comp_prin']:.1f} m³","#7c3aed"), unsafe_allow_html=True)
    with s4: st.markdown(stat_html("PTAR + PTAP", f"{rec['entrada_ptar_ptap']:.1f} m³","#0891b2"), unsafe_allow_html=True)
    with s5: st.markdown(stat_html("Carrotanques", f"{rec['agua_carrotanques']:.1f} m³","#7c3aed"), unsafe_allow_html=True)
    with s6:
        emerg = rec.get('modo_emergencia', False)
        st.markdown(stat_html("Emergencia", "Sí ⚠" if emerg else "No",
                               "#dc2626" if emerg else "#16a34a"), unsafe_allow_html=True)

    # ── GRÁFICOS ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:16px">Gráficas</div>',
                unsafe_allow_html=True)
    generar_graficos(resultados, capacidades)

    # ── TABLA + DESCARGA ─────────────────────────────────────────────────────
    with st.expander("📋 Ver tabla completa hora a hora"):
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True)

    csv = pd.DataFrame(resultados).to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", csv, "simulacion.csv", "text/csv")
