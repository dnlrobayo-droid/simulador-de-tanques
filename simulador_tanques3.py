# app.py
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Simulador de Tanques", layout="wide")
st.title("🚰 Simulador de Sistema de Tanques Interconectados")

# Capacidades de los tanques (m³)
cap_aux = 400.0
cap_cald = 90.0
cap_comp = 120.0
cap_prin = 500.0

# --- FUNCIONES ---
def simular(horas, config, usar_carrotanques=False, carrotanque_aux=0.0, carrotanque_comp=0.0):
    """
    Simula el sistema de tanques durante un número determinado de horas
    Devuelve un historial con todos los datos por hora
    """
    # Extraer capacidades de los tanques
    global cap_aux, cap_cald, cap_comp, cap_prin
    
    # Extraer configuración inicial
    niv_aux = config['niv_aux']
    niv_cald = config['niv_cald']
    niv_comp = config['niv_comp']
    niv_prin = config['niv_prin']
    q_aux_cald = config['q_aux_cald']
    q_cald_comp = config['q_cald_comp']
    q_comp_prin = config['q_comp_prin']
    q_ptar = config['q_ptar']
    q_ptap = config['q_ptap']
    q_lav = config['q_lav']
    q_tinto = config['q_tinto']
    entrada_acueducto_cald = config['entrada_acueducto_cald']
    entrada_acueducto_comp = config['entrada_acueducto_comp']
    consumo_calderas = config['consumo_calderas']
    
    # Preparar suministro de carrotanques
    suministro_aux_por_hora = carrotanque_aux/horas if usar_carrotanques else 0
    suministro_comp_por_hora = carrotanque_comp/horas if usar_carrotanques else 0
    
    # Estados iniciales de bombas/válvulas
    bomba_aux_cald_on = q_aux_cald > 0
    valvula_cald_comp_abierta = q_cald_comp > 0
    bomba_comp_prin_on = q_comp_prin > 0
    
    # Historial de datos
    historial = []
    historial.append({
        "hora": 0,
        "aux_m3": niv_aux, "cald_m3": niv_cald, "comp_m3": niv_comp, "prin_m3": niv_prin,
        "aux_pct": (niv_aux/cap_aux)*100, "cald_pct": (niv_cald/cap_cald)*100,
        "comp_pct": (niv_comp/cap_comp)*100, "prin_pct": (niv_prin/cap_prin)*100,
        "mov_aux_cald": 0, "entrada_cald_acu": 0, "consumo_cald": 0,
        "mover_cald_comp": 0, "entrada_comp_acu": 0, "mov_comp_prin": 0,
        "entrada_ptar_ptap": 0, "consumo_areas": 0, "agua_carrotanques": 0,
        "estado_aux": bomba_aux_cald_on,
        "estado_cald": valvula_cald_comp_abierta,
        "estado_comp": bomba_comp_prin_on
    })

    for hora_actual in range(1, horas + 1):
        # --- Control automático por niveles ---
        # Tanque Principal (Comp→Prin)
        if niv_prin >= 0.9 * cap_prin:
            bomba_comp_prin_on = False
        elif niv_prin <= 0.7 * cap_prin:
            if niv_comp > 0.1 * cap_comp:
                bomba_comp_prin_on = True if q_comp_prin > 0 else False
                
        # Tanque Compresores (Cald→Comp)
        if niv_comp >= 0.9 * cap_comp:
            valvula_cald_comp_abierta = False
        elif niv_comp <= 0.7 * cap_comp:
            valvula_cald_comp_abierta = True if q_cald_comp > 0 else False
            
        # Tanque Calderas (Aux→Cald)
        if niv_cald >= 0.9 * cap_cald:
            bomba_aux_cald_on = False
        elif niv_cald <= 0.7 * cap_cald:
            bomba_aux_cald_on = True if q_aux_cald > 0 else False
            
        # --- Seguridad por niveles mínimos ---
        if niv_aux <= 0.2 * cap_aux:
            bomba_aux_cald_on = False
        if niv_cald <= 0.3 * cap_cald:
            valvula_cald_comp_abierta = False
        if niv_comp <= 0.1 * cap_comp:
            bomba_comp_prin_on = False
            
        # --- Lógica de emergencia para el tanque principal ---
        if niv_prin <= 0.3 * cap_prin:
            consumo_areas_original = q_lav + q_tinto
            q_lav_temp = q_lav * 0.5 if consumo_areas_original > 0 else 0
            q_tinto_temp = q_tinto * 0.5 if consumo_areas_original > 0 else 0
        else:
            q_lav_temp = q_lav
            q_tinto_temp = q_tinto
            
        # --- Cálculo de flujos ---
        # Aux → Cald
        mov_aux_cald = min(q_aux_cald, niv_aux, cap_cald - niv_cald) if bomba_aux_cald_on else 0
        niv_aux -= mov_aux_cald
        niv_cald += mov_aux_cald
        
        # Entrada acueducto a Calderas
        entrada_cald = min(entrada_acueducto_cald, cap_cald - niv_cald)
        niv_cald += entrada_cald
        
        # Consumo Calderas
        consumo_cald = min(consumo_calderas, niv_cald)
        niv_cald -= consumo_cald
        
        # Cald → Comp
        mover_cald_comp = min(q_cald_comp, niv_cald, cap_comp - niv_comp) if valvula_cald_comp_abierta else 0
        niv_cald -= mover_cald_comp
        niv_comp += mover_cald_comp
        
        # Entrada acueducto a Compresores
        entrada_comp = min(entrada_acueducto_comp, cap_comp - niv_comp)
        niv_comp += entrada_comp
        
        # Comp → Prin
        mover_comp_prin = min(q_comp_prin, niv_comp, cap_prin - niv_prin) if bomba_comp_prin_on else 0
        niv_comp -= mover_comp_prin
        niv_prin += mover_comp_prin
        
        # Entrada PTAR/PTAP
        entrada_ptar_ptap = min(q_ptar + q_ptap, cap_prin - niv_prin)
        niv_prin += entrada_ptar_ptap
        
        # Consumo áreas
        consumo_areas = min(q_lav_temp + q_tinto_temp, niv_prin)
        niv_prin -= consumo_areas
        
        # Suministro carrotanques
        agua_carro-tanques = 0
        if usar_carro-tanques:
            sum_aux = min(suministro_aux_por_hora, cap_aux - niv_aux)
            niv_aux += sum_aux
            sum_comp = min(suministro_comp_por_hora, cap_comp - niv_comp)
            niv_comp += sum_comp
            agua_carrotanques = sum_aux + sum_comp
            
        # Asegurar no negativos
        niv_aux = max(0, niv_aux)
        niv_cald = max(0, niv_cald)
        niv_comp = max(0, niv_comp)
        niv_prin = max(0, niv_prin)
        
        # Calcular porcentajes
        aux_pct = (niv_aux / cap_aux) * 100 if cap_aux > 0 else 0
        cald_pct = (niv_cald / cap_cald) * 100 if cap_cald > 0 else 0
        comp_pct = (niv_comp / cap_comp) * 100 if cap_comp > 0 else 0
        prin_pct = (niv_prin / cap_prin) * 100 if cap_prin > 0 else 0
        
        # Registrar hora
        historial.append({
            "hora": hora_actual,
            "aux_m3": round(niv_aux, 2), "cald_m3": round(niv_cald, 2),
            "comp_m3": round(niv_comp, 2), "prin_m3": round(niv_prin, 2),
            "aux_pct": round(aux_pct, 1), "cald_pct": round(cald_pct, 1),
            "comp_pct": round(comp_pct, 1), "prin_pct": round(prin_pct, 1),
            "mov_aux_cald": round(mov_aux_cald, 2), "entrada_cald_acu": round(entrada_cald, 2),
            "consumo_cald": round(consumo_cald, 2), "mover_cald_comp": round(mover_cald_comp, 2),
            "entrada_comp_acu": round(entrada_comp, 2), "mov_comp_prin": round(mover_comp_prin, 2),
            "entrada_ptar_ptap": round(entrada_ptar_ptap, 2), "consumo_areas": round(consumo_areas, 2),
            "agua_carrotanques": round(agua_carrotanques, 2),
            "estado_aux": bomba_aux_cald_on,
            "estado_cald": valvula_cald_comp_abierta,
            "estado_comp": bomba_comp_prin_on
        })

    return historial

