"""Valúa la última tenencia importada a precios de mercado, en pesos y dólares MEP."""
from datetime import date, timedelta

import prices


def ultima_tenencia(con) -> tuple[dict | None, list[dict]]:
    imp = con.execute("SELECT * FROM imports ORDER BY id DESC LIMIT 1").fetchone()
    if not imp:
        return None, []
    filas = con.execute("SELECT * FROM tenencias WHERE import_id=?", (imp["id"],)).fetchall()
    return dict(imp), [dict(f) for f in filas]


def valuar(con) -> dict:
    imp, filas = ultima_tenencia(con)
    mep = prices.mep_hoy()
    if not imp:
        return {"import": None, "mep": mep, "activos": [], "totales": None}
    fecha_imp = date.fromisoformat(imp["fecha"])

    activos = []
    for f in filas:
        p_vivo, pct = prices.precio_vivo(f["tipo"], f["ticker"], f["precio"])
        precio = p_vivo if p_vivo is not None else f["precio"]
        en_usd = f["moneda_valor"] == "USD"
        valor = f["cantidad"] * precio  # en la moneda de valuación de Balanz (ARS, o USD en fondos)
        if not f["cantidad"] or not f["precio"]:
            valor = f["valor"]
        valor_usd = valor if en_usd else (valor / mep if mep else None)
        valor_ars = valor * mep if en_usd and mep else (None if en_usd else valor)

        # Variación del día (data912 trae la % contra el cierre anterior)
        hoy_usd = valor_usd - valor_usd / (1 + pct / 100) if (pct is not None and valor_usd) else None

        # Resultado: en pesos es nominal (incluye la suba del dólar). En dólares se aproxima con el
        # MEP del día de compra estimado = fecha del export - días promedio de tenencia.
        costo_usd, mep_compra = None, None
        if en_usd:
            costo_usd = f["costo"]
        elif f["costo"]:
            mep_compra = prices.mep_en(fecha_imp - timedelta(days=round(f["dias"] or 0)))
            costo_usd = f["costo"] / mep_compra if mep_compra else None
        activos.append({
            **{k: f[k] for k in ("ticker", "tipo", "descripcion", "cantidad", "ppc", "moneda_valor")},
            "precio": precio,
            "precio_origen": "vivo" if p_vivo is not None else "import",
            "pct_hoy": pct if p_vivo is not None else None,
            "valor_ars": valor_ars,
            "valor_usd": valor_usd,
            "hoy_usd": hoy_usd,
            "resultado_ars": (valor - f["costo"]) if not en_usd else None,
            "resultado_usd": (valor_usd - costo_usd) if (valor_usd is not None and costo_usd) else None,
            "costo_usd": costo_usd,
            "mep_compra": mep_compra,
            "dias": f["dias"],
        })

    tot_usd = sum(a["valor_usd"] or 0 for a in activos)
    for a in activos:
        a["peso"] = (a["valor_usd"] or 0) / tot_usd if tot_usd else 0
    con_costo = [a for a in activos if a["resultado_usd"] is not None]
    costo_tot = sum(a["costo_usd"] for a in con_costo)
    hoy_tot = sum(a["hoy_usd"] or 0 for a in activos)
    por_tipo: dict[str, float] = {}
    for a in activos:
        por_tipo[a["tipo"]] = por_tipo.get(a["tipo"], 0) + (a["valor_usd"] or 0)

    return {
        "import": imp,
        "mep": mep,
        "activos": sorted(activos, key=lambda a: -(a["valor_usd"] or 0)),
        "totales": {
            "usd": tot_usd,
            "ars": tot_usd * mep if mep else None,
            "hoy_usd": hoy_tot,
            "hoy_pct": hoy_tot / (tot_usd - hoy_tot) if tot_usd - hoy_tot else None,
            "resultado_usd": sum(a["resultado_usd"] for a in con_costo),
            "resultado_pct": sum(a["resultado_usd"] for a in con_costo) / costo_tot if costo_tot else None,
            "sin_precio_vivo": [a["ticker"] for a in activos if a["precio_origen"] == "import"],
        },
        "por_tipo": sorted(({"tipo": k, "usd": v, "peso": v / tot_usd if tot_usd else 0}
                            for k, v in por_tipo.items()), key=lambda x: -x["usd"]),
    }
