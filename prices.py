"""Precios en vivo (data912) y dólar MEP (dolarapi hoy, argentinadatos histórico), con caché."""
import bisect
import logging
import time
from datetime import date

import requests

import config

log = logging.getLogger("portfolio")

# Tipo de instrumento de Balanz -> panel de data912
PANELES = {
    "Cedears": "live/arg_cedears",
    "Acciones": "live/arg_stocks",
    "Bonos": "live/arg_bonds",
    "Corporativos": "live/arg_corp",
    "Letras": "live/arg_notes",
}

_cache: dict[str, tuple[float, object]] = {}


def _get(url: str, ttl: int):
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        _cache[url] = (time.time(), data)
        return data
    except (requests.RequestException, ValueError) as e:
        log.warning("No pude leer %s: %s", url, type(e).__name__)
        return hit[1] if hit else None  # mejor un precio de hace un rato que ninguno


def panel(tipo: str) -> dict[str, dict]:
    ep = PANELES.get(tipo)
    if not ep:
        return {}
    data = _get(f"{config.DATA912_URL}/{ep}", config.PRICE_CACHE_SECONDS) or []
    return {x["symbol"]: x for x in data if x.get("symbol")}


def precio_vivo(tipo: str, ticker: str, precio_import: float) -> tuple[float | None, float | None]:
    """(precio por la misma unidad que usa Balanz, variación % del día) o (None, None).
    El mercado cotiza bonos/ONs por 100 nominales y Balanz por 1: se elige la escala (1 o 100)
    que deja el precio más cerca del importado, y se descarta si difiere más de 50%."""
    x = panel(tipo).get(ticker)
    if not x:
        return None, None
    c = x.get("c") or 0
    if not c and x.get("px_bid") and x.get("px_ask"):
        c = (x["px_bid"] + x["px_ask"]) / 2
    if not c:
        return None, None
    if not precio_import:
        return c, x.get("pct_change")
    escala = min((1, 100), key=lambda s: abs(c / s - precio_import))
    p = c / escala
    if abs(p / precio_import - 1) > 0.5:
        log.warning("Precio de %s fuera de rango (%s vs %s importado), se ignora", ticker, p, precio_import)
        return None, None
    return p, x.get("pct_change")


def mep_hoy() -> float | None:
    d = _get(config.DOLARAPI_URL, config.PRICE_CACHE_SECONDS)
    if d and d.get("compra") and d.get("venta"):
        return (d["compra"] + d["venta"]) / 2
    bonos = panel("Bonos")  # respaldo: MEP implícito AL30 / AL30D
    if bonos.get("AL30", {}).get("c") and bonos.get("AL30D", {}).get("c"):
        return bonos["AL30"]["c"] / bonos["AL30D"]["c"]
    return None


def _mep_serie() -> tuple[list[str], list[float]]:
    data = _get(config.MEP_HIST_URL, 12 * 3600) or []
    serie = sorted((x["fecha"], (x["compra"] + x["venta"]) / 2) for x in data if x.get("compra") and x.get("venta"))
    return [f for f, _ in serie], [v for _, v in serie]


def mep_en(fecha: date) -> float | None:
    """MEP del último día hábil <= fecha (la serie trae huecos en feriados)."""
    fechas, valores = _mep_serie()
    if not fechas:
        return None
    i = bisect.bisect_right(fechas, fecha.isoformat()) - 1
    return valores[max(i, 0)]


def _usa_serie(ticker: str) -> tuple[list[str], list[float]]:
    """Cierres diarios en US$ de una acción/ETF de EE.UU. (data912, ajustados por dividendos)."""
    d = _get(f"{config.DATA912_URL}/historical/usa_stocks/{ticker}", 12 * 3600) or {}
    fechas, precios = d.get("dates") or [], d.get("prices") or []
    return (fechas, precios) if len(fechas) == len(precios) else ([], [])


def usa_en(ticker: str, fecha: date | None = None) -> float | None:
    """Cierre del último día hábil <= fecha (o el último disponible si fecha es None)."""
    fechas, precios = _usa_serie(ticker)
    if not fechas:
        return None
    if fecha is None:
        return precios[-1]
    i = bisect.bisect_right(fechas, fecha.isoformat()) - 1
    return precios[max(i, 0)]
