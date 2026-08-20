"""Contrato de predictores y controles contra fuga de información."""
from __future__ import annotations

import numpy as np
import pandas as pd

TARGET = "alta_presencia"
TRACE_COLUMNS = ["chl", "ndci", TARGET]
# y=f(poly(NDCI)); NDCI usa B04/B05. NDVI usa B04 y se excluye conservadoramente.
LEAKAGE_COLUMNS = {"chl", "ndci", TARGET, "B04", "B05", "ndvi"}
IDENTIFIER_COLUMNS = {
    "observation_id", "lake", "date", "row", "col", "lon", "lat", "x_utm",
    "y_utm", "spatial_block", "clp", "datamask", "agua",
}
STRICT_FEATURES = ["B02", "B03", "B07", "B08", "B8A", "B11", "B12", "ndwi", "fai",
                   "doy_sin", "doy_cos", "rainy_season"]


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dates = pd.to_datetime(out["date"])
    doy = dates.dt.dayofyear.astype(float)
    out["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    out["rainy_season"] = dates.dt.month.between(5, 10).astype("int8")
    return out


def strict_feature_columns(df: pd.DataFrame) -> list[str]:
    cols = [c for c in STRICT_FEATURES if c in df.columns]
    forbidden = set(cols) & LEAKAGE_COLUMNS
    if forbidden:
        raise ValueError(f"Predictores con leakage: {sorted(forbidden)}")
    return cols


def predictor_audit() -> pd.DataFrame:
    rows = []
    reasons = {
        "chl": "transformación directa de NDCI y fuente de y",
        "ndci": "fuente directa del proxy continuo",
        TARGET: "variable respuesta",
        "B04": "componente directo de NDCI; también de NDVI y FAI",
        "B05": "componente directo de NDCI",
        "ndvi": "comparte B04 con NDCI; exclusión conservadora",
        "lon/lat/x_utm/y_utm": "puede memorizar lago o zonas; solo agrupación/mapas",
        "lake": "identifica dominio; solo segmentación y experimentos",
    }
    for variable, reason in reasons.items():
        rows.append({"variable": variable, "permitido_modelo_principal": False, "razon": reason})
    for variable in STRICT_FEATURES:
        rows.append({"variable": variable, "permitido_modelo_principal": True,
                     "razon": "no participa directamente en NDCI según el linaje declarado"})
    return pd.DataFrame(rows)
