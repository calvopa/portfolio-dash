"""Portfolio Balanz — dashboard de seguimiento (homelab, solo LAN).

Importa el Excel "Mis Instrumentos" de Balanz, lo valúa con precios en vivo de data912 y el dólar
MEP, y guarda una foto del total cada SNAPSHOT_MINUTES para el gráfico de evolución.
"""
import logging
import secrets
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

import balanz
import config
import db
import valuacion

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger("portfolio")
ART = timezone(timedelta(hours=-3))

if not config.DASH_PASSWORD:
    raise SystemExit("Falta DASH_PASSWORD en el .env — el dashboard no arranca sin contraseña")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
seguridad = HTTPBasic()
con = db.connect(config.DATA_DIR)
_lock = threading.Lock()
STATIC = Path(__file__).parent / "static"


def require_auth(cred: HTTPBasicCredentials = Depends(seguridad)):
    ok_user = secrets.compare_digest(cred.username.encode(), config.DASH_USER.encode())
    ok_pass = secrets.compare_digest(cred.password.encode(), config.DASH_PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})


def foto():
    """Guarda el total valuado ahora (para el gráfico de evolución)."""
    with _lock:
        v = valuacion.valuar(con)
        if not v["totales"]:
            return
        con.execute("INSERT OR REPLACE INTO historia VALUES (?,?,?,?,?)", (
            datetime.now(ART).isoformat(timespec="seconds"), v["totales"]["ars"], v["totales"]["usd"],
            v["mep"], v["import"]["id"]))
        con.commit()


def _loop_fotos():
    while True:
        try:
            foto()
        except Exception:
            log.exception("Error guardando la foto del portfolio")
        time.sleep(config.SNAPSHOT_MINUTES * 60)


@app.on_event("startup")
def arrancar():
    threading.Thread(target=_loop_fotos, daemon=True).start()
    log.info("Portfolio dashboard arrancado")


@app.get("/")
def index(_: None = Depends(require_auth)):
    return FileResponse(STATIC / "index.html")


@app.get("/api/portfolio")
def api_portfolio(_: None = Depends(require_auth)):
    with _lock:
        return valuacion.valuar(con)


@app.get("/api/historia")
def api_historia(_: None = Depends(require_auth)):
    """Último valor de cada día (hora ART)."""
    por_dia: dict[str, dict] = {}
    for r in con.execute("SELECT * FROM historia ORDER BY ts"):
        por_dia[r["ts"][:10]] = {"fecha": r["ts"][:10], "usd": r["total_usd"], "ars": r["total_ars"], "mep": r["mep"]}
    return list(por_dia.values())


class Efectivo(BaseModel):
    usd: float = Field(0, ge=0, le=1e9)
    ars: float = Field(0, ge=0, le=1e12)


@app.put("/api/efectivo")
def api_efectivo(e: Efectivo, _: None = Depends(require_auth)):
    """Efectivo sin invertir en la cuenta: el Excel de Balanz no lo trae, se carga a mano."""
    with _lock:
        con.execute("INSERT OR REPLACE INTO efectivo VALUES (1, ?, ?, ?)",
                    (e.usd, e.ars, datetime.now(ART).isoformat(timespec="seconds")))
        con.commit()
    foto()
    return valuacion.efectivo(con)


@app.post("/api/import")
async def api_import(archivo: UploadFile = File(...), _: None = Depends(require_auth)):
    contenido = await archivo.read(config.MAX_UPLOAD_BYTES + 1)
    if len(contenido) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Archivo demasiado grande")
    try:
        filas = balanz.leer(contenido)
    except Exception as e:  # archivo que no es xlsx, o sin las columnas esperadas
        raise HTTPException(400, f"No pude leer el archivo: {e}")
    fecha = balanz.fecha_del_nombre(archivo.filename) or date.today()
    with _lock:
        cur = con.execute("INSERT INTO imports (fecha, cargado) VALUES (?, ?)",
                          (fecha.isoformat(), datetime.now(ART).isoformat(timespec="seconds")))
        iid = cur.lastrowid
        con.executemany(
            "INSERT INTO tenencias VALUES (:import_id,:ticker,:tipo,:descripcion,:cantidad,:precio,:ppc,"
            ":valor,:costo,:dias,:moneda_valor)", [{**f, "import_id": iid} for f in filas])
        con.commit()
    log.info("Import %s: %d instrumentos (tenencia del %s)", iid, len(filas), fecha)
    foto()
    return {"import_id": iid, "fecha": fecha.isoformat(), "instrumentos": len(filas)}
