# 🚰 Simulador de Sistema de Tanques Interconectados

Simulador de flujo de agua entre tanques interconectados, desarrollado en Python con interfaz web Streamlit. Modela la dinámica hora a hora de 4 tanques industriales (Auxiliar, Calderas, Compresores y Principal) con control automático de bombas y válvulas.

## Arquitectura del proyecto

```
simulador-de-tanques/
├── app.py            # Interfaz Streamlit (UI únicamente)
├── simulator.py      # Lógica de simulación (sin dependencia de Streamlit)
├── requirements.txt
├── tests/
│   └── test_simulator.py
└── README.md
```

## Instalación

```bash
git clone https://github.com/dnlrobayo-droid/simulador-de-tanques.git
cd simulador-de-tanques
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```

## Cómo funciona

El simulador calcula el estado de cada tanque hora a hora:

1. **Control automático** — las bombas y válvulas se activan/desactivan según umbrales de nivel (70 % ON / 90 % OFF).
2. **Cortes de seguridad** — si un tanque baja de su nivel crítico, se fuerza el corte de la bomba correspondiente.
3. **Modo emergencia** — si el tanque Principal baja del 30 %, los consumos de lavandería y tintorería se reducen al 50 % y se emite una alerta visual.
4. **Carrotanques** — volumen extra distribuido uniformemente a lo largo de la simulación.

## Diagrama de tanques

```
[ACUEDUCTO]──────┬──────────────────────────────────[ACUEDUCTO]
                 ▼                                          ▼
         [TANQUE AUXILIAR]               [TANQUE COMPRESORES]◄──[CALD]
                 │ bomba                         │ bomba
                 ▼                               ▼
         [TANQUE CALDERAS]               [TANQUE PRINCIPAL]
         (+ acueducto, - vapor)          (+ PTAR/PTAP, - áreas)
```

## Ejecutar tests

```bash
python -m pytest tests/ -v
```

## Parámetros configurables (UI)

| Parámetro | Descripción |
|-----------|-------------|
| Capacidades (m³) | Volumen máximo de cada tanque |
| Niveles iniciales (%) | Estado de arranque |
| Caudales (m³/h) | Flujo entre tanques |
| Entradas acueducto | Suministro externo a Calderas y Compresores |
| PTAR / PTAP | Agua tratada que entra al Principal |
| Consumos | Lavandería, tintorería y calderas |
| Carrotanques | Volumen extra de emergencia |
| Horas | Duración de la simulación (1–72 h) |
