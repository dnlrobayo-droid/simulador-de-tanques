# 🚰 Simulador de Sistema de Tanques Interconectados

Simulador de flujo de agua entre tanques interconectados, desarrollado en Python con interfaz web Streamlit. Modela la dinámica hora a hora de 4 tanques industriales (Auxiliar, Calderas, Compresores y Principal) con control automático de bombas y válvulas.

## Arquitectura del proyecto

```
simulador-de-tanques/
├── app.py               # Interfaz Streamlit (UI únicamente)
├── simulator.py          # Lógica de simulación (sin dependencia de Streamlit)
├── config.py             # Configuración centralizada (umbrales, capacidades, presets)
├── requirements.txt      # Dependencias de producción
├── requirements-dev.txt  # Dependencias de desarrollo (incluye pytest)
├── tests/
│   └── test_simulator.py # 29 tests unitarios
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

El simulador calcula el estado de cada tanque hora a hora en orden secuencial:

1. **Control automático** — las bombas y válvulas se activan/desactivan según umbrales de nivel (70% ON / 90% OFF).
2. **Cortes de seguridad** — si un tanque baja de su nivel crítico, se fuerza el corte de la bomba correspondiente.
3. **Flujos con reservas protegidas** — cada flujo entre tanques respeta la reserva mínima del tanque origen.
4. **Modo emergencia** — si el tanque Principal baja del 30%, los consumos de lavandería y tintorería se reducen al 50%.
5. **Carrotanques** — volumen extra distribuido uniformemente a lo largo de la simulación.

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

## Escenarios predefinidos

El simulador incluye escenarios de un clic para explorar situaciones típicas:

| Escenario | Descripción |
|-----------|-------------|
| Operación normal | Parámetros estándar de planta |
| Sequía (sin acueducto) | Sin entradas de acueducto ni PTAR/PTAP |
| Emergencia (tanques bajos) | Todos los tanques por debajo de reservas |
| Mantenimiento calderas | Calderas aisladas, sin consumo de vapor |
| Alta demanda industrial | Consumos máximos de lavandería y tintorería |

## Configuración centralizada

Todos los umbrales, capacidades y colores están en `config.py`. Para modificar umbrales de control:

```python
# config.py
UMBRALES = {
    "bomba_on":        0.70,   # Bomba se enciende cuando destino ≤ 70%
    "bomba_off":       0.90,   # Bomba se apaga cuando destino ≥ 90%
    "reserva_aux":     0.20,   # Reserva mínima Auxiliar (20%)
    "reserva_cald":    0.30,   # Reserva mínima Calderas (30%)
    "reserva_comp":    0.10,   # Reserva mínima Compresores (10%)
    "emergencia_prin": 0.30,   # Umbral de emergencia Principal (30%)
}
```

## Ejecutar tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Parámetros configurables (UI)

| Parámetro | Descripción |
|-----------|-------------|
| Capacidades (m³) | Volumen máximo de cada tanque |
| Niveles iniciales (%) | Estado de arranque |
| Caudales (m³/h) | Flujo entre tanques (0–60) |
| Entradas acueducto | Suministro externo a Calderas y Compresores |
| PTAR / PTAP | Agua tratada que entra al Principal (0–40) |
| Consumos | Lavandería y tintorería (hasta 80 m³/h) y calderas |
| Carrotanques | Volumen extra de emergencia |
| Horas | Duración de la simulación (1–72 h) |
