"""
app.py — Simulador de Tanques Interconectados
Interfaz Streamlit con diseño moderno, gráficos Plotly interactivos,
diagrama del sistema, presets de escenarios y tanques dinámicos.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from simulator import simular
from config import CAP_DEFAULT, COLORES, LABELS, PRESETS, UMBRALES

st.set_page_config(page_title="Simulador de Tanques", layout="wide", page_icon="🚰")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; }

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

.stat-card {
    background: #ffffff;
    border-radius: 12px; padding: 14px 16px;
    border: 1px solid #e2ddd6;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    margin-bottom: 8px;
}
.stat-label { font-size: 11px; color: #a8a29e; font-family: 'DM Mono', monospace; margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; font-family: 'DM Mono', monospace; }

.alert-box {
    background: #fef2f2; border: 1.5px solid #dc2626;
    border-radius: 10px; padding: 12px 18px;
    color: #dc2626; font-weight: 600; font-size: 14px;
    margin-bottom: 16px;
}

.section-header {
    font-size: 11px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; color: #a8a29e;
    font-family: 'DM Mono', monospace;
    margin-bottom: 12px; margin-top: 4px;
}

.preset-info {
    background: #f0f9ff; border: 1px solid #bae6fd;
    border-radius: 8px; padding: 10px 14px;
    font-size: 13px; color: #0369a1;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers HTML ──────────────────────────────────────────────────────────────

def tank_html(label, color, pct, m3, cap, pump_label, pump_class):
    pct_display = max(0, min(100, round(pct)))
    bar = f"""
    <div style="width:100%;height:90px;background:#f4f1ec;border-radius:8px;
                border:1px solid #cdc7be;position:relative;overflow:hidden;margin:10px 0 8px">
      <div style="position:absolute;bottom:0;left:0;right:0;height:{pct_display}%;
                  background:linear-gradient(to top,{color}cc,{color}44);
                  border-radius:0 0 7px 7px;transition:height 1s ease"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;
                  justify-content:center;font-size:22px;font-weight:700;
                  font-family:'DM Mono',monospace;color:{color};
                  text-shadow:0 1px 6px rgba(255,255,255,.8)">{pct_display}%</div>
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


def pump_info(on, lbl_on, lbl_off, alarm=False):
    if alarm:
        return lbl_on, "badge-alarm"
    return (lbl_on, "badge-on") if on else (lbl_off, "badge-off")


def formato_rangos_emergencia(horas_em):
    """Convierte lista de horas [5,6,7,8,20,21] en rangos legibles: '5–8, 20–21'."""
    if not horas_em:
        return ""
    rangos = []
    inicio = horas_em[0]
    fin = horas_em[0]
    for h in horas_em[1:]:
        if h == fin + 1:
            fin = h
        else:
            rangos.append(f"{inicio}–{fin}" if inicio != fin else str(inicio))
            inicio = fin = h
    rangos.append(f"{inicio}–{fin}" if inicio != fin else str(inicio))
    return ", ".join(rangos)


# ── Diagrama SVG del sistema ──────────────────────────────────────────────────

