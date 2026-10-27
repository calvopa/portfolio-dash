import os

DASH_USER = os.getenv("DASH_USER", "admin")
DASH_PASSWORD = os.getenv("DASH_PASSWORD", "")

DATA_DIR = os.getenv("DATA_DIR", "/data")

# Precios en vivo del mercado argentino (API pública, sin claves)
DATA912_URL = os.getenv("DATA912_URL", "https://data912.com")
# Dólar MEP hoy e histórico
DOLARAPI_URL = os.getenv("DOLARAPI_URL", "https://dolarapi.com/v1/dolares/bolsa")
MEP_HIST_URL = os.getenv("MEP_HIST_URL", "https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa")

# Contra qué se compara la cartera ("¿te conviene?"): un ETF de EE.UU. con histórico en data912
BENCHMARK = os.getenv("BENCHMARK", "SPY")

# Cartera objetivo por tipo de Balanz (% del total en US$), acordada con Pablo el 26/10/2026.
# Un tipo se marca "corrido" si se aleja más de BANDA_REBALANCEO puntos.
OBJETIVOS = {"Cedears": 50, "Corporativos": 25, "Bonos": 7, "Liquidez": 15, "Acciones": 3}
# Tipos que se suman en un mismo objetivo: el FCI dólar y el efectivo cumplen la misma función
GRUPOS = {"Fondos": "Liquidez", "Efectivo": "Liquidez"}
BANDA_REBALANCEO = 5
# Reglas dentro de la cartera (en % del total)
INDICES = {"SPY", "QQQ", "VOO", "IVV", "DIA", "IWM", "EEM", "EWZ", "VEA", "VTI", "ACWI"}
SEMIS = {"AMD", "NVDA", "TSM", "INTC", "AVGO", "QCOM", "MU", "ASML", "TXN", "ARM", "AMAT", "SMH"}
MIN_INDICE_PCT = 25
MAX_ACCION_PCT = 10
MAX_SEMIS_PCT = 15

PRICE_CACHE_SECONDS = int(os.getenv("PRICE_CACHE_SECONDS", "300"))
SNAPSHOT_MINUTES = int(os.getenv("SNAPSHOT_MINUTES", "15"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "2000000"))
