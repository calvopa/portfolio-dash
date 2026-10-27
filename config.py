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

PRICE_CACHE_SECONDS = int(os.getenv("PRICE_CACHE_SECONDS", "300"))
SNAPSHOT_MINUTES = int(os.getenv("SNAPSHOT_MINUTES", "15"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "2000000"))
