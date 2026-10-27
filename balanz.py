"""Lectura del Excel "Mis Instrumentos" que exporta Balanz.

Reglas verificadas contra un export real (26/10/2026):
- "Valor actual" / "Valor inicial" vienen en PESOS para todo, salvo los Fondos, que vienen en la
  moneda del fondo (columna "Moneda"). Sumarlos tal cual mezcla pesos con dólares; con esta regla
  los % de cartera coinciden con la columna "Porcentaje de tenencia" de Balanz (±1,5 pts).
- En Bonos y ONs la columna "Moneda" es la del instrumento, no la del precio: el precio es en pesos
  por 1 nominal (el mercado cotiza por 100).
- El nombre del archivo trae el titular y los números de cuenta: no se guardan.
"""
import io
import re
from datetime import date

import openpyxl

COLUMNAS = ["Ticker", "Tipo de Instrumento", "Descripcion", "Nominales", "Precio",
            "Precio promedio de compra", "Valor actual", "Valor inicial", "Días promedio de tenencia", "Moneda"]
MONEDAS_USD = {"dólares", "dolares", "us dollar (cable)", "us dollar", "usd"}


def _num(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("%", "").strip()
    if "," in s:  # formato argentino: 1.234,56
        s = s.replace(".", "").replace(",", ".")
    return float(s or 0)


def fecha_del_nombre(nombre: str) -> date | None:
    m = re.search(r"\[(\d{8})\]", nombre or "")
    if not m:
        return None
    s = m.group(1)
    return date(int(s[:4]), int(s[4:6]), int(s[6:]))


def leer(contenido: bytes) -> list[dict]:
    ws = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True).worksheets[0]
    filas = ws.iter_rows(values_only=True)
    cab = [str(c).strip() if c is not None else "" for c in next(filas)]
    faltan = [c for c in COLUMNAS if c not in cab]
    if faltan:
        raise ValueError(f"No parece un export de 'Mis Instrumentos' de Balanz: faltan columnas {faltan}")
    idx = {c: cab.index(c) for c in COLUMNAS}

    out = []
    for f in filas:
        if not f or not f[idx["Ticker"]]:
            continue
        tipo = str(f[idx["Tipo de Instrumento"]] or "").strip()
        moneda = str(f[idx["Moneda"]] or "").strip()
        moneda_valor = "USD" if tipo == "Fondos" and moneda.lower() in MONEDAS_USD else "ARS"
        out.append({
            "ticker": str(f[idx["Ticker"]]).strip(),
            "tipo": tipo,
            "descripcion": str(f[idx["Descripcion"]] or "").strip(),
            "cantidad": _num(f[idx["Nominales"]]),
            "precio": _num(f[idx["Precio"]]),
            "ppc": _num(f[idx["Precio promedio de compra"]]),
            "valor": _num(f[idx["Valor actual"]]),
            "costo": _num(f[idx["Valor inicial"]]),
            "dias": _num(f[idx["Días promedio de tenencia"]]),
            "moneda_valor": moneda_valor,
        })
    if not out:
        raise ValueError("El archivo no tiene instrumentos")
    return out
