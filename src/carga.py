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
from src.evalscripts import BANDAS_INDICES, SCL_DESCARTAR

# Valores de clorofila-a fuera de este rango se consideran artefactos del
# ajuste polinómico (el NDCI satura en píxeles de orilla y en reflejos).
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


@lru_cache(maxsize=4)
def mascara_lago(clave_lago: str) -> np.ndarray:
    """Máscara del polígono del lago rasterizada sobre la grilla de trabajo.

    El geojson del enunciado es el rectángulo del área de interés, así que por
    sí solo no recorta el agua. La delimitación fina del cuerpo de agua la hace
    la máscara espectral del script (banda `agua`); esta función solo asegura
    que no se analice nada fuera del área de interés declarada.
    """
    fecha_ref = FECHAS[clave_lago][0][0]
    with rasterio.open(ruta_indices(clave_lago, fecha_ref)) as src:
        forma = (src.height, src.width)
        transform = src.transform
        crs = src.crs

    gdf = gpd.read_file(LAGOS[clave_lago]["geojson"]).to_crs(crs)
    dentro = geometry_mask(
        gdf.geometry, out_shape=forma, transform=transform, invert=True
    )
    return dentro


def cargar_escena(clave_lago: str, fecha: str) -> Escena | None:
    """Lee un GeoTIFF de índices y devuelve la escena limpia, o None si falta."""
    ruta = ruta_indices(clave_lago, fecha)
    if not ruta.exists():
        return None

    with rasterio.open(ruta) as src:
        bandas = {n: src.read(i).astype("float64") for n, i in BANDAS_INDICES.items()}
        transform, crs, forma = src.transform, src.crs, (src.height, src.width)

    # Cadena de filtros: dato válido -> agua -> sin nube/sombra -> rango físico.
    valido = bandas["datamask"] > 0
    agua = bandas["agua"] > 0.5
    sin_nube = ~np.isin(np.rint(bandas["scl"]).astype(int), list(SCL_DESCARTAR))
    chl = bandas["chl"]
    rango = np.isfinite(chl) & (chl >= CHL_MIN) & (chl <= CHL_MAX)

    mascara = valido & agua & sin_nube & rango & mascara_lago(clave_lago)

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
