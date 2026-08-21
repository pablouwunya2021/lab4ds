"""Conversión reproducible de GeoTIFF ML v1 a observaciones tabulares."""
from __future__ import annotations

import hashlib
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask

from src.config import LAGOS
from src.evalscripts import CLP_MAXIMO, ML_BAND_NAMES

TARGET_THRESHOLD = 10.0
UTM_EPSG = 32615


def spatial_block_ids(lake, x, y, size_m: int = 1000, origin=(0, 0)) -> np.ndarray:
    bx = np.floor((np.asarray(x) - origin[0]) / size_m).astype(int)
    by = np.floor((np.asarray(y) - origin[1]) / size_m).astype(int)
    return np.asarray([f"{l}_{size_m}m_{i}_{j}" for l, i, j in zip(lake, bx, by)])


def raster_to_observations(path: Path, lake: str, date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve datos limpios y bitácora con conteos acumulativos por filtro."""
    with rasterio.open(path) as src:
        if src.count != len(ML_BAND_NAMES):
            raise ValueError(f"{path}: se esperaban {len(ML_BAND_NAMES)} bandas, hay {src.count}")
        arr = src.read().astype("float64")
        height, width, transform, crs = src.height, src.width, src.transform, src.crs
        gdf = gpd.read_file(LAGOS[lake]["geojson"]).to_crs(crs)
        inside = geometry_mask(gdf.geometry, (height, width), transform, invert=True)
    rows, cols = np.indices((height, width))
    xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")
    data = {name: arr[i].ravel() for i, name in enumerate(ML_BAND_NAMES)}
    data.update(row=rows.ravel(), col=cols.ravel(), x_utm=np.asarray(xs).ravel(),
                y_utm=np.asarray(ys).ravel(), lake=lake, date=date, inside=inside.ravel())
    df = pd.DataFrame(data)
    log = []
    def apply(name, mask):
        nonlocal df
        before = len(df); df = df.loc[np.asarray(mask)].copy()
        log.append({"lake": lake, "date": date, "filter": name, "before": before,
                    "after": len(df), "removed": before-len(df)})
    apply("inside_aoi", df["inside"])
    apply("datamask", df["datamask"] > 0)
    apply("water", df["agua"] > .5)
    apply("cloud", df["clp"].between(0, CLP_MAXIMO))
    numeric = ML_BAND_NAMES + ["x_utm", "y_utm"]
    apply("finite", np.isfinite(df[numeric]).all(axis=1))
    reflectance = [c for c in ML_BAND_NAMES if c.startswith("B")]
    apply("physical_range", df[reflectance].apply(lambda s: s.between(0, 1.5)).all(axis=1)
          & df["chl"].between(0, 300))
    df = df.drop(columns="inside")
    to_wgs = Transformer.from_crs(crs, 4326, always_xy=True)
    df["lon"], df["lat"] = to_wgs.transform(df["x_utm"].to_numpy(), df["y_utm"].to_numpy())
    df["alta_presencia"] = (df["chl"] >= TARGET_THRESHOLD).astype("int8")
    df["spatial_block"] = spatial_block_ids(df["lake"], df["x_utm"], df["y_utm"])
    df["observation_id"] = [hashlib.sha1(f"{lake}|{date}|{r}|{c}".encode()).hexdigest()[:16]
                              for r, c in zip(df["row"], df["col"])]
    before = len(df); df = df.drop_duplicates("observation_id")
    log.append({"lake": lake, "date": date, "filter": "duplicates", "before": before,
                "after": len(df), "removed": before-len(df)})
    return df, pd.DataFrame(log)


def deterministic_sample(df: pd.DataFrame, max_rows: int, seed: int = 3084) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df.copy()
    frac = max_rows / len(df)
    return (df.groupby(["lake", "date", "alta_presencia"], group_keys=False)
            .sample(frac=frac, random_state=seed).sort_values("observation_id").reset_index(drop=True))
