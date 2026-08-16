"""Ejercicio 6: relación entre el NDVI, el NDWI y el índice de cianobacteria.

Se mide la relación en dos escalas distintas, porque responden preguntas
distintas:

* **Por píxel**: dentro de una misma fecha, ¿las zonas del lago con más
  cianobacteria son también las que tienen más señal de vegetación (NDVI) y
  menos señal de agua limpia (NDWI)?
* **Por fecha**: a lo largo del tiempo, ¿las fechas con más cianobacteria son
  las que tienen valores promedio de NDVI o NDWI distintos?
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.carga import Escena
from src.config import DIR_FIGURAS, DIR_TABLAS, LAGOS
from src.estilo import CMAP_CHL, COLOR_LAGO, MARCADOR_LAGO, TINTA_SEC, TINTA_TENUE, guardar

# Con cientos de miles de píxeles por fecha, cualquier correlación sale
# "significativa"; lo que importa es su magnitud. Se submuestrea para que los
# gráficos sean manejables sin cambiar la estimación.
MAX_PIXELES_POR_ESCENA = 40_000
SEMILLA = 42


def _submuestrear(escena: Escena, rng) -> pd.DataFrame:
    idx = np.flatnonzero(escena.mascara.ravel())
    if idx.size > MAX_PIXELES_POR_ESCENA:
        idx = rng.choice(idx, MAX_PIXELES_POR_ESCENA, replace=False)
    return pd.DataFrame(
        {
            "lago": escena.lago,
            "fecha": escena.fecha,
            "chl": escena.chl.ravel()[idx],
            "ndvi": escena.ndvi.ravel()[idx],
            "ndwi": escena.ndwi.ravel()[idx],
            "ndci": escena.ndci.ravel()[idx],
        }
    )


def muestra_pixeles(escenas_por_lago: dict[str, list[Escena]]) -> pd.DataFrame:
    rng = np.random.default_rng(SEMILLA)
    partes = [
        _submuestrear(e, rng) for lista in escenas_por_lago.values() for e in lista
    ]
    return pd.concat(partes, ignore_index=True).dropna()


def correlaciones_por_pixel(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson y Spearman de chl vs NDVI y NDWI, por lago y fecha."""
    filas = []
    for (lago, fecha), grupo in df.groupby(["lago", "fecha"], sort=True):
        fila = {"lago": lago, "fecha": fecha, "n": len(grupo)}
        for indice in ("ndvi", "ndwi"):
            if grupo[indice].std() == 0 or len(grupo) < 3:
                fila[f"pearson_{indice}"] = np.nan
                fila[f"spearman_{indice}"] = np.nan
                continue
            fila[f"pearson_{indice}"] = float(
                stats.pearsonr(grupo["chl"], grupo[indice]).statistic
            )
            fila[f"spearman_{indice}"] = float(
                stats.spearmanr(grupo["chl"], grupo[indice]).statistic
            )
        filas.append(fila)
    return pd.DataFrame(filas)


def correlaciones_por_fecha(serie: pd.DataFrame) -> pd.DataFrame:
    """Correlación entre los promedios de cada fecha (una fila por lago)."""
    filas = []
    for lago, grupo in serie.groupby("lago", sort=True):
        fila = {"lago": lago, "n_fechas": len(grupo)}
        for indice in ("ndvi_medio", "ndwi_medio"):
            resultado = stats.pearsonr(grupo["chl_medio"], grupo[indice])
            fila[f"pearson_{indice}"] = float(resultado.statistic)
            fila[f"p_{indice}"] = float(resultado.pvalue)
        filas.append(fila)
    return pd.DataFrame(filas)


def figura_dispersion(df: pd.DataFrame) -> None:
    """Densidad de píxeles: chl frente a NDVI y a NDWI, un panel por lago."""
    lagos = list(LAGOS.keys())
    fig, ejes = plt.subplots(len(lagos), 2, figsize=(10, 4.5 * len(lagos)))
    ejes = np.atleast_2d(ejes)

    for fila, clave in enumerate(lagos):
        d = df[df["lago"] == clave]
        for columna, indice in enumerate(("ndvi", "ndwi")):
            eje = ejes[fila, columna]
            eje.hexbin(
                d[indice], d["chl"], gridsize=55, cmap=CMAP_CHL,
                bins="log", mincnt=1, linewidths=0,
            )
            r = stats.pearsonr(d["chl"], d[indice]).statistic
            rho = stats.spearmanr(d["chl"], d[indice]).statistic

            # Recta de ajuste, solo como guía de lectura de la pendiente.
            pendiente, intercepto = np.polyfit(d[indice], d["chl"], 1)
            xs = np.linspace(d[indice].min(), d[indice].max(), 50)
            eje.plot(xs, pendiente * xs + intercepto, color=TINTA_SEC,
                     linewidth=1.5, linestyle=(0, (5, 3)))

            eje.set_title(
                f"{LAGOS[clave]['nombre']} · {indice.upper()}\n"
                f"r de Pearson = {r:+.2f} · ρ de Spearman = {rho:+.2f}",
                fontsize=10.5,
            )
            eje.set_xlabel(indice.upper())
            eje.set_ylabel("Clorofila-a (µg/L)")

    fig.suptitle(
        "Relación píxel a píxel entre los índices de vegetación y agua y la cianobacteria",
        fontsize=12.5, fontweight="bold", y=1.0,
    )
    fig.tight_layout()
    guardar(
        fig, DIR_FIGURAS / "06_dispersion_indices.png",
        nota="Color más oscuro = más píxeles en esa zona del gráfico (escala logarítmica).",
    )


