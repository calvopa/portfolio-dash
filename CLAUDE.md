# CLAUDE.md

Guía para Claude Code en este repo.

## Qué es esto

Dashboard de **seguimiento** del portfolio personal de Pablo en **Balanz** (broker argentino). No
opera ni se conecta a Balanz (no tiene API pública para clientes): se importa el Excel
**"Mis Instrumentos"** que exporta Balanz, y el dashboard lo valúa con precios en vivo y el dólar
MEP. Proyecto **personal** (no GCS): vive en el homelab, solo LAN, con usuario y contraseña.

Muestra: valor total en US$ MEP y pesos, variación del día, resultado en dólares (aprox.) y en pesos,
distribución por tipo, evolución del total (una foto cada 15 min, un punto por día) y la tabla de
tenencias. Tema **Panel Oscuro** de Pablo.

## Fuentes de datos — todas públicas, sin claves (verificadas en vivo el 26/10/2026)

| Dato | Fuente |
|---|---|
| Precios CEDEARs / acciones / bonos / ONs / letras | `data912.com/live/arg_cedears`, `arg_stocks`, `arg_bonds`, `arg_corp`, `arg_notes` (~20 min de demora) |
| Dólar MEP hoy | `dolarapi.com/v1/dolares/bolsa` (promedio compra/venta); respaldo: AL30 / AL30D de data912 |
| Dólar MEP histórico | `api.argentinadatos.com/v1/cotizaciones/dolares/bolsa` (desde 2018, con huecos en feriados) |
| Benchmark "¿te conviene?" | `data912.com/historical/usa_stocks/SPY` (cierres diarios en US$ desde 2016, **ajustados por dividendos**; `BENCHMARK` en config) |
| Fondos (FCI) | **sin precio en vivo**: se usa el del último import (marcado `import` en la tabla) |

## Gotchas del Excel de Balanz (verificados con un export real)

- **Monedas mezcladas**: "Valor actual"/"Valor inicial" vienen en **pesos** para todo salvo los
  **Fondos**, que vienen en la moneda del fondo (columna "Moneda"). Con esa regla los % de cartera
  coinciden con la columna "Porcentaje de tenencia" de Balanz (±1,5 pts; Balanz usa otro tipo de cambio).
- En Bonos/ONs la columna "Moneda" es la del instrumento, **no** la del precio: el precio es en pesos
  por 1 nominal. data912 cotiza **por 100** → `prices.precio_vivo()` elige la escala (1 o 100) más
  cercana al precio importado y descarta el precio vivo si difiere > 50%.
- El "Rendimiento" de Balanz es en pesos nominales: incluye la devaluación (ej. AE38 +192% en pesos
  ≈ +94% en dólares). Por eso el resultado en dólares se calcula aparte: costo en pesos / MEP del
  día de compra estimado (fecha del export − "Días promedio de tenencia"). Es aproximado si se compró
  en varias veces; no incluye cupones ni dividendos cobrados.
- El **nombre del archivo** trae titular y números de cuenta: no se guarda, solo la fecha (`[AAAAMMDD]`).
  Tampoco se guarda el archivo: solo las filas parseadas en `portfolio.db`.

## Comparación "¿te conviene invertir así?"

`valuacion._comparacion()`: para cada activo con costo en US$, qué valdrían hoy esos mismos dólares si en la
fecha de compra estimada se hubieran puesto en el SPY (`bench_usd`), o dejado quietos en MEP (= el costo).
La columna `vs_bench_usd` de la tabla es `valor_usd - bench_usd`. Es exigente con la cartera: el SPY va con
dividendos reinvertidos y la cartera sin cupones/dividendos cobrados. Un CEDEAR de SPY puede salir distinto
de 0 contra el SPY por la diferencia CCL/MEP y la fecha estimada.

## Infraestructura

| Elemento | Valor |
|---|---|
| Código local | `/home/calvop/portfolio-dash/` |
| Servidor | srv-hometainer `192.168.232.60`, stack `/opt/stacks/portfolio-dash/` |
| URL (LAN) | `http://192.168.232.60:8088` — usuario/contraseña en `.env` del server (`DASH_USER`/`DASH_PASSWORD`) |
| Container / volumen | `portfolio-dash` / `portfolio_data` → `/data/portfolio.db` (imports, tenencias, historia) |
| GitHub | `github.com/calvopa/portfolio-dash` (privado), deploy key de solo lectura en el server |

Sin `DASH_PASSWORD` la app **no arranca** (a propósito: son datos financieros personales).

## Comandos

```bash
# Deploy — git push + pull + rebuild, NUNCA scp
cd /home/calvop/portfolio-dash && git push origin main
ssh pablo@192.168.232.60 "cd /opt/stacks/portfolio-dash && git pull && docker compose up -d --build"

# Logs
ssh pablo@192.168.232.60 "docker logs -f portfolio-dash"

# Probar local (sin Docker)
python3 -m venv /tmp/pv && /tmp/pv/bin/pip install -r requirements.txt
DASH_PASSWORD=prueba DATA_DIR=/tmp/pdata /tmp/pv/bin/uvicorn app:app --port 8188
```

## Arquitectura

| Archivo | Rol |
|---|---|
| `balanz.py` | Parser del Excel "Mis Instrumentos" (reglas de moneda de arriba) |
| `prices.py` | data912 + MEP hoy/histórico, con caché (y fallback al último valor si la API falla) |
| `valuacion.py` | Valúa la última tenencia: ARS, US$, día, resultado US$ aprox. y en pesos, por tipo |
| `db.py` | SQLite: `imports`, `tenencias`, `historia` |
| `app.py` | FastAPI + auth básica + foto del total cada `SNAPSHOT_MINUTES` |
| `static/index.html` | Página (Chart.js 4.4.1 de cdnjs, tema Panel Oscuro). En móvil la tabla deja solo Activo / Valor / Hoy / Resultado US$ |

## Pendientes / ideas

- Precio en vivo de FCI (CAFCI) — hoy usa el del import.
- Importar "Movimientos" para costo exacto por operación y cupones/dividendos.
- La evolución arranca con el primer import; no hay historia previa.
