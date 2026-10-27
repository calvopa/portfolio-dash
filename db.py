import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,          -- fecha de la tenencia (del nombre del archivo, o del día de carga)
    cargado TEXT NOT NULL         -- cuándo se subió
);
CREATE TABLE IF NOT EXISTS tenencias (
    import_id INTEGER NOT NULL REFERENCES imports(id),
    ticker TEXT NOT NULL, tipo TEXT, descripcion TEXT,
    cantidad REAL, precio REAL, ppc REAL, valor REAL, costo REAL, dias REAL, moneda_valor TEXT,
    PRIMARY KEY (import_id, ticker)
);
CREATE TABLE IF NOT EXISTS efectivo (   -- plata sin invertir en la cuenta (el Excel de Balanz no la trae)
    id INTEGER PRIMARY KEY CHECK (id = 1),
    usd REAL NOT NULL DEFAULT 0, ars REAL NOT NULL DEFAULT 0, actualizado TEXT
);
CREATE TABLE IF NOT EXISTS historia (
    ts TEXT PRIMARY KEY,          -- ISO, hora ART
    total_ars REAL, total_usd REAL, mep REAL, import_id INTEGER
);
"""


def connect(data_dir: str) -> sqlite3.Connection:
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(Path(data_dir) / "portfolio.db", check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(ESQUEMA)
    return con
