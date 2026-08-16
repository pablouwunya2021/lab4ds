"""Lectura y limpieza de los rásters descargados.

Convierte cada GeoTIFF en un diccionario de arreglos enmascarados, dejando
únicamente los píxeles que representan agua del lago con observación válida
(sin nubes, sin sombras de nube y dentro del polígono del cuerpo de agua).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask

from src.config import FECHAS, LAGOS
from src.descarga import ruta_indices
from src.evalscripts import BANDAS_INDICES, CLP_MAXIMO

# Tratamiento de los valores fuera de rango del polinomio de clorofila-a.
#
# En agua muy limpia el NDCI se vuelve negativo y el polinomio devuelve valores
# negativos, que físicamente no existen. Esos píxeles NO se descartan: se
# recortan a cero, porque un negativo significa "clorofila por debajo del
# límite de detección", no "dato inválido". Descartarlos sesgaría el promedio
# hacia arriba justo en los lagos y las fechas más limpios, que es exactamente
# donde el sesgo cambiaría las conclusiones.
#
# Por arriba sí se descarta: por encima de este valor el ajuste ya no es
# fiable y suele corresponder a píxeles de orilla o a reflejos especulares.
CHL_MIN, CHL_MAX = 0.0, 300.0

# Umbral de floración. El script de CyanoLakes cambia a tonos verdes brillantes
# a partir de ~10 ug/L; la OMS ubica ahí el inicio del riesgo recreativo bajo
# por cianobacterias, así que se usa como corte de "valor alto".
UMBRAL_FLORACION = 10.0


@dataclass
class Escena:
    """Una fecha de un lago, ya limpia y lista para analizar."""

    lago: str
    fecha: str
    chl: np.ndarray       # clorofila-a (ug/L), NaN fuera del agua válida
    ndci: np.ndarray
    ndvi: np.ndarray
    ndwi: np.ndarray
    fai: np.ndarray
    mascara: np.ndarray   # True = píxel de agua válido
    transform: object
    crs: object
    forma: tuple[int, int]

    @property
    def n_validos(self) -> int:
        return int(self.mascara.sum())

    @property
    def cobertura(self) -> float:
        """Fracción del polígono del lago efectivamente observada."""
        return self.n_validos / max(mascara_lago(self.lago).sum(), 1)

    @property
    def valores(self) -> np.ndarray:
        """Vector 1-D de clorofila-a solo en los píxeles válidos."""
        return self.chl[self.mascara]


def _rutas_disponibles(clave_lago: str) -> list:
    rutas = [
        ruta_indices(clave_lago, fecha)
        for fecha, _nub, _sat in FECHAS[clave_lago]
        if ruta_indices(clave_lago, fecha).exists()
    ]
    if not rutas:
        raise FileNotFoundError(
            f"No hay ningún ráster de {clave_lago}. Corré primero: python -m src.descarga"
        )
    return rutas


@lru_cache(maxsize=4)
def mascara_area_interes(clave_lago: str) -> np.ndarray:
    """Rectángulo del área de interés del enunciado, rasterizado a la grilla.

    El geojson provisto es el bounding box, no la orilla del lago, así que por
    sí solo no recorta el agua: solo garantiza que no se analice nada fuera del
    área declarada.
    """
    with rasterio.open(_rutas_disponibles(clave_lago)[0]) as src:
        forma, transform, crs = (src.height, src.width), src.transform, src.crs

    gdf = gpd.read_file(LAGOS[clave_lago]["geojson"]).to_crs(crs)
    return geometry_mask(gdf.geometry, out_shape=forma, transform=transform, invert=True)


@lru_cache(maxsize=4)
def mascara_lago(clave_lago: str) -> np.ndarray:
    """Espejo de agua estable del lago: el dominio común a todas las fechas.

    Se define como el conjunto de píxeles que el detector de agua del script
    clasifica como agua en al menos la mitad de las fechas disponibles. Fijar
    un dominio único es importante: si cada fecha se analizara sobre los
    píxeles que ella misma detecta como agua, los promedios y los mapas de
    diferencia entre fechas estarían comparando superficies distintas, y una
    variación del contorno del lago se confundiría con un cambio en la
    floración.
    """
    rutas = _rutas_disponibles(clave_lago)
    conteo = None
    for ruta in rutas:
        with rasterio.open(ruta) as src:
            agua = (src.read(BANDAS_INDICES["agua"]) > 0.5) & (
                src.read(BANDAS_INDICES["datamask"]) > 0
            )
        conteo = agua.astype("int32") if conteo is None else conteo + agua
    return (conteo >= len(rutas) / 2) & mascara_area_interes(clave_lago)


def cargar_escena(clave_lago: str, fecha: str) -> Escena | None:
    """Lee un GeoTIFF de índices y devuelve la escena limpia, o None si falta."""
    ruta = ruta_indices(clave_lago, fecha)
    if not ruta.exists():
        return None

    with rasterio.open(ruta) as src:
        bandas = {n: src.read(i).astype("float64") for n, i in BANDAS_INDICES.items()}
        transform, crs, forma = src.transform, src.crs, (src.height, src.width)

    # Cadena de filtros: espejo de agua estable -> dato válido -> sin nube ->
    # valor físicamente plausible.
    valido = bandas["datamask"] > 0
    sin_nube = bandas["clp"] <= CLP_MAXIMO
    chl = np.clip(bandas["chl"], CHL_MIN, None)
    rango = np.isfinite(chl) & (chl <= CHL_MAX)

    mascara = mascara_lago(clave_lago) & valido & sin_nube & rango

    def enmascarar(arr: np.ndarray) -> np.ndarray:
        salida = np.full_like(arr, np.nan, dtype="float64")
        salida[mascara] = arr[mascara]
        return salida

    return Escena(
        lago=clave_lago,
        fecha=fecha,
        chl=enmascarar(chl),
        ndci=enmascarar(bandas["ndci"]),
        ndvi=enmascarar(bandas["ndvi"]),
        ndwi=enmascarar(bandas["ndwi"]),
        fai=enmascarar(bandas["fai"]),
        mascara=mascara,
        transform=transform,
        crs=crs,
        forma=forma,
    )


def cargar_lago(clave_lago: str, cobertura_minima: float = 0.10) -> list[Escena]:
    """Todas las escenas utilizables de un lago, en orden cronológico.

    Se descartan las fechas donde queda muy poca superficie de agua observable
    (por nubosidad), porque un promedio calculado sobre un puñado de píxeles no
    es representativo del lago.
    """
    escenas = []
    for fecha, _nub, _sat in FECHAS[clave_lago]:
        escena = cargar_escena(clave_lago, fecha)
        if escena is None:
            print(f"  aviso: falta el ráster de {clave_lago} {fecha}")
            continue
        if escena.cobertura < cobertura_minima:
            print(
                f"  aviso: {clave_lago} {fecha} descartada "
                f"(solo {escena.cobertura:.1%} del área observable)"
            )
            continue
        escenas.append(escena)
    return sorted(escenas, key=lambda e: e.fecha)
