"""Ejercicio 5 (y parte del 8): análisis espacial y mapas.

Produce mapas estáticos de la distribución de cianobacteria dentro de cada lago,
mapas comparativos entre fechas, mapas de diferencia, un mapa de persistencia de
las zonas de acumulación y un mapa interactivo en folium.
"""

from __future__ import annotations

import base64
import io

import folium
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from branca.colormap import LinearColormap
from matplotlib import colors as mcolors
from rasterio.warp import Resampling, calculate_default_transform, reproject

from src.carga import UMBRAL_FLORACION, Escena
from src.config import DIR_FIGURAS, DIR_MAPAS, LAGOS, RESOLUCION_M
from src.estilo import (
    CMAP_CHL,
    CMAP_DIF,
    COLOR_TIERRA,
    TINTA_SEC,
    TINTA_TENUE,
    guardar,
    norma_divergente,
)

# Escala fija de color para todos los mapas de un mismo lago: si cada mapa usara
# su propia escala, dos fechas distintas se verían igual de "rojas" aunque una
# tuviera el triple de clorofila, y la comparación visual sería engañosa.
ESCALA_CHL = (0.0, 40.0)


def _a_wgs84(arreglo: np.ndarray, transform, crs):
    """Reproyecta un arreglo a coordenadas geográficas para superponerlo en folium."""
    alto, ancho = arreglo.shape
    dst_crs = "EPSG:4326"
    dst_transform, dst_ancho, dst_alto = calculate_default_transform(
        crs, dst_crs, ancho, alto, *rasterio.transform.array_bounds(alto, ancho, transform)[:4]
    )
    destino = np.full((dst_alto, dst_ancho), np.nan, dtype="float64")
    reproject(
        source=arreglo,
        destination=destino,
        src_transform=transform,
        src_crs=crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    oeste, sur, este, norte = rasterio.transform.array_bounds(
        dst_alto, dst_ancho, dst_transform
    )
    return destino, [[sur, oeste], [norte, este]]


def _pintar(eje, datos: np.ndarray, cmap, norm, titulo: str):
    """Dibuja una capa sobre un fondo gris que representa la tierra circundante."""
    eje.imshow(np.ones_like(datos), cmap=mcolors.ListedColormap([COLOR_TIERRA]))
    imagen = eje.imshow(np.ma.masked_invalid(datos), cmap=cmap, norm=norm)
    eje.set_title(titulo, fontsize=10.5, pad=6)
    eje.set_xticks([])
    eje.set_yticks([])
    eje.grid(False)
    for spine in eje.spines.values():
        spine.set_visible(False)
    return imagen


def mapas_todas_las_fechas(clave_lago: str, escenas: list[Escena]) -> None:
    """Panel con la distribución de cianobacteria en cada fecha disponible."""
    n = len(escenas)
    columnas = min(4, n)
    filas = int(np.ceil(n / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(3.1 * columnas, 3.35 * filas))
    ejes = np.atleast_1d(ejes).ravel()

    norm = mcolors.Normalize(*ESCALA_CHL)
    imagen = None
    for eje, escena in zip(ejes, escenas):
        media = float(np.nanmean(escena.chl))
        imagen = _pintar(eje, escena.chl, CMAP_CHL, norm, f"{escena.fecha}\nmedia {media:.1f} µg/L")
    for eje in ejes[n:]:
        eje.axis("off")

    fig.suptitle(
        f"{LAGOS[clave_lago]['nombre']} — clorofila-a por fecha",
        fontsize=13, fontweight="bold", y=0.995,
    )
    barra = fig.colorbar(
        imagen, ax=ejes.tolist(), orientation="horizontal",
        fraction=0.04, pad=0.04, extend="max",
    )
    barra.set_label("Clorofila-a (µg/L) — más oscuro = más floración", color=TINTA_SEC)
    barra.outline.set_visible(False)
    guardar(fig, DIR_FIGURAS / f"05_mapas_por_fecha_{clave_lago}.png")


def mapa_comparativo(clave_lago: str, escenas: list[Escena]) -> tuple[str, str]:
    """Compara la fecha más limpia con la más afectada y muestra la diferencia."""
    medias = [float(np.nanmean(e.chl)) for e in escenas]
    peor = escenas[int(np.argmax(medias))]
    mejor = escenas[int(np.argmin(medias))]

    diferencia = peor.chl - mejor.chl
    finitos = diferencia[np.isfinite(diferencia)]
    limite = float(np.percentile(np.abs(finitos), 98)) if finitos.size else 1.0

    fig, ejes = plt.subplots(1, 3, figsize=(12.5, 4.5))
    norm = mcolors.Normalize(*ESCALA_CHL)

    im0 = _pintar(ejes[0], mejor.chl, CMAP_CHL, norm,
                  f"Fecha más limpia\n{mejor.fecha} · media {min(medias):.1f} µg/L")
    _pintar(ejes[1], peor.chl, CMAP_CHL, norm,
            f"Fecha más afectada\n{peor.fecha} · media {max(medias):.1f} µg/L")
    im2 = _pintar(ejes[2], diferencia, CMAP_DIF, norma_divergente(-limite, limite),
                  "Diferencia\n(afectada − limpia)")

    barra0 = fig.colorbar(im0, ax=ejes[:2].tolist(), orientation="horizontal",
                          fraction=0.05, pad=0.06, extend="max")
    barra0.set_label("Clorofila-a (µg/L)", color=TINTA_SEC)
    barra0.outline.set_visible(False)

    barra2 = fig.colorbar(im2, ax=ejes[2], orientation="horizontal",
                          fraction=0.05, pad=0.06, extend="both")
    barra2.set_label("Cambio (µg/L): rojo = aumentó · azul = disminuyó", color=TINTA_SEC)
    barra2.outline.set_visible(False)

    fig.suptitle(f"{LAGOS[clave_lago]['nombre']} — comparación entre fechas",
                 fontsize=13, fontweight="bold", y=1.0)
    guardar(fig, DIR_FIGURAS / f"05_comparacion_fechas_{clave_lago}.png")
    return mejor.fecha, peor.fecha


def mapa_persistencia(clave_lago: str, escenas: list[Escena]) -> np.ndarray:
    """Frecuencia con que cada punto del lago supera el umbral de floración.

    Un punto que aparece alto en casi todas las fechas es una zona persistente
    de acumulación, y suele delatar una fuente continua de nutrientes o una
    zona de poca circulación, no un evento aislado.
    """
    apilado_alto = np.stack(
        [np.where(e.mascara, (e.chl >= UMBRAL_FLORACION).astype(float), np.nan)
         for e in escenas]
    )
    frecuencia = 100 * np.nanmean(apilado_alto, axis=0)

    apilado_chl = np.stack([e.chl for e in escenas])
    promedio = np.nanmean(apilado_chl, axis=0)

    fig, ejes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    im0 = _pintar(ejes[0], promedio, CMAP_CHL, mcolors.Normalize(*ESCALA_CHL),
                  "Promedio de todo el período")
    im1 = _pintar(ejes[1], frecuencia, CMAP_CHL, mcolors.Normalize(0, 100),
                  f"Persistencia: % de fechas sobre {UMBRAL_FLORACION:.0f} µg/L")

    for imagen, eje, etiqueta in (
        (im0, ejes[0], "Clorofila-a promedio (µg/L)"),
        (im1, ejes[1], "% de las fechas observadas"),
    ):
        barra = fig.colorbar(imagen, ax=eje, orientation="horizontal",
                             fraction=0.05, pad=0.05)
        barra.set_label(etiqueta, color=TINTA_SEC, fontsize=9)
        barra.outline.set_visible(False)

    fig.suptitle(
        f"{LAGOS[clave_lago]['nombre']} — zonas persistentes de acumulación "
        f"({len(escenas)} fechas)",
        fontsize=13, fontweight="bold", y=1.0,
    )
    guardar(fig, DIR_FIGURAS / f"08_persistencia_{clave_lago}.png")
    return frecuencia


def mapa_interactivo(clave_lago: str, escenas: list[Escena], frecuencia: np.ndarray) -> None:
    """Mapa folium con una capa por fecha más la capa de persistencia."""
    oeste, sur, este, norte = LAGOS[clave_lago]["bbox"]
    centro = [(sur + norte) / 2, (oeste + este) / 2]

    mapa = folium.Map(location=centro, zoom_start=12, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Mapa base", control=True).add_to(mapa)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satélite", control=True,
    ).add_to(mapa)

    norm = mcolors.Normalize(*ESCALA_CHL)

    def capa(datos, transform, crs, nombre, cmap, normalizacion, visible):
        reproyectado, limites = _a_wgs84(datos, transform, crs)
        rgba = cmap(normalizacion(reproyectado))
        rgba[..., 3] = np.where(np.isfinite(reproyectado), 0.85, 0.0)

        buffer = io.BytesIO()
        plt.imsave(buffer, rgba, format="png")
        uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

        folium.raster_layers.ImageOverlay(
            image=uri, bounds=limites, name=nombre, opacity=1.0, show=visible
        ).add_to(mapa)

    for i, escena in enumerate(escenas):
        media = float(np.nanmean(escena.chl))
        capa(escena.chl, escena.transform, escena.crs,
             f"{escena.fecha} (media {media:.1f} µg/L)", CMAP_CHL, norm,
             visible=(i == len(escenas) - 1))

    ref = escenas[0]
    capa(frecuencia, ref.transform, ref.crs,
         f"Persistencia (% de fechas > {UMBRAL_FLORACION:.0f} µg/L)",
         CMAP_CHL, mcolors.Normalize(0, 100), visible=False)

    escala = LinearColormap(
        colors=[mcolors.to_hex(CMAP_CHL(x)) for x in np.linspace(0, 1, 8)],
        vmin=ESCALA_CHL[0], vmax=ESCALA_CHL[1],
        caption="Clorofila-a (µg/L) — indicador de cianobacteria",
    )
    escala.add_to(mapa)

    folium.GeoJson(
        str(LAGOS[clave_lago]["geojson"]),
        name="Área de interés",
        style_function=lambda _: {"color": "#0b0b0b", "weight": 1.5,
                                  "fillOpacity": 0, "dashArray": "5,4"},
    ).add_to(mapa)
    folium.LayerControl(collapsed=False).add_to(mapa)

    destino = DIR_MAPAS / f"mapa_interactivo_{clave_lago}.html"
    mapa.save(str(destino))
    print(f"  mapa -> {destino.name}")


def interpretar(clave_lago: str, escenas: list[Escena], frecuencia: np.ndarray) -> str:
    """Describe dónde se concentra la floración y cuánto se mueve entre fechas."""
    nombre = LAGOS[clave_lago]["nombre"]
    validos = np.isfinite(frecuencia) & (frecuencia >= 0)
    area_pixel_km2 = (RESOLUCION_M**2) / 1e6

    persistente = (frecuencia >= 50) & validos
    ocasional = (frecuencia > 0) & (frecuencia < 50) & validos
    nunca = (frecuencia == 0) & validos

    # ¿La zona afectada es siempre la misma o se mueve? Se compara la mitad
    # norte con la sur del área observada como referencia gruesa de ubicación.
    filas = np.where(validos.any(axis=1))[0]
    if filas.size:
        corte = (filas.min() + filas.max()) // 2
        norte_media = np.nanmean(frecuencia[: corte + 1][validos[: corte + 1]])
        sur_media = np.nanmean(frecuencia[corte + 1 :][validos[corte + 1 :]])
        if abs(norte_media - sur_media) < 5:
            reparto = "la afectación se reparte de forma pareja entre el norte y el sur del lago"
        elif norte_media > sur_media:
            reparto = (
                f"la mitad norte está más afectada que la sur "
                f"({norte_media:.0f} % frente a {sur_media:.0f} % de las fechas)"
            )
        else:
            reparto = (
                f"la mitad sur está más afectada que la norte "
                f"({sur_media:.0f} % frente a {norte_media:.0f} % de las fechas)"
            )
    else:
        reparto = "no hay superficie suficiente para comparar zonas"

    return (
        f"**{nombre}.** Sobre {int(validos.sum()) * area_pixel_km2:.1f} km² de espejo de agua "
        f"analizados, el {100 * persistente.sum() / max(validos.sum(), 1):.1f} % de la "
        f"superficie supera el umbral de floración en al menos la mitad de las fechas "
        f"(zonas persistentes de acumulación), el "
        f"{100 * ocasional.sum() / max(validos.sum(), 1):.1f} % lo supera solo de forma "
        f"ocasional y el {100 * nunca.sum() / max(validos.sum(), 1):.1f} % nunca lo supera. "
        f"Espacialmente, {reparto}."
    )


def ejecutar(escenas_por_lago: dict[str, list[Escena]]) -> dict[str, np.ndarray]:
    """Corre el ejercicio 5 completo y devuelve los mapas de persistencia."""
    persistencias = {}
    for clave, escenas in escenas_por_lago.items():
        print(f"  {LAGOS[clave]['nombre']}")
        mapas_todas_las_fechas(clave, escenas)
        mapa_comparativo(clave, escenas)
        frecuencia = mapa_persistencia(clave, escenas)
        mapa_interactivo(clave, escenas, frecuencia)
        persistencias[clave] = frecuencia
    return persistencias