def diagrama_sistema_svg(rec=None):
    """Genera un diagrama SVG del sistema de tanques con estados actuales."""
    # Estados por defecto si no hay datos
    b_aux = rec.get("estado_bomba_aux", False) if rec else False
    v_cald = rec.get("estado_valvula_cald", False) if rec else False
    b_comp = rec.get("estado_bomba_comp", False) if rec else False
    emerg = rec.get("modo_emergencia", False) if rec else False

    c_on = "#16a34a"
    c_off = "#a8a29e"
    c_alarm = "#dc2626"

    b_aux_c = c_on if b_aux else c_off
    v_cald_c = c_on if v_cald else c_off
    b_comp_c = c_on if b_comp else c_off
    emerg_c = c_alarm if emerg else c_on

    b_aux_t = "ON" if b_aux else "OFF"
    v_cald_t = "ABIERTA" if v_cald else "CERRADA"
    b_comp_t = "ON" if b_comp else "OFF"
    emerg_t = "EMERGENCIA" if emerg else "NORMAL"

    svg = f"""
    <svg viewBox="0 0 820 320" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:820px;font-family:'DM Sans',sans-serif">
      <!-- Fondo -->
      <rect width="820" height="320" rx="16" fill="#faf9f7" stroke="#e2ddd6" stroke-width="1.5"/>

      <!-- Tanque Auxiliar -->
      <rect x="30" y="60" width="140" height="100" rx="10" fill="#2563eb22" stroke="#2563eb" stroke-width="2"/>
      <text x="100" y="50" text-anchor="middle" font-size="12" font-weight="600" fill="#2563eb" letter-spacing="1">AUXILIAR</text>
      <text x="100" y="115" text-anchor="middle" font-size="11" fill="#2563eb" font-family="'DM Mono',monospace">400 m³</text>

      <!-- Flecha Aux → Cald -->
      <line x1="170" y1="110" x2="250" y2="110" stroke="{b_aux_c}" stroke-width="2.5" stroke-dasharray="{'none' if b_aux else '6,4'}"/>
      <polygon points="247,104 257,110 247,116" fill="{b_aux_c}"/>
      <rect x="190" y="90" width="50" height="18" rx="9" fill="{b_aux_c}18" stroke="{b_aux_c}" stroke-width="1"/>
      <text x="215" y="103" text-anchor="middle" font-size="9" font-weight="600" fill="{b_aux_c}" font-family="'DM Mono',monospace">B {b_aux_t}</text>

      <!-- Tanque Calderas -->
      <rect x="260" y="60" width="140" height="100" rx="10" fill="#16a34a22" stroke="#16a34a" stroke-width="2"/>
      <text x="330" y="50" text-anchor="middle" font-size="12" font-weight="600" fill="#16a34a" letter-spacing="1">CALDERAS</text>
      <text x="330" y="115" text-anchor="middle" font-size="11" fill="#16a34a" font-family="'DM Mono',monospace">90 m³</text>
      <text x="330" y="132" text-anchor="middle" font-size="9" fill="#57534e">vapor ↓</text>

      <!-- Flecha Cald → Comp -->
      <line x1="400" y1="110" x2="480" y2="110" stroke="{v_cald_c}" stroke-width="2.5" stroke-dasharray="{'none' if v_cald else '6,4'}"/>
      <polygon points="477,104 487,110 477,116" fill="{v_cald_c}"/>
      <rect x="418" y="90" width="55" height="18" rx="9" fill="{v_cald_c}18" stroke="{v_cald_c}" stroke-width="1"/>
      <text x="445" y="103" text-anchor="middle" font-size="9" font-weight="600" fill="{v_cald_c}" font-family="'DM Mono',monospace">V {v_cald_t}</text>

      <!-- Tanque Compresores -->
      <rect x="490" y="60" width="140" height="100" rx="10" fill="#ea580c22" stroke="#ea580c" stroke-width="2"/>
      <text x="560" y="50" text-anchor="middle" font-size="12" font-weight="600" fill="#ea580c" letter-spacing="1">COMPRESORES</text>
      <text x="560" y="115" text-anchor="middle" font-size="11" fill="#ea580c" font-family="'DM Mono',monospace">120 m³</text>

      <!-- Flecha Comp → Prin -->
      <line x1="630" y1="110" x2="710" y2="110" stroke="{b_comp_c}" stroke-width="2.5" stroke-dasharray="{'none' if b_comp else '6,4'}"/>
      <polygon points="707,104 717,110 707,116" fill="{b_comp_c}"/>
      <rect x="648" y="90" width="50" height="18" rx="9" fill="{b_comp_c}18" stroke="{b_comp_c}" stroke-width="1"/>
      <text x="673" y="103" text-anchor="middle" font-size="9" font-weight="600" fill="{b_comp_c}" font-family="'DM Mono',monospace">B {b_comp_t}</text>

      <!-- Tanque Principal -->
      <rect x="720" y="40" width="80" height="140" rx="10" fill="#7c3aed22" stroke="{emerg_c}" stroke-width="2"/>
      <text x="760" y="32" text-anchor="middle" font-size="12" font-weight="600" fill="#7c3aed" letter-spacing="1">PRINCIPAL</text>
      <text x="760" y="115" text-anchor="middle" font-size="11" fill="#7c3aed" font-family="'DM Mono',monospace">500 m³</text>
      <rect x="724" y="152" width="72" height="16" rx="8" fill="{emerg_c}18" stroke="{emerg_c}" stroke-width="1"/>
      <text x="760" y="163" text-anchor="middle" font-size="8" font-weight="600" fill="{emerg_c}" font-family="'DM Mono',monospace">{emerg_t}</text>

      <!-- Entradas externas -->
      <!-- Acueducto → Cald -->
      <line x1="330" y1="200" x2="330" y2="165" stroke="#0891b2" stroke-width="1.5"/>
      <polygon points="324,168 330,158 336,168" fill="#0891b2"/>
      <text x="330" y="215" text-anchor="middle" font-size="9" fill="#0891b2" font-family="'DM Mono',monospace">Acueducto</text>

      <!-- Acueducto → Comp -->
      <line x1="560" y1="200" x2="560" y2="165" stroke="#0891b2" stroke-width="1.5"/>
      <polygon points="554,168 560,158 566,168" fill="#0891b2"/>
      <text x="560" y="215" text-anchor="middle" font-size="9" fill="#0891b2" font-family="'DM Mono',monospace">Acueducto</text>

      <!-- PTAR/PTAP → Prin -->
      <line x1="760" y1="225" x2="760" y2="185" stroke="#0891b2" stroke-width="1.5"/>
      <polygon points="754,188 760,178 766,188" fill="#0891b2"/>
      <text x="760" y="240" text-anchor="middle" font-size="9" fill="#0891b2" font-family="'DM Mono',monospace">PTAR + PTAP</text>

      <!-- Consumo áreas -->
      <line x1="760" y1="265" x2="760" y2="290" stroke="#ea580c" stroke-width="1.5"/>
      <polygon points="754,287 760,297 766,287" fill="#ea580c"/>
      <text x="760" y="310" text-anchor="middle" font-size="9" fill="#ea580c" font-family="'DM Mono',monospace">Áreas (Lav+Tint)</text>

      <!-- Carrotanques -->
      <line x1="100" y1="200" x2="100" y2="165" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="4,3"/>
      <polygon points="94,168 100,158 106,168" fill="#7c3aed"/>
      <text x="100" y="215" text-anchor="middle" font-size="9" fill="#7c3aed" font-family="'DM Mono',monospace">Carrotanques</text>

      <!-- Leyenda -->
      <rect x="30" y="260" width="280" height="44" rx="8" fill="#fff" stroke="#e2ddd6" stroke-width="1"/>
      <line x1="45" y1="275" x2="70" y2="275" stroke="#16a34a" stroke-width="2"/>
      <text x="75" y="279" font-size="9" fill="#57534e">Activo/Abierto</text>
      <line x1="145" y1="275" x2="170" y2="275" stroke="#a8a29e" stroke-width="2" stroke-dasharray="6,4"/>
      <text x="175" y="279" font-size="9" fill="#57534e">Inactivo/Cerrado</text>
      <text x="45" y="296" font-size="9" fill="#57534e" font-weight="500">B = Bomba &nbsp; V = Válvula</text>
    </svg>"""
    return svg