def figura_correlacion_temporal(serie: pd.DataFrame) -> None:
    """Cómo se mueven juntos, fecha a fecha, el chl promedio y el NDVI/NDWI."""
    fig, ejes = plt.subplots(1, 2, figsize=(10, 4.3))

    for eje, indice, etiqueta in (
        (ejes[0], "ndvi_medio", "NDVI promedio del agua"),
        (ejes[1], "ndwi_medio", "NDWI promedio del agua"),
    ):
        for clave in LAGOS:
            d = serie[serie["lago"] == clave]
            eje.scatter(
                d[indice], d["chl_medio"],
                color=COLOR_LAGO[clave], marker=MARCADOR_LAGO[clave],
                s=70, edgecolor="white", linewidth=1.2,
                label=LAGOS[clave]["nombre"], zorder=3,
            )
            if len(d) >= 3:
                pendiente, intercepto = np.polyfit(d[indice], d["chl_medio"], 1)
                xs = np.linspace(d[indice].min(), d[indice].max(), 50)
                eje.plot(xs, pendiente * xs + intercepto,
                         color=COLOR_LAGO[clave], linewidth=1.4,
                         linestyle=(0, (5, 3)), alpha=0.8, zorder=2)

        eje.set_xlabel(etiqueta)
        eje.set_ylabel("Clorofila-a promedio (µg/L)")
        eje.set_title(f"Clorofila-a frente a {etiqueta.split()[0]}", fontsize=10.5)

    ejes[0].legend(loc="best")
    fig.suptitle("Relación entre fechas: cada punto es una imagen satelital",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    guardar(fig, DIR_FIGURAS / "06_correlacion_temporal.png")


def _fuerza(r: float) -> str:
    a = abs(r)
    if a >= 0.7:
        return "fuerte"
    if a >= 0.4:
        return "moderada"
    if a >= 0.2:
        return "débil"
    return "prácticamente nula"


def interpretar(por_pixel: pd.DataFrame, por_fecha: pd.DataFrame) -> str:
    """Redacta los hallazgos de correlación en lenguaje llano."""
    lineas: list[str] = []

    for clave in LAGOS:
        nombre = LAGOS[clave]["nombre"]
        p = por_pixel[por_pixel["lago"] == clave]
        f = por_fecha[por_fecha["lago"] == clave]
        if p.empty:
            continue

        r_ndvi = p["pearson_ndvi"].mean()
        r_ndwi = p["pearson_ndwi"].mean()
        signo_ndvi = "positiva" if r_ndvi > 0 else "negativa"
        signo_ndwi = "positiva" if r_ndwi > 0 else "negativa"

        texto = (
            f"**{nombre}.** Píxel a píxel, la relación entre la cianobacteria y el "
            f"NDVI es {signo_ndvi} y {_fuerza(r_ndvi)} (r promedio = {r_ndvi:+.2f}), "
            f"y con el NDWI es {signo_ndwi} y {_fuerza(r_ndwi)} "
            f"(r promedio = {r_ndwi:+.2f}). "
        )

        if not f.empty:
            fila = f.iloc[0]
            texto += (
                f"Entre fechas, el promedio de clorofila-a correlaciona "
                f"{fila['pearson_ndvi_medio']:+.2f} con el NDVI promedio "
                f"(p = {fila['p_ndvi_medio']:.3f}) y "
                f"{fila['pearson_ndwi_medio']:+.2f} con el NDWI promedio "
                f"(p = {fila['p_ndwi_medio']:.3f})."
            )
        lineas.append(texto)

    lineas.append(
        "**Qué significa esto ambientalmente.** El NDVI mide cuánta clorofila hay "
        "en la superficie: como las cianobacterias son organismos fotosintéticos "
        "que flotan cerca de la superficie, un agua con floración empieza a "
        "comportarse ópticamente como si fuera vegetación, y por eso el NDVI sube "
        "donde sube la cianobacteria. El NDWI hace lo contrario: mide qué tan "
        "'limpia de vegetación' se ve el agua, así que baja cuando la superficie se "
        "cubre de biomasa. Que ambos índices se muevan en sentidos opuestos y de "
        "forma coherente con el índice de cianobacteria es una señal de que lo "
        "detectado es material biológico real en el agua y no un artefacto de la "
        "imagen. Ahora bien, ninguno de los dos índices sustituye al índice "
        "específico: el NDVI también sube con la vegetación acuática flotante y con "
        "los sedimentos suspendidos, de modo que sirve como confirmación, no como "
        "medida de cianobacteria por sí solo."
    )
    return "\n\n".join(lineas)


def ejecutar(
    escenas_por_lago: dict[str, list[Escena]], serie: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Corre el ejercicio 6 completo."""
    df_pixeles = muestra_pixeles(escenas_por_lago)
    por_pixel = correlaciones_por_pixel(df_pixeles)
    por_fecha = correlaciones_por_fecha(serie)

    por_pixel.to_csv(DIR_TABLAS / "correlacion_por_pixel.csv", index=False)
    por_fecha.to_csv(DIR_TABLAS / "correlacion_por_fecha.csv", index=False)
    print(f"  tabla -> correlacion_por_pixel.csv ({len(por_pixel)} filas)")
    print("  tabla -> correlacion_por_fecha.csv")

    figura_dispersion(df_pixeles)
    figura_correlacion_temporal(serie)
    return df_pixeles, por_pixel, por_fecha
