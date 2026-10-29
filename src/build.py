"""Corre el análisis y genera site/data.json."""
import json
from pathlib import Path

import pandas as pd

import analisis as a

RAIZ = Path(__file__).resolve().parent.parent
HASTA = "2011-12-01"          # diciembre de 2011 está incompleto (termina el 9): queda fuera de las cohortes
FECHA_REF = pd.Timestamp("2011-12-10")


def main() -> dict:
    crudo = pd.read_csv(RAIZ / "data" / "online_retail.csv.gz", dtype={"InvoiceNo": str, "StockCode": str})
    df, limpieza = a.limpiar(crudo)

    matriz = a.cohortes(df, HASTA)
    tamanos = a.tamanos_cohorte(df, HASTA)
    # La cohorte de diciembre 2010 mezcla clientes nuevos con clientes previos al inicio de los datos
    # (censura a izquierda), así que la curva promedio se calcula sin ella.
    curva = a.curva_promedio(matriz.iloc[1:], tamanos)
    t = a.rfm(df, FECHA_REF)
    seg = a.resumen_segmentos(t)

    reino_unido = df["Country"].eq("United Kingdom")
    por_cliente = df.groupby("CustomerID")["InvoiceNo"].nunique()
    salida = {
        "limpieza": limpieza,
        "kpis": {
            "clientes": int(df["CustomerID"].nunique()),
            "ingresos": float(df["importe"].sum()),
            "recompra": float((por_cliente > 1).mean()),
            "retencion_m1": curva[1],
            "retencion_m3": curva[3],
            "retencion_dic10_m11": float(matriz.iloc[0, 11]),
            "share_uk": float(df.loc[reino_unido, "importe"].sum() / df["importe"].sum()),
        },
        "cohortes": {
            "filas": [str(p) for p in matriz.index],
            "tamanos": [int(tamanos[p]) for p in matriz.index],
            "columnas": [int(c) for c in matriz.columns],
            "valores": [[None if pd.isna(v) else round(float(v), 4) for v in fila] for fila in matriz.values],
            "curva": curva,
        },
        "segmentos": [
            {"segmento": k, **{c: (float(v) if c != "clientes" else int(v)) for c, v in r.items()}}
            for k, r in seg.iterrows()
        ],
        "mensual": [
            {"mes": str(m), "ingresos": float(v)}
            for m, v in df[df["InvoiceDate"] < HASTA].groupby(df["InvoiceDate"].dt.to_period("M"))["importe"].sum().items()
        ],
    }
    (RAIZ / "site" / "data.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    return salida


if __name__ == "__main__":
    s = main()
    print(json.dumps(s["limpieza"]), json.dumps(s["kpis"]))
    for x in s["segmentos"]:
        print(f"{x['segmento']:<22} {x['clientes']:>5} clientes {x['share_clientes']:.1%} | ingresos {x['share_ingresos']:.1%} | rec {x['recencia']:.0f} d | frec {x['frecuencia']:.0f}")
    print([round(v, 3) for v in s["cohortes"]["curva"]])
