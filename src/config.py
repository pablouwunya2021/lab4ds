"""Configuración central del Laboratorio 4 — Análisis de datos geoespaciales.

Reúne en un solo lugar las credenciales, las rutas del proyecto, las áreas de
interés de cada lago y las fechas oficiales indicadas en el enunciado.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sentinelhub import DataCollection, SHConfig

# --------------------------------------------------------------------------- #
# Rutas
# --------------------------------------------------------------------------- #
RAIZ = Path(__file__).resolve().parents[1]
DIR_DATOS = RAIZ / "data"
DIR_GEOJSON = DIR_DATOS / "geojson"
DIR_RAW = DIR_DATOS / "raw"
DIR_SALIDA = RAIZ / "outputs"
DIR_FIGURAS = DIR_SALIDA / "figuras"
DIR_MAPAS = DIR_SALIDA / "mapas"
DIR_TABLAS = DIR_SALIDA / "tablas"

for _d in (DIR_RAW, DIR_FIGURAS, DIR_MAPAS, DIR_TABLAS):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Áreas de interés (bounding boxes del enunciado, EPSG:4326)
# --------------------------------------------------------------------------- #
LAGOS = {
    "Atitlan": {
        "nombre": "Lago de Atitlán",
        "bbox": (-91.326256, 14.5948, -91.07151, 14.750979),  # W, S, E, N
        "geojson": DIR_GEOJSON / "Lago_Atitlan.geojson",
    },
    "Amatitlan": {
        "nombre": "Lago de Amatitlán",
        "bbox": (-90.638065, 14.412347, -90.512924, 14.493799),
        "geojson": DIR_GEOJSON / "Lago_Amatitlan.geojson",
    },
}

# --------------------------------------------------------------------------- #
# Fechas oficiales del enunciado (11 por lago) con su nubosidad reportada
# --------------------------------------------------------------------------- #
FECHAS = {
    "Amatitlan": [
        ("2025-01-28", 0.06, "Sentinel-2B"),
        ("2025-04-15", 0.09, "Sentinel-2A"),
        ("2025-04-28", 1.03, "Sentinel-2B"),
        ("2025-11-24", 0.50, "Sentinel-2B"),
        ("2026-01-08", 0.77, "Sentinel-2C"),
        ("2026-02-02", 0.39, "Sentinel-2B"),
        ("2026-02-07", 0.02, "Sentinel-2C"),
        ("2026-03-29", 0.01, "Sentinel-2C"),
        ("2026-04-13", 0.09, "Sentinel-2B"),
        ("2026-04-28", 4.96, "Sentinel-2C"),
        ("2026-06-19", 13.00, "Sentinel-2A"),
    ],
    "Atitlan": [
        ("2025-01-18", 0.02, "Sentinel-2B"),
        ("2025-04-13", 0.54, "Sentinel-2C"),
        ("2025-05-13", 4.37, "Sentinel-2C"),
        ("2025-07-17", 3.57, "Sentinel-2A"),
        ("2025-11-21", 3.15, "Sentinel-2A"),
        ("2025-12-29", 3.17, "Sentinel-2C"),
        ("2026-02-12", 0.04, "Sentinel-2B"),
        ("2026-03-24", 3.17, "Sentinel-2B"),
        ("2026-04-13", 0.01, "Sentinel-2B"),
        ("2026-04-28", 4.96, "Sentinel-2C"),
        ("2026-07-22", 4.02, "Sentinel-2B"),
    ],
}

# Resolución de trabajo en metros. Las bandas del borde rojo (B05) son de 20 m,
# así que 20 m es la resolución nativa más fina común a todo lo que usamos.
RESOLUCION_M = 20

# --------------------------------------------------------------------------- #
# Conexión con Sentinel Hub sobre el Copernicus Data Space Ecosystem
# --------------------------------------------------------------------------- #
URL_BASE_SH = "https://sh.dataspace.copernicus.eu"
URL_TOKEN_SH = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/"
    "protocol/openid-connect/token"
)


def obtener_config() -> SHConfig:
    """Devuelve una SHConfig autenticada contra el CDSE.

    Las credenciales se leen del archivo `.env` (ver `.env.example`); nunca se
    escriben en el código ni se versionan.
    """
    load_dotenv(RAIZ / ".env")

    client_id = os.getenv("SH_CLIENT_ID", "").strip()
    client_secret = os.getenv("SH_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise RuntimeError(
            "Faltan credenciales. Copiá `.env.example` a `.env` y llená "
            "SH_CLIENT_ID y SH_CLIENT_SECRET con las de tu cuenta de "
            "Copernicus Data Space Ecosystem."
        )

    config = SHConfig()
    config.sh_client_id = client_id
    config.sh_client_secret = client_secret
    config.sh_base_url = URL_BASE_SH
    config.sh_token_url = URL_TOKEN_SH
    return config


# Colección Sentinel-2 L2A servida por el CDSE (reflectancia a nivel de suelo).
SENTINEL2_L2A_CDSE = DataCollection.SENTINEL2_L2A.define_from(
    "s2l2a_cdse", service_url=URL_BASE_SH
)
