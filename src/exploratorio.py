"""Ejercicio 8: análisis exploratorio adicional.

Compara la distribución completa de valores entre fechas (no solo el promedio),
que es donde se ve la diferencia entre "todo el lago subió un poco" y "una parte
del lago subió muchísimo".
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.carga import UMBRAL_FLORACION, Escena
from src.config import DIR_FIGURAS, DIR_TABLAS, LAGOS
from src.estilo import COLOR_LAGO, CRITICO, TINTA_SEC, TINTA_TENUE, guardar
from src.formato import pct
from src.temporal import UMBRAL_INTENSO

LIMITE_HISTOGRAMA = 60.0


def figura_distribuciones(clave_lago: str, escenas: list[Escena]) -> None:
    """Distribución de valores por fecha, en cascada, para ver la forma completa."""
    color = COLOR_LAGO[clave_lago]
    fig, eje = plt.subplots(figsize=(9.5, 0.62 * len(escenas) + 2.6))

    bordes = np.linspace(0, LIMITE_HISTOGRAMA, 61)
    centros = (bordes[:-1] + bordes[1:]) / 2
    separacion = 1.0

    for i, escena in enumerate(reversed(escenas)):
        valores = np.clip(escena.valores, 0, LIMITE_HISTOGRAMA)
        densidad, _ = np.histogram(valores, bins=bordes, density=True)
        # Se normaliza cada curva a la misma altura: interesa comparar la forma
        # y la posición de la distribución, no cuántos píxeles tenía cada fecha.
        altura = densidad / max(densidad.max(), 1e-9) * 0.92
        base = i * separacion

        eje.fill_between(centros, base, base + altura, color=color,
                         alpha=0.55, linewidth=0, zorder=len(escenas) - i)
        eje.plot(centros, base + altura, color="white", linewidth=1.1,
                 zorder=len(escenas) - i)

        mediana = float(np.median(valores))
        # La marca de la mediana llega hasta la altura de la curva en ese punto.
        alto_mediana = float(np.interp(mediana, centros, altura))
        eje.plot([mediana, mediana], [base, base + alto_mediana],
                 color=TINTA_SEC, linewidth=1.3, zorder=len(escenas) - i)
        eje.text(LIMITE_HISTOGRAMA * 1.02, base + 0.25,
                 f"mediana {mediana:.1f}", fontsize=8.5, color=TINTA_TENUE, va="center")

    eje.axvline(UMBRAL_FLORACION, color=CRITICO, linewidth=1.3, linestyle=(0, (4, 3)),
                zorder=len(escenas) + 1)
    eje.set_yticks(
        [i * separacion + 0.35 for i in range(len(escenas))],
        [e.fecha for e in reversed(escenas)],
    )
    eje.set_xlim(0, LIMITE_HISTOGRAMA * 1.18)
    eje.set_xlabel("Clorofila-a (µg/L)")
    eje.set_title(
        f"{LAGOS[clave_lago]['nombre']} — distribución de valores en cada fecha",
        fontsize=12.5,
    )
    eje.grid(axis="y", visible=False)
    eje.text(UMBRAL_FLORACION + 0.8, len(escenas) * separacion,
             f"umbral de floración ({UMBRAL_FLORACION:.0f} µg/L)",
             fontsize=8.5, color=CRITICO)
    fig.tight_layout()
    guardar(
        fig, DIR_FIGURAS / f"08_distribuciones_{clave_lago}.png",
        nota="Cada curva es una fecha; a más área a la derecha del umbral, mayor "
             "porción del lago en floración.",
    )


def figura_extension_por_categoria(serie: pd.DataFrame) -> None:
    """Cuánto del lago está limpio, en alerta o en floración intensa, por fecha."""
    fig, ejes = plt.subplots(len(LAGOS), 1, figsize=(9.5, 7.4))

    for eje, clave in zip(np.atleast_1d(ejes), LAGOS):
        d = serie[serie["lago"] == clave].reset_index(drop=True)
        x = np.arange(len(d))
        limpio = 100 - d["pct_area_alta"]
        alerta = d["pct_area_alta"] - d["pct_area_intensa"]
        intenso = d["pct_area_intensa"]

        # Separación de 2 px entre segmentos para que el apilado no se lea
        # como una sola masa continua.
        eje.bar(x, limpio, color="#cde2fb", label=f"por debajo de {UMBRAL_FLORACION:.0f} µg/L",
                edgecolor="white", linewidth=1.5)
        eje.bar(x, alerta, bottom=limpio, color="#fab219",
                label=f"{UMBRAL_FLORACION:.0f}–{UMBRAL_INTENSO:.0f} µg/L (floración)",
                edgecolor="white", linewidth=1.5)
        eje.bar(x, intenso, bottom=limpio + alerta, color=CRITICO,
                label=f"más de {UMBRAL_INTENSO:.0f} µg/L (floración intensa)",
                edgecolor="white", linewidth=1.5)

        eje.set_xticks(x, d["fecha"], rotation=35, ha="right", fontsize=8.5)
        eje.set_ylabel("% del espejo de agua")
        eje.set_ylim(0, 100)
        eje.set_title(LAGOS[clave]["nombre"], fontsize=11)
        eje.grid(axis="x", visible=False)
        eje.legend(loc="lower left", bbox_to_anchor=(0, 1.06), ncols=3, fontsize=8.8)

    fig.suptitle("Composición de la superficie del lago en cada fecha",
                 fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout()
    guardar(fig, DIR_FIGURAS / "08_composicion_superficie.png")


def tabla_percentiles(escenas_por_lago: dict[str, list[Escena]]) -> pd.DataFrame:
    """Percentiles por fecha: la cola alta es la que define el riesgo sanitario."""
    filas = []
    for clave, escenas in escenas_por_lago.items():
        for escena in escenas:
            v = escena.valores
            filas.append(
                {
                    "lago": clave,
                    "fecha": escena.fecha,
                    "p10": float(np.percentile(v, 10)),
                    "p25": float(np.percentile(v, 25)),
                    "p50": float(np.percentile(v, 50)),
                    "p75": float(np.percentile(v, 75)),
                    "p90": float(np.percentile(v, 90)),
                    "p99": float(np.percentile(v, 99)),
                    "asimetria": float(
                        ((v - v.mean()) ** 3).mean() / max(v.std() ** 3, 1e-9)
                    ),
                }
            )
    return pd.DataFrame(filas)


def interpretar(serie: pd.DataFrame, percentiles: pd.DataFrame) -> str:
    """Redacta los hallazgos del análisis exploratorio."""
    lineas: list[str] = []

    for clave in LAGOS:
        nombre = LAGOS[clave]["nombre"]
        d = serie[serie["lago"] == clave]
        p = percentiles[percentiles["lago"] == clave]
        peor = d.loc[d["pct_area_alta"].idxmax()]
        asimetria_media = p["asimetria"].mean()

        if asimetria_media > 1:
            forma = (
                "Las distribuciones son marcadamente asimétricas hacia la derecha: la "
                "mayor parte del lago se mantiene en valores bajos y una minoría de la "
                "superficie concentra los valores altos. Por eso el promedio del lago "
                "subestima el riesgo local: puede haber zonas con floración fuerte "
                "aunque el promedio general parezca aceptable"
            )
        else:
            forma = (
                "Las distribuciones son relativamente simétricas, lo que indica que "
                "cuando el nivel sube, sube de forma bastante pareja en todo el lago"
            )

        lineas.append(
            f"**{nombre}.** La fecha con mayor extensión afectada fue {peor['fecha']}, "
            f"con el {pct(peor['pct_area_alta'])} de la superficie por encima del "
            f"umbral y un {pct(peor['pct_area_intensa'])} en floración intensa. "
            f"En una fecha típica, el 10 % más afectado del lago está por encima de "
            f"{p['p90'].median():.1f} µg/L, frente a una mediana general de "
            f"{p['p50'].median():.1f} µg/L. {forma}."
        )

    # Estacionalidad, con la salvedad honesta del tamaño de muestra.
    resumen_estacional = (
        serie.groupby(["lago", "estacion"])["chl_medio"].agg(["mean", "size"]).reset_index()
    )
    detalles = []
    for clave in LAGOS:
        sub = resumen_estacional[resumen_estacional["lago"] == clave]
        texto = " · ".join(
            f"{fila['estacion'].lower()}: {fila['mean']:.1f} µg/L (n={int(fila['size'])})"
            for _, fila in sub.iterrows()
        )
        detalles.append(f"{LAGOS[clave]['nombre'].replace('Lago de ', '')} → {texto}")

    lineas.append(
        "**Patrón estacional.** Promedios por estación: " + "; ".join(detalles) + ". "
        "La lectura debe hacerse con cautela: el calendario de imágenes disponibles no "
        "está repartido de forma pareja entre las dos estaciones, y varias fechas de la "
        "época lluviosa se pierden por nubosidad, que es precisamente el sesgo esperable "
        "en un monitoreo satelital de una región tropical. Cualquier conclusión "
        "estacional firme necesitaría una serie más larga y con cobertura equilibrada."
    )
    return "\n\n".join(lineas)


def ejecutar(
    escenas_por_lago: dict[str, list[Escena]], serie: pd.DataFrame
) -> pd.DataFrame:
    for clave, escenas in escenas_por_lago.items():
        figura_distribuciones(clave, escenas)
    figura_extension_por_categoria(serie)

    percentiles = tabla_percentiles(escenas_por_lago)
    percentiles.to_csv(DIR_TABLAS / "percentiles_por_fecha.csv", index=False)
    print("  tabla -> percentiles_por_fecha.csv")
    return percentiles
