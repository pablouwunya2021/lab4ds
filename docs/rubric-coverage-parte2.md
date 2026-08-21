# Matriz de cobertura — Laboratorio 4, Parte 2

Última actualización: 2026-08-20. `Implementado` significa que existe código verificable con
datos sintéticos; `verificado` exige artefactos producidos con los 22 rasters oficiales. No se
presentan métricas simuladas como resultados académicos.

| Ejercicio/inciso o rúbrica | Requisito | Código | Evidencia notebook/informe | Artefacto | Estado |
|---|---|---|---|---|---|
| 1.1–1.3; preparación | Raster a fila geográfica y filtros auditables | `src/ml_dataset.py` | Notebook §1 | `observations_master.parquet`, `filter_log.csv` | Verificado |
| 1.4–1.6; EDA | Conteos, tipos, faltantes, clases, estadísticas y mapas | `src/ml_artifacts.py` | Notebook §1–3 | tablas/figuras EDA | Verificado |
| 2.1–2.5; respuesta | y binaria, corte, balance y leakage | `src/ml_dataset.py`, `src/ml_features.py` | Notebook §2 | `predictor_audit.csv` | Verificado |
| 3.1–3.3; predictores | Conjunto estricto y variables temporales | `src/ml_features.py` | Notebook §3 | auditoría de predictores | Verificado |
| 4.1–4.4; modelos | LR, RF, HGB; 70/30 común; búsqueda en train | `src/ml_models.py`, `src/parte2.py` | Notebook §4 | modelos y parámetros | Verificado |
| 5.1–5.3; evaluación | métricas, confusión, criterio ambiental | `src/ml_validation.py` | Notebook §5 | `random_metrics.csv` | Verificado |
| 6.1–6.6; espacial | EPSG:32615, bloques 1 km, folds por grupo | `src/ml_dataset.py`, `src/ml_validation.py` | Notebook §6 | métricas por fold/mapas | Verificado |
| Rúbrica temporal | Últimas fechas completas, sin futuro en train | `src/ml_validation.py`, `src/parte2.py` | Notebook §7 | `temporal_split.csv` | Verificado |
| 7.1–7.6; entre lagos | A→B y B→A sin usar destino en ajuste | `src/parte2.py` | Notebook §8 | métricas de transferencia | Verificado |
| 8.1–8.4; interpretación | Permutación y SHAP | `src/ml_explain.py` | Notebook §9 | tabla y SHAP summary | Verificado |
| 9.1–9.7; mapas | Probabilidad común, clases y reconstrucción sin interpolar | `src/ml_maps.py` | Notebook §10 | mapas por lago/error | Verificado |
| 10.1–10.3; conclusiones | Evidencia, limitaciones y mejoras | generador de informe | Informe | PDF | Verificado |
| Entregable notebook | Rutas relativas, funciones de `src`, kernel limpio | `notebooks/laboratorio4_parte2.ipynb` | Completo | notebook ejecutado | Verificado |
| Entregable PDF | Informe programático e inspección de páginas | `src/informe_parte2.py` | Informe completo | PDF + PNG por página | Verificado |
| Versionamiento | Rama y commits semánticos | Git | Anexo | historial | Implementado |

## Linaje y decisión anti-leakage

`NDCI=(B05-B04)/(B05+B04)`; `chl=826.57·NDCI³−176.43·NDCI²+19·NDCI+4.071`;
`y=1[chl≥10 µg/L]`. El modelo principal excluye `chl`, `NDCI`, `y`, B04, B05, NDVI y
FAI (los dos últimos comparten B04). Coordenadas y lago se conservan, pero se excluyen de `X`.

El corte de 10 µg/L es una **categoría operativa del proxy**, no una medición de campo ni
toxicidad. La guía OMS histórica lo vincula a probabilidad relativamente baja de efectos solo
cuando la clorofila-a es medida y dominan cianobacterias; la guía OMS 2021 exige verificar esa
dominancia. Por eso este laboratorio no convierte automáticamente reflectancia en riesgo sanitario.

## Fuentes metodológicas

- Mishra, S. & Mishra, D. R. (2012). *Normalized difference chlorophyll index*.
  Remote Sensing of Environment 117, 394–406. DOI: 10.1016/j.rse.2011.10.016.
- WHO (2021). *Guidelines on recreational water quality, Volume 1* (ISBN 9789240031302).
- US EPA (2019). *Recommendations for Cyanobacteria and Cyanotoxin Monitoring in Recreational Waters*.
- Kravitz & Matthews (2020). *CyanoLakes Chlorophyll-a*, Sentinel Hub custom script.

## Evidencia ejecutada

Se verificaron 22/22 rasters ML v1 y 3,190,331 observaciones. La clase positiva contiene
44,328 observaciones (42,990 en Amatitlán y 1,338 en Atitlán). Todos los resultados numéricos
se encuentran en `outputs/parte2/metrics/` y se regeneran con `python -m src.parte2`.
