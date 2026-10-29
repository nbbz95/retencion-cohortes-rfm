import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import analisis as a  # noqa: E402


def ventas(filas):
    return pd.DataFrame(filas, columns=["InvoiceNo", "CustomerID", "InvoiceDate", "importe"]).assign(
        InvoiceDate=lambda d: pd.to_datetime(d["InvoiceDate"]))


def test_limpiar_saca_cancelaciones_sin_cliente_e_invalidas():
    df = pd.DataFrame({
        "InvoiceNo": ["1", "C2", "3", "4"],
        "CustomerID": [10.0, 10.0, None, 11.0],
        "Quantity": [2, -2, 1, 0],
        "UnitPrice": [1.5, 1.5, 3.0, 2.0],
        "InvoiceDate": ["12/1/2010 8:26"] * 4,
    })
    limpio, info = a.limpiar(df)
    assert list(limpio["InvoiceNo"]) == ["1"]
    assert limpio["importe"].item() == 3.0
    assert (info["cancelaciones"], info["sin_cliente"], info["cantidad_o_precio_invalido"]) == (1, 1, 1)


def test_cohortes_cuenta_clientes_activos_por_mes():
    df = ventas([
        ("1", 1, "2011-01-05", 10), ("2", 2, "2011-01-20", 10),   # cohorte enero: 2 clientes
        ("3", 1, "2011-02-03", 10),                               # vuelve 1 de 2 en el mes 1
        ("4", 3, "2011-02-10", 10),                               # cohorte febrero: 1 cliente
        ("5", 2, "2011-03-01", 10), ("6", 3, "2011-03-15", 10),
    ])
    m = a.cohortes(df)
    assert m.loc[pd.Period("2011-01"), 0] == 1
    assert m.loc[pd.Period("2011-01"), 1] == 0.5
    assert m.loc[pd.Period("2011-01"), 2] == 0.5
    assert m.loc[pd.Period("2011-02"), 1] == 1


def test_curva_corta_con_pocas_cohortes():
    m = pd.DataFrame({0: [1, 1, 1], 1: [0.5, 0.2, None]}, index=["a", "b", "c"])
    t = pd.Series({"a": 100, "b": 300, "c": 50})
    assert a.curva_promedio(m, t, min_cohortes=2) == [1.0, pytest.approx((50 + 60) / 400)]
    assert a.curva_promedio(m, t, min_cohortes=3) == [1.0]


@pytest.mark.parametrize("r, f, esperado", [
    (5, 5, "Campeones"), (4, 4, "Leales"), (1, 5, "No podemos perderlos"), (2, 3, "En riesgo"),
    (5, 1, "Nuevos"), (1, 1, "Hibernando"), (3, 3, "Necesitan atención"),
])
def test_segmento(r, f, esperado):
    assert a.segmento(r, f) == esperado


def test_todas_las_combinaciones_tienen_segmento():
    for r in range(1, 6):
        for f in range(1, 6):
            assert a.segmento(r, f)


def test_rfm_puntajes():
    filas = []
    for c in range(1, 11):  # el cliente c compra c veces y la última vez hace 11 - c días
        for k in range(c):
            filas.append((f"{c}-{k}", c, pd.Timestamp("2011-12-10") - pd.Timedelta(days=11 - c + k), 10.0 * c))
    t = a.rfm(ventas(filas), pd.Timestamp("2011-12-10"))
    assert t.loc[10, ["R", "F", "M"]].tolist() == [5, 5, 5]
    assert t.loc[1, ["R", "F", "M"]].tolist() == [1, 1, 1]
    assert t.loc[10, "segmento"] == "Campeones"
