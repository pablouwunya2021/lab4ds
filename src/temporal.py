"""Ejercicio 4: análisis temporal de la floración de cianobacteria.

Calcula el índice promedio de cianobacteria por lago y por fecha, grafica su
evolución, detecta los picos de floración y describe el patrón observado.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.carga import UMBRAL_FLORACION, Escena
from src.config import DIR_FIGURAS, DIR_TABLAS, LAGOS, RESOLUCION_M
from src.estilo import COLOR_LAGO, CRITICO, MARCADOR_LAGO, TINTA_SEC, TINTA_TENUE, guardar

# Un segundo corte, más severo, para separar "floración" de "floración intensa".
UMBRAL_INTENSO = 25.0

AREA_PIXEL_KM2 = (RESOLUCION_M**2) / 1e6


def resumen_escena(escena: Escena) -> dict:
    """Estadísticas de una fecha: nivel típico, extremos y extensión afectada."""
    valores = escena.valores
    return {
        "lago": escena.lago,
        "fecha": escena.fecha,
        "chl_medio": float(np.mean(valores)),
        "chl_mediana": float(np.median(valores)),
        "chl_p90": float(np.percentile(valores, 90)),
        "chl_max": float(np.max(valores)),
        "ndci_medio": float(np.nanmean(escena.ndci)),
        "ndvi_medio": float(np.nanmean(escena.ndvi)),
        "ndwi_medio": float(np.nanmean(escena.ndwi)),
        "fai_medio": float(np.nanmean(escena.fai)),
        "pct_area_alta": float(100 * np.mean(valores >= UMBRAL_FLORACION)),
        "pct_area_intensa": float(100 * np.mean(valores >= UMBRAL_INTENSO)),
        "area_agua_km2": float(escena.n_validos * AREA_PIXEL_KM2),
        "cobertura": float(escena.cobertura),
        "n_pixeles": escena.n_validos,
    }


def tabla_series(escenas_por_lago: dict[str, list[Escena]]) -> pd.DataFrame:
    """Serie temporal completa de ambos lagos, ordenada por lago y fecha."""
    filas = [resumen_escena(e) for lista in escenas_por_lago.values() for e in lista]
    df = pd.DataFrame(filas)
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    df["mes"] = df["fecha_dt"].dt.month
    df["anio"] = df["fecha_dt"].dt.year
    # En Guatemala la época seca va de noviembre a abril y la lluviosa de mayo
    # a octubre; la estacionalidad de la escorrentía se organiza así.
    df["estacion"] = np.where(df["mes"].isin([11, 12, 1, 2, 3, 4]), "Seca", "Lluviosa")
    return df.sort_values(["lago", "fecha_dt"]).reset_index(drop=True)


def detectar_picos(df_lago: pd.DataFrame, columna: str = "chl_medio") -> pd.DataFrame:
    """Marca como pico toda fecha que supere la media de su lago en 1 desviación.

    Con 11 observaciones por lago no tiene sentido un detector de picos
    sofisticado: lo informativo es qué fechas se salen del comportamiento
    habitual del propio lago, así que el umbral se define en unidades de su
    propia variabilidad y no con un valor absoluto arbitrario.
    """
    serie = df_lago[columna]
    umbral = serie.mean() + serie.std(ddof=0)
    salida = df_lago.copy()
    salida["umbral_pico"] = umbral
    salida["es_pico"] = serie >= umbral
    salida["z"] = (serie - serie.mean()) / (serie.std(ddof=0) or 1)
    return salida


def figura_serie_por_lago(df: pd.DataFrame) -> None:
    """Evolución temporal del índice promedio, un panel por lago."""
    lagos = list(LAGOS.keys())
    fig, ejes = plt.subplots(len(lagos), 1, figsize=(9.5, 7.2), sharex=False)

    for eje, clave in zip(ejes, lagos):
        d = detectar_picos(df[df["lago"] == clave])
        color = COLOR_LAGO[clave]

        eje.plot(
            d["fecha_dt"], d["chl_medio"],
            color=color, marker=MARCADOR_LAGO[clave],
            markerfacecolor="white", markeredgewidth=1.8, zorder=3,
        )
        # Banda intercuartil implícita: mediana vs p90 da idea de la cola alta.
        eje.fill_between(
            d["fecha_dt"], d["chl_mediana"], d["chl_p90"],
            color=color, alpha=0.13, linewidth=0, zorder=1,
            label="rango mediana – percentil 90",
        )
        eje.axhline(
            UMBRAL_FLORACION, color=CRITICO, linewidth=1.2,
            linestyle=(0, (4, 3)), zorder=2,
        )

        picos = d[d["es_pico"]]
        eje.scatter(
            picos["fecha_dt"], picos["chl_medio"],
            s=140, facecolor="none", edgecolor=CRITICO, linewidth=2, zorder=4,
        )
        for _, fila in picos.iterrows():
            eje.annotate(
                f"{fila['fecha']}\n{fila['chl_medio']:.1f}",
                (fila["fecha_dt"], fila["chl_medio"]),
                textcoords="offset points", xytext=(0, 14),
                ha="center", fontsize=8.5, color=CRITICO, fontweight="bold",
            )

        eje.set_title(f"{LAGOS[clave]['nombre']} — clorofila-a promedio del espejo de agua")
        eje.set_ylabel("Clorofila-a (µg/L)")
        eje.margins(y=0.28)
        eje.legend(loc="upper left")
        eje.text(
            0.995, 0.04, f"línea roja = umbral de floración ({UMBRAL_FLORACION:.0f} µg/L)",
            transform=eje.transAxes, ha="right", fontsize=8.5, color=TINTA_TENUE,
        )

    ejes[-1].set_xlabel("Fecha de la imagen satelital")
    fig.tight_layout()
    guardar(fig, DIR_FIGURAS / "04_serie_temporal_por_lago.png")


def figura_extension_afectada(df: pd.DataFrame) -> None:
    """Porcentaje de la superficie del lago por encima del umbral de floración."""
    fig, eje = plt.subplots(figsize=(9.5, 4.4))

    for clave in LAGOS:
        d = df[df["lago"] == clave]
        eje.plot(
            d["fecha_dt"], d["pct_area_alta"],
            color=COLOR_LAGO[clave], marker=MARCADOR_LAGO[clave],
            markerfacecolor="white", markeredgewidth=1.8,
            label=LAGOS[clave]["nombre"],
        )
        # Etiqueta directa al final de cada serie: la identidad no depende del color.
        ultima = d.iloc[-1]
        eje.annotate(
            LAGOS[clave]["nombre"].replace("Lago de ", ""),
            (ultima["fecha_dt"], ultima["pct_area_alta"]),
            textcoords="offset points", xytext=(8, 0),
            va="center", fontsize=9.5, color=COLOR_LAGO[clave], fontweight="bold",
        )

    eje.set_title(f"Extensión de la floración: superficie con más de {UMBRAL_FLORACION:.0f} µg/L")
    eje.set_ylabel("% del espejo de agua observado")
    eje.set_xlabel("Fecha de la imagen satelital")
    eje.set_ylim(-3, 103)
    eje.margins(x=0.10)
    eje.legend(loc="center left")
    fig.tight_layout()
    guardar(fig, DIR_FIGURAS / "04_extension_floracion.png")


def figura_estacional(df: pd.DataFrame) -> None:
    """Distribución del índice según estación seca / lluviosa (Ej. 8.4)."""
    fig, ejes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)

    for eje, clave in zip(ejes, LAGOS):
        d = df[df["lago"] == clave]
        grupos, etiquetas = [], []
        for estacion in ("Seca", "Lluviosa"):
            valores = d[d["estacion"] == estacion]["chl_medio"].to_numpy()
            if len(valores):
                grupos.append(valores)
                etiquetas.append(f"{estacion}\n(n={len(valores)})")

        caja = eje.boxplot(
            grupos, tick_labels=etiquetas, widths=0.5,
            patch_artist=True, medianprops={"color": "white", "linewidth": 2},
            flierprops={"marker": "o", "markersize": 4, "markerfacecolor": TINTA_TENUE,
                        "markeredgecolor": "none"},
        )
        for parche in caja["boxes"]:
            parche.set(facecolor=COLOR_LAGO[clave], alpha=0.75, edgecolor="none")
        for elemento in ("whiskers", "caps"):
            for linea in caja[elemento]:
                linea.set(color=TINTA_SEC, linewidth=1)

        # Los puntos individuales: con n pequeño, la caja sola engaña.
        for i, valores in enumerate(grupos, start=1):
            jitter = np.random.default_rng(7).normal(0, 0.045, len(valores))
            eje.scatter(i + jitter, valores, s=26, color=TINTA_SEC, alpha=0.75, zorder=3)

        eje.set_title(LAGOS[clave]["nombre"])
        eje.grid(axis="x", visible=False)

    ejes[0].set_ylabel("Clorofila-a promedio (µg/L)")
    fig.suptitle(
        "Comparación por estación del año (seca: nov–abr · lluviosa: may–oct)",
        fontsize=12.5, fontweight="bold", y=1.02,
    )
    fig.tight_layout()
    guardar(fig, DIR_FIGURAS / "08_patron_estacional.png")


def interpretar(df: pd.DataFrame) -> str:
    """Redacta la lectura del comportamiento temporal a partir de los números."""
    lineas: list[str] = []

    for clave in LAGOS:
        d = detectar_picos(df[df["lago"] == clave]).sort_values("fecha_dt")
        nombre = LAGOS[clave]["nombre"]
        picos = d[d["es_pico"]]
        maximo = d.loc[d["chl_medio"].idxmax()]
        minimo = d.loc[d["chl_medio"].idxmin()]

        # Tendencia: pendiente de una recta ajustada al tiempo en días.
        dias = (d["fecha_dt"] - d["fecha_dt"].min()).dt.days.to_numpy(dtype=float)
        pendiente = float(np.polyfit(dias, d["chl_medio"].to_numpy(), 1)[0]) * 365
        variabilidad = d["chl_medio"].std(ddof=0) / max(d["chl_medio"].mean(), 1e-9)

        if abs(pendiente) < 0.5:
            tendencia = "se mantiene estable en el conjunto del período"
        elif pendiente > 0:
            tendencia = f"muestra una tendencia al alza (+{pendiente:.1f} µg/L por año)"
        else:
            tendencia = f"muestra una tendencia a la baja ({pendiente:.1f} µg/L por año)"

        regimen = (
            "con oscilaciones fuertes entre fechas" if variabilidad > 0.35
            else "con oscilaciones moderadas entre fechas"
        )

        seca = d[d["estacion"] == "Seca"]["chl_medio"]
        lluviosa = d[d["estacion"] == "Lluviosa"]["chl_medio"]
        if len(seca) and len(lluviosa):
            estacional = (
                f"El promedio en época seca es {seca.mean():.1f} µg/L y en época "
                f"lluviosa {lluviosa.mean():.1f} µg/L."
            )
        else:
            estacional = "Las fechas disponibles no cubren ambas estaciones por igual."

        lineas.append(
            f"**{nombre}.** El índice promedio va de {minimo['chl_medio']:.1f} µg/L "
            f"({minimo['fecha']}) a {maximo['chl_medio']:.1f} µg/L ({maximo['fecha']}); "
            f"{tendencia}, {regimen}. "
            f"Fechas críticas (por encima de la media del lago más una desviación): "
            f"{', '.join(picos['fecha']) if len(picos) else 'ninguna'}. "
            f"En su fecha más afectada, el {maximo['pct_area_alta']:.1f} % del espejo "
            f"de agua superó los {UMBRAL_FLORACION:.0f} µg/L. {estacional}"
        )

    return "\n\n".join(lineas)


def ejecutar(escenas_por_lago: dict[str, list[Escena]]) -> pd.DataFrame:
    """Corre todo el ejercicio 4 y devuelve la tabla de series temporales."""
    df = tabla_series(escenas_por_lago)
    df.to_csv(DIR_TABLAS / "serie_temporal.csv", index=False)
    print(f"  tabla -> serie_temporal.csv ({len(df)} filas)")

    figura_serie_por_lago(df)
    figura_extension_afectada(df)
    figura_estacional(df)
    return df
