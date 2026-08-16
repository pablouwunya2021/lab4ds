"""Ejercicios 1–3: conexión al API de Sentinel-2 y descarga de los rásters.

Para cada lago y cada fecha oficial del enunciado se hace **una sola petición**
a Sentinel Hub que devuelve directamente los índices ya calculados en la nube
(clorofila-a de cianobacteria, NDCI, NDVI, NDWI, FAI y máscara de agua). Así se
descarga únicamente lo necesario para el análisis y no escenas completas.

Uso:
    python -m src.descarga              # descarga todo lo que falte
    python -m src.descarga --probar     # solo verifica la autenticación
    python -m src.descarga --forzar     # vuelve a descargar todo
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from sentinelhub import (
    CRS,
    BBox,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)

from src.config import (
    DIR_RAW,
    FECHAS,
    LAGOS,
    RESOLUCION_M,
    SENTINEL2_L2A_CDSE,
    obtener_config,
)
from src.evalscripts import (
    EVALSCRIPT_CYANO_RGB,
    EVALSCRIPT_INDICES,
    EVALSCRIPT_RGB,
)

# Ambos lagos caen en la zona UTM 15 norte. Trabajar en metros hace que la
# resolución de 20 m sea real y que las áreas se puedan calcular directamente.
CRS_TRABAJO = CRS("32615")

NOMBRES_BANDAS = ["chl", "ndci", "ndvi", "ndwi", "fai", "agua", "scl", "datamask"]


def bbox_lago(clave_lago: str) -> BBox:
    """BBox del lago reproyectado a UTM 15N."""
    oeste, sur, este, norte = LAGOS[clave_lago]["bbox"]
    return BBox((oeste, sur, este, norte), crs=CRS.WGS84).transform(CRS_TRABAJO)


def _pedir(evalscript: str, bbox: BBox, tamano, fecha: str, config, mime):
    """Arma y ejecuta una petición de tipo Process API a Sentinel Hub."""
    # Ventana de un día: se pide exactamente la escena de la fecha indicada.
    dia = date.fromisoformat(fecha)
    intervalo = (dia.isoformat(), (dia + timedelta(days=1)).isoformat())

    peticion = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=SENTINEL2_L2A_CDSE,
                time_interval=intervalo,
                mosaicking_order="leastCC",
            )
        ],
        responses=[SentinelHubRequest.output_response("default", mime)],
        bbox=bbox,
        size=tamano,
        config=config,
    )
    return peticion.get_data()[0]


def _guardar_geotiff(arreglo: np.ndarray, bbox: BBox, destino: Path) -> None:
    """Escribe el arreglo (alto, ancho, bandas) como GeoTIFF georreferenciado."""
    if arreglo.ndim == 2:
        arreglo = arreglo[:, :, np.newaxis]
    alto, ancho, n_bandas = arreglo.shape
    transform = from_bounds(*bbox, ancho, alto)

    with rasterio.open(
        destino,
        "w",
        driver="GTiff",
        height=alto,
        width=ancho,
        count=n_bandas,
        dtype=arreglo.dtype,
        crs=str(bbox.crs.ogc_string()),
        transform=transform,
        compress="deflate",
    ) as dst:
        for i in range(n_bandas):
            dst.write(arreglo[:, :, i], i + 1)
            if n_bandas == len(NOMBRES_BANDAS):
                dst.set_band_description(i + 1, NOMBRES_BANDAS[i])


def ruta_indices(clave_lago: str, fecha: str) -> Path:
    return DIR_RAW / f"{clave_lago}_{fecha}_indices.tif"


def ruta_cyano_rgb(clave_lago: str, fecha: str) -> Path:
    return DIR_RAW / f"{clave_lago}_{fecha}_cyano_rgb.tif"


def ruta_rgb(clave_lago: str, fecha: str) -> Path:
    return DIR_RAW / f"{clave_lago}_{fecha}_rgb.tif"


def descargar_fecha(clave_lago: str, fecha: str, config, forzar: bool = False) -> bool:
    """Descarga los tres productos de un lago en una fecha. True si hubo datos."""
    bbox = bbox_lago(clave_lago)
    tamano = bbox_to_dimensions(bbox, resolution=RESOLUCION_M)

    destinos = {
        "indices": (ruta_indices(clave_lago, fecha), EVALSCRIPT_INDICES, MimeType.TIFF),
        "cyano": (ruta_cyano_rgb(clave_lago, fecha), EVALSCRIPT_CYANO_RGB, MimeType.PNG),
        "rgb": (ruta_rgb(clave_lago, fecha), EVALSCRIPT_RGB, MimeType.PNG),
    }

    if not forzar and all(ruta.exists() for ruta, _, _ in destinos.values()):
        print(f"  {clave_lago} {fecha}: ya descargado")
        return True

    # 1) Índices numéricos — el insumo del análisis.
    ruta, script, mime = destinos["indices"]
    datos = _pedir(script, bbox, tamano, fecha, config, mime)
    if datos is None or not np.isfinite(datos).any() or datos[..., -1].max() == 0:
        print(f"  {clave_lago} {fecha}: sin datos válidos, se omite")
        return False
    _guardar_geotiff(datos.astype("float32"), bbox, ruta)

    # 2) y 3) Vistas en color: script original de CyanoLakes y color verdadero.
    for llave in ("cyano", "rgb"):
        ruta, script, mime = destinos[llave]
        imagen = _pedir(script, bbox, tamano, fecha, config, mime)
        _guardar_geotiff(imagen.astype("uint8"), bbox, ruta)

    validos = int((datos[..., -1] > 0).sum())
    print(f"  {clave_lago} {fecha}: OK  {tamano[0]}x{tamano[1]} px, {validos:,} válidos")
    return True


def probar_conexion(config) -> None:
    """Ejercicio 1: comprueba que la autenticación con el API funciona."""
    from sentinelhub import SentinelHubCatalog

    catalogo = SentinelHubCatalog(config=config)
    bbox = bbox_lago("Amatitlan")
    resultados = list(
        catalogo.search(
            SENTINEL2_L2A_CDSE,
            bbox=bbox,
            time=("2026-02-01", "2026-02-10"),
            fields={"include": ["id", "properties.datetime"], "exclude": []},
        )
    )
    print(f"Conexión establecida. {len(resultados)} escenas en la ventana de prueba:")
    for r in resultados[:5]:
        print("   -", r["id"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga de rásters Sentinel-2")
    parser.add_argument("--probar", action="store_true", help="solo probar conexión")
    parser.add_argument("--forzar", action="store_true", help="re-descargar todo")
    args = parser.parse_args()

    config = obtener_config()

    if args.probar:
        probar_conexion(config)
        return 0

    total, obtenidas = 0, 0
    for clave_lago in LAGOS:
        print(f"\n{LAGOS[clave_lago]['nombre']}")
        for fecha, _nubosidad, _sat in FECHAS[clave_lago]:
            total += 1
            try:
                if descargar_fecha(clave_lago, fecha, config, forzar=args.forzar):
                    obtenidas += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  {clave_lago} {fecha}: ERROR -> {exc}")

    print(f"\nDescargas completas: {obtenidas}/{total}")
    return 0 if obtenidas else 1


if __name__ == "__main__":
    sys.exit(main())
