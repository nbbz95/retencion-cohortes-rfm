"""Retención por cohortes, segmentación RFM y valor de cliente sobre Online Retail (UCI)."""
from __future__ import annotations

import pandas as pd

# Mapa clásico de segmentos RFM a partir del puntaje de Recencia y Frecuencia (1 a 5).
SEGMENTOS = [
    ("Campeones",            {5},       {4, 5}),
    ("Leales",               {3, 4},    {4, 5}),
    ("No podemos perderlos", {1, 2},    {5}),
    ("En riesgo",            {1, 2},    {3, 4}),
    ("Potenciales leales",   {4, 5},    {2, 3}),
    ("Necesitan atención",   {3},       {3}),
    ("Nuevos",               {5},       {1}),
    ("Prometedores",         {4},       {1}),
    ("Por dormirse",         {3},       {1, 2}),
    ("Hibernando",           {1, 2},    {1, 2}),
]


def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Deja solo ventas válidas de clientes identificados."""
    total = len(df)
    df = df.copy()
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    cancel = df["InvoiceNo"].str.startswith("C")
    sin_cliente = df["CustomerID"].isna()
    invalidas = (df["Quantity"] <= 0) | (df["UnitPrice"] <= 0)
    limpio = df[~cancel & ~sin_cliente & ~invalidas].copy()
    limpio["CustomerID"] = limpio["CustomerID"].astype(int)
    limpio["InvoiceDate"] = pd.to_datetime(limpio["InvoiceDate"], format="%m/%d/%Y %H:%M")
    limpio["importe"] = limpio["Quantity"] * limpio["UnitPrice"]
    return limpio, {
        "filas_originales": total,
        "cancelaciones": int(cancel.sum()),
        "sin_cliente": int((sin_cliente & ~cancel).sum()),
        "cantidad_o_precio_invalido": int((invalidas & ~cancel & ~sin_cliente).sum()),
        "filas_finales": int(len(limpio)),
    }


def cohortes(df: pd.DataFrame, hasta: str | None = None) -> pd.DataFrame:
    """Matriz de retención: % de clientes de cada cohorte (mes de primera compra) activos en cada mes posterior."""
    d = df[["CustomerID", "InvoiceDate"]].copy()
    if hasta:
        d = d[d["InvoiceDate"] < hasta]
    d["mes"] = d["InvoiceDate"].dt.to_period("M")
    d["cohorte"] = d.groupby("CustomerID")["mes"].transform("min")
    d["periodo"] = (d["mes"] - d["cohorte"]).apply(lambda x: x.n)
    activos = d.groupby(["cohorte", "periodo"])["CustomerID"].nunique().unstack("periodo")
    return activos.div(activos[0], axis=0)


def tamanos_cohorte(df: pd.DataFrame, hasta: str | None = None) -> pd.Series:
    d = df if not hasta else df[df["InvoiceDate"] < hasta]
    primera = d.groupby("CustomerID")["InvoiceDate"].min().dt.to_period("M")
    return primera.value_counts().sort_index()


def rfm(df: pd.DataFrame, fecha_ref: pd.Timestamp) -> pd.DataFrame:
    """Recencia (días), frecuencia (facturas) y monto por cliente, con puntajes 1-5 por quintiles."""
    g = df.groupby("CustomerID").agg(
        ultima=("InvoiceDate", "max"),
        frecuencia=("InvoiceNo", "nunique"),
        monto=("importe", "sum"),
    )
    g["recencia"] = (fecha_ref - g["ultima"]).dt.days
    # rank(method="first") evita cortes duplicados cuando muchos clientes empatan (por ejemplo, 1 compra)
    g["R"] = pd.qcut(g["recencia"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    g["F"] = pd.qcut(g["frecuencia"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    g["M"] = pd.qcut(g["monto"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    g["segmento"] = [segmento(r, f) for r, f in zip(g["R"], g["F"])]
    return g.drop(columns="ultima")


def segmento(r: int, f: int) -> str:
    for nombre, rs, fs in SEGMENTOS:
        if r in rs and f in fs:
            return nombre
    raise ValueError(f"Combinación sin segmento: R={r} F={f}")


def resumen_segmentos(t: pd.DataFrame) -> pd.DataFrame:
    s = t.groupby("segmento").agg(clientes=("R", "size"), recencia=("recencia", "median"),
                                  frecuencia=("frecuencia", "median"), monto=("monto", "sum"),
                                  ticket_cliente=("monto", "median"))
    s["share_clientes"] = s["clientes"] / s["clientes"].sum()
    s["share_ingresos"] = s["monto"] / s["monto"].sum()
    return s.sort_values("monto", ascending=False)


def curva_promedio(matriz: pd.DataFrame, tamanos: pd.Series, min_cohortes: int = 3) -> list[float]:
    """Retención promedio por mes ponderada por el tamaño de cada cohorte que llegó a ese mes.

    Corta la curva cuando quedan menos de min_cohortes, porque el promedio pasa a
    depender de una o dos cohortes y deja de ser representativo.
    """
    out = []
    for p in matriz.columns:
        col = matriz[p].dropna()
        if len(col) < min_cohortes:
            break
        w = tamanos.reindex(col.index)
        out.append(float((col * w).sum() / w.sum()))
    return out
