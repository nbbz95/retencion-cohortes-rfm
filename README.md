# Retención por cohortes y segmentación RFM

**Reporte en vivo:** https://nbbz95.github.io/retencion-cohortes-rfm/

Un año de ventas (dic 2010 a dic 2011) de un mayorista online de regalos del Reino Unido: 4.338 clientes y £ 8,9 M. La pregunta: **¿quiénes vuelven a comprar y en quién conviene invertir?**

## Hallazgos y acciones

1. **Cuidar a Campeones y Leales:** son el 33% de los clientes y generan el 75% de los ingresos.
2. **Reactivar a los que se están yendo:** 663 clientes que compraban seguido ("En riesgo" y "No podemos perderlos") llevan más de 100 días sin comprar y representan el 9% de los ingresos. Es la campaña de mejor retorno esperado.
3. **Conseguir la segunda compra:** solo el 20% de una cohorte vuelve el mes siguiente y la curva se aplana entre 22% y 28%. El primer mes es donde más clientes se pierden.
4. **No invertir de más en "Hibernando":** 25% de los clientes, 6% de los ingresos.

## Qué muestra este proyecto

- **Cohortes de retención** por mes de primera compra, con una curva promedio ponderada por tamaño de cohorte.
- **Criterio analítico explícito:** la cohorte de diciembre 2010 queda fuera del promedio porque mezcla clientes previos al inicio de los datos (censura a izquierda) y retiene artificialmente el doble.
- **RFM** con quintiles (usando `rank(method="first")` para que los empates no rompan los cortes) y el mapa clásico de 10 segmentos.
- **Un memo de una página** que traduce los números en acciones priorizadas.
- **Limpieza documentada:** se descartan 9.288 cancelaciones, 134.697 filas sin cliente y 40 con cantidad o precio inválido.

## Cómo correrlo

```bash
pip install -r requirements.txt
python -m pytest -q      # cohortes, curva, RFM y segmentos con datos sintéticos
python src/build.py      # genera site/data.json
python -m http.server -d site
```

```
data/online_retail.csv.gz   dataset original comprimido
src/analisis.py             limpieza, cohortes, curva de retención, RFM y segmentos
src/build.py                arma site/data.json
site/                       reporte estático (HTML + SVG, sin dependencias)
```

**Datos:** Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33