# ── Gráficos Plotly ───────────────────────────────────────────────────────────

def generar_graficos_plotly(historial, caps):
    """Genera 3 gráficos interactivos con Plotly."""
    horas = [h['hora'] for h in historial if h['hora'] > 0]

    # ── Gráfico 1: Niveles % ──
    fig1 = go.Figure()
    for k, label in LABELS.items():
        vals = [h[f'{k}_pct'] for h in historial if h['hora'] > 0]
        fig1.add_trace(go.Scatter(
            x=horas, y=vals, name=label,
            line=dict(color=COLORES[k], width=2.5),
            mode='lines',
            hovertemplate=f'<b>{label}</b><br>Hora: %{{x}}<br>Nivel: %{{y:.1f}}%<extra></extra>',
        ))

    # Sombrear emergencia
    em_horas = [h for h in historial if h.get('modo_emergencia') and h['hora'] > 0]
    if em_horas:
        for h in em_horas:
            fig1.add_vrect(x0=h['hora']-0.5, x1=h['hora']+0.5,
                           fillcolor="#dc2626", opacity=0.06, line_width=0)

    fig1.add_hline(y=90, line_dash="dash", line_color="#e2ddd6", line_width=1,
                   annotation_text="90% OFF", annotation_position="top left",
                   annotation_font_size=10, annotation_font_color="#a8a29e")
    fig1.add_hline(y=70, line_dash="dot", line_color="#e2ddd6", line_width=1,
                   annotation_text="70% ON", annotation_position="bottom left",
                   annotation_font_size=10, annotation_font_color="#a8a29e")

    fig1.update_layout(
        title=dict(text="Evolución de Niveles", font=dict(size=14, color="#1c1917")),
        yaxis=dict(title="Nivel (%)", range=[0, 105], gridcolor="#f0ede8"),
        xaxis=dict(title="Hora", gridcolor="#f0ede8"),
        plot_bgcolor="#ffffff", paper_bgcolor="#faf9f7",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=60, b=40), height=350,
        hovermode="x unified",
    )

    # ── Gráfico 2: Flujos apilados ──
    fig2 = go.Figure()
    b1 = [h['mov_aux_cald']      for h in historial if h['hora'] > 0]
    b2 = [h['mover_cald_comp']   for h in historial if h['hora'] > 0]
    b3 = [h['mov_comp_prin']     for h in historial if h['hora'] > 0]
    b4 = [h['agua_carrotanques'] for h in historial if h['hora'] > 0]
    b5 = [h['entrada_ptar_ptap'] for h in historial if h['hora'] > 0]

    for vals, name, color in [
        (b1, 'Aux→Cald', '#2563eb'), (b2, 'Cald→Comp', '#16a34a'),
        (b3, 'Comp→Prin', '#ea580c'), (b5, 'PTAR+PTAP', '#0891b2'),
    ]:
        fig2.add_trace(go.Bar(
            x=horas, y=vals, name=name,
            marker_color=color, opacity=0.85,
            hovertemplate=f'<b>{name}</b><br>Hora: %{{x}}<br>%{{y:.1f}} m³/h<extra></extra>',
        ))
    if any(v > 0 for v in b4):
        fig2.add_trace(go.Bar(
            x=horas, y=b4, name='Carrotanques',
            marker_color='#7c3aed', opacity=0.85,
            hovertemplate='<b>Carrotanques</b><br>Hora: %{x}<br>%{y:.1f} m³/h<extra></extra>',
        ))

    fig2.update_layout(
        barmode='stack',
        title=dict(text="Flujos entre Tanques", font=dict(size=14, color="#1c1917")),
        yaxis=dict(title="Caudal (m³/h)", gridcolor="#f0ede8"),
        xaxis=dict(title="Hora", gridcolor="#f0ede8"),
        plot_bgcolor="#ffffff", paper_bgcolor="#faf9f7",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=60, b=40), height=350,
        hovermode="x unified",
    )

    # ── Gráfico 3: Balance hídrico ──
    fig3 = go.Figure()
    entradas = [h['entrada_ptar_ptap']+h['entrada_cald_acu']+h['entrada_comp_acu']+h['agua_carrotanques']
                for h in historial if h['hora'] > 0]
    consumos = [h['consumo_areas']+h['consumo_cald'] for h in historial if h['hora'] > 0]

    fig3.add_trace(go.Bar(
        x=horas, y=entradas, name='Entradas', marker_color='#16a34a', opacity=0.85,
        hovertemplate='<b>Entradas</b><br>Hora: %{x}<br>%{y:.1f} m³/h<extra></extra>',
    ))
    fig3.add_trace(go.Bar(
        x=horas, y=[-c for c in consumos], name='Consumos', marker_color='#ea580c', opacity=0.85,
        hovertemplate='<b>Consumos</b><br>Hora: %{x}<br>%{customdata:.1f} m³/h<extra></extra>',
        customdata=consumos,
    ))

    fig3.update_layout(
        barmode='relative',
        title=dict(text="Balance Hídrico", font=dict(size=14, color="#1c1917")),
        yaxis=dict(title="Caudal (m³/h)", gridcolor="#f0ede8", zeroline=True, zerolinecolor="#d6d3d1"),
        xaxis=dict(title="Hora", gridcolor="#f0ede8"),
        plot_bgcolor="#ffffff", paper_bgcolor="#faf9f7",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=60, b=40), height=350,
        hovermode="x unified",
    )

    return fig1, fig2, fig3


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
    <div style="font-size:18px;font-weight:700;color:#1c1917">Simulador de Tanques Interconectados</div>
    <div style="font-size:12px;color:#a8a29e;font-family:'DM Mono',monospace">
      flujo de agua entre 4 tanques industriales — hora a hora</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Presets
    st.markdown('<div class="section-header">Escenario</div>', unsafe_allow_html=True)
    preset_nombre = st.selectbox(
        "Cargar escenario predefinido",
        list(PRESETS.keys()),
        index=0,
        label_visibility="collapsed",
    )
    preset = PRESETS[preset_nombre]

    if preset_nombre != "Personalizado":
        st.markdown(
            f'<div class="preset-info">📋 Escenario: <b>{preset_nombre}</b></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown('<div class="section-header">Capacidades (m³)</div>', unsafe_allow_html=True)
    cap_aux  = st.number_input("Auxiliar",    min_value=0.1, value=CAP_DEFAULT["aux"],  step=10.0)
    cap_cald = st.number_input("Calderas",    min_value=0.1, value=CAP_DEFAULT["cald"], step=10.0)
    cap_comp = st.number_input("Compresores", min_value=0.1, value=CAP_DEFAULT["comp"], step=10.0)
    cap_prin = st.number_input("Principal",   min_value=0.1, value=CAP_DEFAULT["prin"], step=10.0)
    capacidades = {"aux": cap_aux, "cald": cap_cald, "comp": cap_comp, "prin": cap_prin}

    st.divider()
    st.markdown('<div class="section-header">Niveles iniciales (%)</div>', unsafe_allow_html=True)
    pct_aux  = st.slider("Auxiliar",    0, 100, preset.get("niv_aux", 70),  key="s_aux")
    pct_cald = st.slider("Calderas",    0, 100, preset.get("niv_cald", 70), key="s_cald")
    pct_comp = st.slider("Compresores", 0, 100, preset.get("niv_comp", 70), key="s_comp")
    pct_prin = st.slider("Principal",   0, 100, preset.get("niv_prin", 80), key="s_prin")

# ── CONFIGURACIÓN PRINCIPAL ──────────────────────────────────────────────────
col_config, col_sim = st.columns([3, 1])

with col_config:
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="section-header">Caudales entre tanques</div>', unsafe_allow_html=True)
        q_aux_cald  = st.number_input("Aux → Calderas (m³/h)",    min_value=0.0, max_value=50.0,
                                       value=preset.get("q_aux_cald", 15.0))
        q_cald_comp = st.number_input("Cald → Compresores (m³/h)", min_value=0.0, max_value=50.0,
                                       value=preset.get("q_cald_comp", 10.0))
        q_comp_prin = st.number_input("Comp → Principal (m³/h)",   min_value=0.0, max_value=60.0,
                                       value=preset.get("q_comp_prin", 20.0))

    with c2:
        st.markdown('<div class="section-header">Entradas externas</div>', unsafe_allow_html=True)
        q_ptar = st.number_input("PTAR → Principal (m³/h)", min_value=0.0, max_value=40.0,
                                  value=preset.get("q_ptar", 5.0))
        q_ptap = st.number_input("PTAP → Principal (m³/h)", min_value=0.0, max_value=40.0,
                                  value=preset.get("q_ptap", 5.0))
        ent_cald = st.number_input("Acueducto → Calderas (m³/h)", min_value=0.0, max_value=50.0,
                                    value=preset.get("entrada_acueducto_cald", 10.0))
        ent_comp = st.number_input("Acueducto → Compresores (m³/h)", min_value=0.0, max_value=50.0,
                                    value=preset.get("entrada_acueducto_comp", 25.0))

    with c3:
        st.markdown('<div class="section-header">Consumos</div>', unsafe_allow_html=True)
        consumo_calderas = st.number_input("Consumo Calderas (m³/h)", min_value=0.0, max_value=50.0,
                                            value=preset.get("consumo_calderas", 8.0))
        q_lav   = st.number_input("Lavandería (m³/h)", min_value=0.0, max_value=80.0,
                                   value=preset.get("q_lav", 8.0))
        q_tinto = st.number_input("Tintorería (m³/h)", min_value=0.0, max_value=80.0,
                                   value=preset.get("q_tinto", 6.0))

with col_sim:
    st.markdown('<div class="section-header">Simulación</div>', unsafe_allow_html=True)
    horas_sim = st.slider("Horas", 1, 72, preset.get("horas", 24))

    usar_carrotanques = st.checkbox("Carrotanques")
    if usar_carrotanques:
        carro_aux  = st.number_input("Vol. Auxiliar (m³)",    min_value=0.0, max_value=500.0, value=0.0)
        carro_comp = st.number_input("Vol. Compresores (m³)", min_value=0.0, max_value=500.0, value=0.0)
    else:
        carro_aux = carro_comp = 0.0

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    ejecutar = st.button("▶ Ejecutar Simulación", type="primary", use_container_width=True)


# ── CONFIG DICT ──────────────────────────────────────────────────────────────
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


# ── RESULTADOS ────────────────────────────────────────────────────────────────
if ejecutar:
    with st.spinner("Simulando..."):
        resultados = simular(
            horas_sim, config,
            capacidades=capacidades,
            usar_carrotanques=usar_carrotanques,
            carrotanque_aux=carro_aux,
            carrotanque_comp=carro_comp,
        )

    # ── ALERTA EMERGENCIA (con rangos legibles) ──
    horas_em = [r['hora'] for r in resultados if r.get('modo_emergencia')]
    if horas_em:
        rangos = formato_rangos_emergencia(horas_em)
        st.markdown(
            f'<div class="alert-box">⚠️ Modo emergencia activado — '
            f'Horas: {rangos} — Consumos reducidos al 50%</div>',
            unsafe_allow_html=True)

    # ── SLIDER EXPLORADOR (mueve tanques + stats + diagrama) ──
    st.markdown('<div class="section-header" style="margin-top:8px">Explorador hora a hora</div>',
                unsafe_allow_html=True)
    hora_sel = st.slider("Hora", 0, len(resultados)-1, len(resultados)-1, key="hora_explorador")
    rec = resultados[hora_sel]

    # ── TANQUES DINÁMICOS (actualizan con slider) ──
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pct = round(rec['aux_pct'])
        lbl, cls = pump_info(rec['estado_bomba_aux'], "Bomba ON", "Bomba OFF")
        st.markdown(tank_html("AUXILIAR", "#2563eb", pct,
            rec['aux_m3'], cap_aux, lbl, cls), unsafe_allow_html=True)

    with col2:
        pct = round(rec['cald_pct'])
        lbl, cls = pump_info(rec['estado_valvula_cald'], "Válvula abierta", "Válvula cerrada")
        st.markdown(tank_html("CALDERAS", "#16a34a", pct,
            rec['cald_m3'], cap_cald, lbl, cls), unsafe_allow_html=True)

    with col3:
        pct = round(rec['comp_pct'])
        lbl, cls = pump_info(rec['estado_bomba_comp'], "Bomba ON", "Bomba OFF")
        st.markdown(tank_html("COMPRESORES", "#ea580c", pct,
            rec['comp_m3'], cap_comp, lbl, cls), unsafe_allow_html=True)

    with col4:
        pct = round(rec['prin_pct'])
        alarm = rec.get('modo_emergencia', False)
        lbl = "⚠ Emergencia" if alarm else "Normal"
        cls = "badge-alarm" if alarm else "badge-on"
        st.markdown(tank_html("PRINCIPAL", "#7c3aed", pct,
            rec['prin_m3'], cap_prin, lbl, cls), unsafe_allow_html=True)

    # ── DIAGRAMA DEL SISTEMA ──
    with st.expander("📐 Diagrama del sistema", expanded=False):
        st.markdown(diagrama_sistema_svg(rec), unsafe_allow_html=True)

    # ── STATS ──
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    with s1: st.markdown(stat_html("Consumo Áreas", f"{rec['consumo_areas']:.1f} m³", "#ea580c"), unsafe_allow_html=True)
    with s2: st.markdown(stat_html("Flujo Aux→Cald", f"{rec['mov_aux_cald']:.1f} m³", "#2563eb"), unsafe_allow_html=True)
    with s3: st.markdown(stat_html("Flujo Cald→Comp", f"{rec['mover_cald_comp']:.1f} m³", "#16a34a"), unsafe_allow_html=True)
    with s4: st.markdown(stat_html("Flujo Comp→Prin", f"{rec['mov_comp_prin']:.1f} m³", "#7c3aed"), unsafe_allow_html=True)
    with s5: st.markdown(stat_html("PTAR + PTAP", f"{rec['entrada_ptar_ptap']:.1f} m³", "#0891b2"), unsafe_allow_html=True)
    with s6:
        emerg = rec.get('modo_emergencia', False)
        st.markdown(stat_html("Emergencia", "Sí ⚠" if emerg else "No",
                               "#dc2626" if emerg else "#16a34a"), unsafe_allow_html=True)

    # ── GRÁFICOS PLOTLY ──
    st.markdown('<div class="section-header" style="margin-top:16px">Gráficas interactivas</div>',
                unsafe_allow_html=True)
    fig1, fig2, fig3 = generar_graficos_plotly(resultados, capacidades)
    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)

    # ── TABLA + DESCARGA ──
    with st.expander("📋 Ver tabla completa hora a hora"):
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True)

    csv = pd.DataFrame(resultados).to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", csv, "simulacion.csv", "text/csv")