def generar_graficos_streamlit(historial, titulo_extra=""):
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
    
    # Gráfico 1: Evolución de niveles
    horas = [h['hora'] for h in historial if h['hora'] > 0]
    ax1.plot(horas, [h['aux_m3'] for h in historial if h['hora'] > 0], 'b-', label='Auxiliar')
    ax1.plot(horas, [h['cald_m3'] for h in historial if h['hora'] > 0], 'g-', label='Calderas')
    ax1.plot(horas, [h['comp_m3'] for h in historial if h['hora'] > 0], 'r-', label='Compresores')
    ax1.plot(horas, [h['prin_m3'] for h in historial if h['hora'] > 0], 'm-', label='Principal')
    
    # Líneas de referencia
    ax1.axhline(y=0.9*cap_aux, color='b', linestyle='--', alpha=0.3)
    ax1.axhline(y=0.7*cap_aux, color='b', linestyle=':', alpha=0.3)
    ax1.axhline(y=0.9*cap_cald, color='g', linestyle='--', alpha=0.3)
    ax1.axhline(y=0.7*cap_cald, color='g', linestyle=':', alpha=0.3)
    ax1.axhline(y=0.9*cap_comp, color='r', linestyle='--', alpha=0.3)
    ax1.axhline(y=0.7*cap_comp, color='r', linestyle=':', alpha=0.3)
    ax1.axhline(y=0.9*cap_prin, color='m', linestyle='--', alpha=0.3)
    ax1.axhline(y=0.7*cap_prin, color='m', linestyle=':', alpha=0.3)
    
    ax1.set_title(f'Evolución de Niveles {titulo_extra}')
    ax1.set_ylabel('Volumen (m³)')
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Gráfico 2: Flujos entre tanques - COLOR CAMBIADO A VERDE ESMERALDA
    ax2.bar(horas, [h['mov_aux_cald'] for h in historial if h['hora'] > 0], label='Aux→Cald', color='blue', alpha=0.7)
    ax2.bar(horas, [h['mover_cald_comp'] for h in historial if h['hora'] > 0], label='Cald→Comp', color='green', alpha=0.7,
           bottom=[h['mov_aux_cald'] for h in historial if h['hora'] > 0])
    ax2.bar(horas, [h['mov_comp_prin'] for h in historial if h['hora'] > 0], label='Comp→Prin', color='red', alpha=0.7,
           bottom=[h['mov_aux_cald']+h['mover_cald_comp'] for h in historial if h['hora'] > 0])
    if any(h['agua_carrotanques'] > 0 for h in historial):
        ax2.bar(horas, [h['agua_carrotanques'] for h in historial if h['hora'] > 0], 
               label='Carrotanques', color='seagreen', alpha=0.7,  # ✅ VERDE ESMERALDA
               bottom=[h['mov_aux_cald']+h['mover_cald_comp']+h['mov_comp_prin'] for h in historial if h['hora'] > 0])
    ax2.set_title(f'Flujos entre Tanques {titulo_extra}')
    ax2.set_ylabel('Caudal (m³/h)')
    ax2.legend()
    ax2.grid(True, axis='y', linestyle='--', alpha=0.6)
    
    # Gráfico 3: Balance hídrico
    entradas = [h['entrada_ptar_ptap']+h['entrada_cald_acu']+h['entrada_comp_acu']+h['agua_carrotanques'] for h in historial if h['hora'] > 0]
    consumos = [h['consumo_areas']+h['consumo_cald'] for h in historial if h['hora'] > 0]
    ax3.bar(horas, entradas, width=0.4, label='Entradas', color='#2ecc71')
    ax3.bar([h+0.4 for h in horas], consumos, width=0.4, label='Consumos', color='#e74c3c')
    ax3.set_title(f'Balance Hídrico {titulo_extra}')
    ax3.set_xlabel('Tiempo (horas)')
    ax3.set_ylabel('Caudal (m³/h)')
    ax3.legend()
    ax3.grid(True, axis='y', linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    st.pyplot(fig)

# --- INTERFAZ STREAMLIT ---
with st.sidebar:
    st.header("⚙️ Configuración Inicial")
    
    # Capacidades
    st.subheader("Capacidades de Tanques (m³)")
    cap_aux = st.number_input("Auxiliar", value=400.0)
    cap_cald = st.number_input("Calderas", value=90.0)
    cap_comp = st.number_input("Compresores", value=120.0)
    cap_prin = st.number_input("Principal", value=500.0)
    
    # Niveles iniciales
    st.subheader("Niveles Iniciales (%)")
    pct_aux = st.slider("Auxiliar", 0, 100, 70)
    pct_cald = st.slider("Calderas", 0, 100, 70)
    pct_comp = st.slider("Compresores", 0, 100, 70)
    pct_prin = st.slider("Principal", 0, 100, 80)
    
    # Convertir a m³
    niv_aux = pct_aux/100 * cap_aux
    niv_cald = pct_cald/100 * cap_cald
    niv_comp = pct_comp/100 * cap_comp
    niv_prin = pct_prin/100 * cap_prin

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2, tab3 = st.tabs(["📊 Flujos", "⚡ Bombas", "🚚 Carro-tanques"])

with tab1:
    st.subheader("Configuración de Flujos")
    col1, col2 = st.columns(2)
    
    with col1:
        q_aux_cald = st.number_input("Caudal Aux→Cald (m³/h)", value=15.0)
        q_cald_comp = st.number_input("Caudal Cald→Comp (m³/h)", value=10.0)
        q_comp_prin = st.number_input("Caudal Comp→Prin (m³/h)", value=20.0)
    
    with col2:
        q_ptar = st.number_input("Caudal PTAR (m³/h)", value=5.0)
        q_ptap = st.number_input("Caudal PTAP (m³/h)", value=5.0)
        consumo_calderas = st.number_input("Consumo Calderas (m³/h)", value=8.0)

with tab2:
    st.subheader("Consumos y Entradas")
    col1, col2 = st.columns(2)
    
    with col1:
        q_lav = st.number_input("Consumo Lavandería (m³/h)", value=8.0)
        q_tinto = st.number_input("Consumo Tintorería (m³/h)", value=6.0)
    
    with col2:
        entrada_acueducto_cald = st.number_input("Acueducto a Calderas (m³/h)", value=10.0)
        entrada_acueducto_comp = st.number_input("Acueducto a Compresores (m³/h)", value=25.0)

with tab3:
    st.subheader("Configuración de Carrotanques")
    usar_carrotanques = st.checkbox("Usar carrotanques")
    
    if usar_carrotanques:
        carrotanque_aux = st.number_input("Agua para Auxiliar (m³)", value=0.0)
        carrotanque_comp = st.number_input("Agua para Compresores (m³)", value=0.0)
    else:
        carrotanque_aux = carrotanque_comp = 0.0

# Configuración final
horas_simulacion = st.slider("Horas a simular", 1, 72, 24)

config = {
    'niv_aux': niv_aux, 'niv_cald': niv_cald, 'niv_comp': niv_comp, 'niv_prin': niv_prin,
    'q_aux_cald': q_aux_cald, 'q_cald_comp': q_cald_comp, 'q_comp_prin': q_comp_prin,
    'q_ptar': q_ptar, 'q_ptap': q_ptap, 'q_lav': q_lav, 'q_tinto': q_tinto,
    'entrada_acueducto_cald': entrada_acueducto_cald, 'entrada_acueducto_comp': entrada_acueducto_comp,
    'consumo_calderas': consumo_calderas
}

# --- BOTÓN DE SIMULACIÓN ---
if st.button("🎯 Ejecutar Simulación", type="primary"):
    with st.spinner("Simulando..."):
        resultados = simular(horas_simulacion, config, usar_carrotanques, carrotanque_aux, carrotanque_comp)
    
    # Mostrar resultados
    st.success("Simulación completada!")
    
    # Gráficos
    generar_graficos_streamlit(resultados)
    
    # Tabla de resultados con m³ y %
    st.subheader("📋 Resultados Detallados")
    df = pd.DataFrame(resultados)
    
    # Crear columnas combinadas m³ y %
    df_display = df.copy()
    df_display['Auxiliar'] = df_display['aux_m3'].astype(str) + ' m³ (' + df_display['aux_pct'].astype(str) + '%)'
    df_display['Calderas'] = df_display['cald_m3'].astype(str) + ' m³ (' + df_display['cald_pct'].astype(str) + '%)'
    df_display['Compresores'] = df_display['comp_m3'].astype(str) + ' m³ (' + df_display['comp_pct'].astype(str) + '%)'
    df_display['Principal'] = df_display['prin_m3'].astype(str) + ' m³ (' + df_display['prin_pct'].astype(str) + '%)'
    
    # Seleccionar columnas para mostrar
    columns_to_display = ['hora', 'Auxiliar', 'Calderas', 'Compresores', 'Principal']
    st.dataframe(df_display[columns_to_display])
    
    # Métricas finales con m³ y %
    ultimo = resultados[-1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Auxiliar Final", f"{ultimo['aux_m3']:.1f} m³", f"{ultimo['aux_pct']:.1f}%")
    with col2:
        st.metric("Calderas Final", f"{ultimo['cald_m3']:.1f} m³", f"{ultimo['cald_pct']:.1f}%")
    with col3:
        st.metric("Compresores Final", f"{ultimo['comp_m3']:.1f} m³", f"{ultimo['comp_pct']:.1f}%")
    with col4:
        st.metric("Principal Final", f"{ultimo['prin_m3']:.1f} m³", f"{ultimo['prin_pct']:.1f}%")


