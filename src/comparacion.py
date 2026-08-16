"""Ejercicio 7: análisis de cada lago y comparación entre ambos.

Compara la **intensidad** de las floraciones (qué tan altos llegan los valores)
y su **frecuencia** (en cuántas de las fechas observadas hay floración), y pone
esas diferencias en contexto con las características de cada cuenca.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.carga import UMBRAL_FLORACION, Escena
from src.config import DIR_FIGURAS, DIR_TABLAS, LAGOS
from src.estilo import COLOR_LAGO, MARCADOR_LAGO, TINTA_SEC, TINTA_TENUE, guardar
from src.formato import pct
from src.temporal import UMBRAL_INTENSO

# Contexto de cuenca. Son datos de referencia publicados sobre ambos lagos, no
# derivados de las imágenes; sirven para discutir *por qué* difieren los
# resultados, que es lo que pide el ejercicio 7.3.
CONTEXTO = {
    "Atitlan": {
        "area_km2": 130.1,
        "prof_max_m": 340,
        "altitud_msnm": 1562,
        "cuenca_km2": 541,
        "poblacion_cuenca": "~350 000 habitantes en 15 municipios",
        "drenaje": "endorreico (sin salida superficial)",
        "presion": (
            "aguas residuales de los municipios ribereños con tratamiento parcial, "
            "agricultura en laderas empinadas y arrastre de ceniza volcánica"
        ),
    },
    "Amatitlan": {
        "area_km2": 15.2,
        "prof_max_m": 33,
        "altitud_msnm": 1186,
        "cuenca_km2": 381,
        "poblacion_cuenca": "más de 1 500 000 habitantes, incluida parte de la capital",
        "drenaje": "río Villalobos como afluente principal y río Michatoya como salida",
        "presion": (
            "descarga del río Villalobos, que concentra aguas residuales domésticas e "
            "industriales del área metropolitana de Guatemala, más residuos sólidos"
        ),
    },
}


def resumen_por_lago(serie: pd.DataFrame) -> pd.DataFrame:
    """Una fila por lago con las métricas de intensidad y frecuencia."""
    filas = []
    for clave in LAGOS:
        d = serie[serie["lago"] == clave]
        n = len(d)
        filas.append(
            {
                "lago": clave,
                "nombre": LAGOS[clave]["nombre"],
                "n_fechas": n,
                # Intensidad
                "chl_medio": d["chl_medio"].mean(),
                "chl_mediana": d["chl_mediana"].median(),
                "chl_pico": d["chl_medio"].max(),
                "chl_p90_tipico": d["chl_p90"].median(),
                # Frecuencia
                "fechas_con_floracion": int((d["chl_medio"] >= UMBRAL_FLORACION).sum()),
                "frec_floracion_pct": 100 * (d["chl_medio"] >= UMBRAL_FLORACION).mean(),
                "fechas_intensas": int((d["chl_medio"] >= UMBRAL_INTENSO).sum()),
                # Extensión
                "pct_area_alta_media": d["pct_area_alta"].mean(),
                "pct_area_alta_max": d["pct_area_alta"].max(),
                "pct_area_intensa_max": d["pct_area_intensa"].max(),
                # Variabilidad
                "desv_std": d["chl_medio"].std(ddof=0),
                "coef_variacion": d["chl_medio"].std(ddof=0) / max(d["chl_medio"].mean(), 1e-9),
                "area_agua_km2": d["area_agua_km2"].median(),
            }
        )
    return pd.DataFrame(filas)


def prueba_diferencia(serie: pd.DataFrame) -> dict:
    """Compara los dos lagos con una prueba no paramétrica.

    Se usa Mann-Whitney porque son 11 observaciones por lago, sin garantía de
    normalidad y con posibles valores extremos; una prueba t sería frágil aquí.
    """
    a = serie[serie["lago"] == "Atitlan"]["chl_medio"].to_numpy()
    b = serie[serie["lago"] == "Amatitlan"]["chl_medio"].to_numpy()
    resultado = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {
        "u": float(resultado.statistic),
        "p": float(resultado.pvalue),
        "mediana_atitlan": float(np.median(a)),
        "mediana_amatitlan": float(np.median(b)),
        "razon": float(np.median(b) / max(np.median(a), 1e-9)),
    }


def figura_comparativa(serie: pd.DataFrame, resumen: pd.DataFrame) -> None:
    """Tres vistas de la misma comparación: nivel típico, evolución y extensión."""
    fig = plt.figure(figsize=(11.5, 8.2))
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.42, wspace=0.28)

    # (a) Distribución del índice promedio en las 11 fechas de cada lago.
    eje_a = fig.add_subplot(grid[0, 0])
    grupos = [serie[serie["lago"] == c]["chl_medio"].to_numpy() for c in LAGOS]
    etiquetas = [LAGOS[c]["nombre"].replace("Lago de ", "") for c in LAGOS]
    caja = eje_a.boxplot(grupos, tick_labels=etiquetas, widths=0.45, patch_artist=True,
                         medianprops={"color": "white", "linewidth": 2})
    for parche, clave in zip(caja["boxes"], LAGOS):
        parche.set(facecolor=COLOR_LAGO[clave], alpha=0.75, edgecolor="none")
    for elemento in ("whiskers", "caps"):
        for linea in caja[elemento]:
            linea.set(color=TINTA_SEC, linewidth=1)
    for i, (valores, clave) in enumerate(zip(grupos, LAGOS), start=1):
        jitter = np.random.default_rng(11).normal(0, 0.05, len(valores))
        eje_a.scatter(i + jitter, valores, s=30, color=TINTA_SEC, alpha=0.8, zorder=3)
    eje_a.axhline(UMBRAL_FLORACION, color="#d03b3b", linewidth=1.2, linestyle=(0, (4, 3)))
    eje_a.set_ylabel("Clorofila-a promedio (µg/L)")
    eje_a.set_title("Intensidad típica por lago", fontsize=11)
    eje_a.grid(axis="x", visible=False)

    # (b) Ambas series en el mismo eje temporal.
    eje_b = fig.add_subplot(grid[0, 1])
    for clave in LAGOS:
        d = serie[serie["lago"] == clave]
        eje_b.plot(d["fecha_dt"], d["chl_medio"], color=COLOR_LAGO[clave],
                   marker=MARCADOR_LAGO[clave], markerfacecolor="white",
                   markeredgewidth=1.6, label=LAGOS[clave]["nombre"])
    eje_b.axhline(UMBRAL_FLORACION, color="#d03b3b", linewidth=1.2, linestyle=(0, (4, 3)))
    eje_b.set_ylabel("Clorofila-a promedio (µg/L)")
    eje_b.set_title("Evolución comparada", fontsize=11)
    eje_b.legend(loc="best")
    eje_b.tick_params(axis="x", labelrotation=30)

    # (c) Frecuencia de floración.
    eje_c = fig.add_subplot(grid[1, 0])
    y = np.arange(len(resumen))
    barras = eje_c.barh(y, resumen["frec_floracion_pct"], height=0.5,
                        color=[COLOR_LAGO[c] for c in resumen["lago"]])
    for barra, fila in zip(barras, resumen.itertuples()):
        eje_c.text(barra.get_width() + 2, barra.get_y() + barra.get_height() / 2,
                   f"{fila.fechas_con_floracion} de {fila.n_fechas} fechas",
                   va="center", fontsize=9.5, color=TINTA_SEC)
    eje_c.set_yticks(y, [n.replace("Lago de ", "") for n in resumen["nombre"]])
    eje_c.set_xlabel(f"% de fechas con promedio sobre {UMBRAL_FLORACION:.0f} µg/L")
    eje_c.set_xlim(0, 118)
    eje_c.set_title("Frecuencia de floración", fontsize=11)
    eje_c.grid(axis="y", visible=False)

    # (d) Extensión media y máxima de la superficie afectada.
    eje_d = fig.add_subplot(grid[1, 1])
    ancho = 0.35
    x = np.arange(len(resumen))
    eje_d.bar(x - ancho / 2, resumen["pct_area_alta_media"], ancho,
              color=[COLOR_LAGO[c] for c in resumen["lago"]], alpha=0.55, label="media")
    eje_d.bar(x + ancho / 2, resumen["pct_area_alta_max"], ancho,
              color=[COLOR_LAGO[c] for c in resumen["lago"]], label="máximo")
    for xi, fila in zip(x, resumen.itertuples()):
        eje_d.text(xi - ancho / 2, fila.pct_area_alta_media + 2,
                   f"{fila.pct_area_alta_media:.0f}%", ha="center", fontsize=9, color=TINTA_SEC)
        eje_d.text(xi + ancho / 2, fila.pct_area_alta_max + 2,
                   f"{fila.pct_area_alta_max:.0f}%", ha="center", fontsize=9, color=TINTA_SEC)
    eje_d.set_xticks(x, [n.replace("Lago de ", "") for n in resumen["nombre"]])
    eje_d.set_ylabel("% del espejo de agua")
    eje_d.set_ylim(0, 112)
    eje_d.set_title("Extensión de la superficie afectada", fontsize=11)
    eje_d.legend(loc="upper left")
    eje_d.grid(axis="x", visible=False)
    eje_d.text(0.99, 0.92, "barra clara = promedio · barra sólida = peor fecha",
               transform=eje_d.transAxes, ha="right", fontsize=8.5, color=TINTA_TENUE)

    fig.suptitle("Atitlán frente a Amatitlán: intensidad, frecuencia y extensión",
                 fontsize=13.5, fontweight="bold", y=0.98)
    guardar(fig, DIR_FIGURAS / "07_comparacion_lagos.png")


def interpretar(resumen: pd.DataFrame, prueba: dict, serie: pd.DataFrame) -> str:
    """Redacta la comparación con los números reales y el contexto de cuenca."""
    r = resumen.set_index("lago")
    at, am = r.loc["Atitlan"], r.loc["Amatitlan"]

    if prueba["p"] < 0.05:
        veredicto = (
            f"La diferencia entre ambos lagos es estadísticamente significativa "
            f"(prueba de Mann-Whitney, p = {prueba['p']:.4f})"
        )
    else:
        veredicto = (
            f"Con solo {int(at['n_fechas'])} y {int(am['n_fechas'])} fechas por lago, la "
            f"diferencia no alcanza significancia estadística formal "
            f"(prueba de Mann-Whitney, p = {prueba['p']:.3f}), aunque la brecha en los "
            f"valores típicos es clara"
        )

    mas_afectado = "Amatitlán" if am["chl_medio"] > at["chl_medio"] else "Atitlán"

    partes = [
        f"**Intensidad.** El promedio de clorofila-a en el período estudiado es de "
        f"{at['chl_medio']:.1f} µg/L en Atitlán y {am['chl_medio']:.1f} µg/L en "
        f"Amatitlán, es decir, {mas_afectado} presenta el nivel de base más alto. "
        f"El pico más alto registrado fue de {at['chl_pico']:.1f} µg/L en Atitlán y "
        f"{am['chl_pico']:.1f} µg/L en Amatitlán. {veredicto}.",

        f"**Frecuencia.** Atitlán superó el umbral de floración en "
        f"{int(at['fechas_con_floracion'])} de {int(at['n_fechas'])} fechas "
        f"({at['frec_floracion_pct']:.0f} %) y Amatitlán en "
        f"{int(am['fechas_con_floracion'])} de {int(am['n_fechas'])} "
        f"({am['frec_floracion_pct']:.0f} %). Conviene matizar esta cifra: el promedio "
        f"de todo el lago es una medida exigente, porque una bahía en floración pesa "
        f"poco frente al resto del espejo de agua. Mirando la floración intensa "
        f"(más de {UMBRAL_INTENSO:.0f} µg/L) por superficie y no por promedio, Atitlán "
        f"llegó como máximo a un {pct(at['pct_area_intensa_max'])} del lago afectado en "
        f"una misma fecha y Amatitlán a un {pct(am['pct_area_intensa_max'])}.",

        f"**Extensión.** En una fecha típica, el {at['pct_area_alta_media']:.0f} % de la "
        f"superficie de Atitlán y el {am['pct_area_alta_media']:.0f} % de la de Amatitlán "
        f"están por encima del umbral; en la peor fecha de cada lago esas cifras suben a "
        f"{at['pct_area_alta_max']:.0f} % y {am['pct_area_alta_max']:.0f} %.",

        f"**Estabilidad.** El coeficiente de variación es de {at['coef_variacion']:.2f} en "
        f"Atitlán y {am['coef_variacion']:.2f} en Amatitlán: cuanto más alto, más "
        f"cambia el lago de una fecha a otra, es decir, más episódico y menos "
        f"predecible es el fenómeno.",
    ]

    # Discusión de causas (7.3), anclada en las diferencias físicas de cada cuenca.
    ca, cm = CONTEXTO["Atitlan"], CONTEXTO["Amatitlan"]
    partes.append(
        f"**Por qué difieren.** Los dos lagos no son comparables en escala física. "
        f"Atitlán tiene {ca['area_km2']:.0f} km² de superficie y hasta "
        f"{ca['prof_max_m']} m de profundidad, mientras que Amatitlán tiene apenas "
        f"{cm['area_km2']:.0f} km² y {cm['prof_max_m']} m de profundidad máxima. "
        f"Un lago somero y pequeño se calienta más, mezcla los nutrientes del fondo con "
        f"más facilidad y diluye mucho menos lo que recibe: la misma carga de nutrientes "
        f"produce concentraciones mucho mayores. A eso se suma la presión de la cuenca: "
        f"la de Amatitlán ({cm['cuenca_km2']} km²) alberga {cm['poblacion_cuenca']} y "
        f"recibe {cm['presion']}; la de Atitlán ({ca['cuenca_km2']} km²) alberga "
        f"{ca['poblacion_cuenca']} y su presión principal es {ca['presion']}. "
        f"Además, Atitlán es {ca['drenaje']}, de modo que los nutrientes que entran no "
        f"tienen salida y se acumulan a lo largo de los años, lo que explica que allí "
        f"el problema se manifieste como episodios grandes y ocasionales más que como "
        f"un estado permanente."
    )
    return "\n\n".join(partes)


def ejecutar(serie: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    resumen = resumen_por_lago(serie)
    prueba = prueba_diferencia(serie)
    resumen.to_csv(DIR_TABLAS / "comparacion_lagos.csv", index=False)
    print("  tabla -> comparacion_lagos.csv")
    figura_comparativa(serie, resumen)
    return resumen, prueba
