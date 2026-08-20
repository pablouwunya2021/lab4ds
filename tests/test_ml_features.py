import pandas as pd

from src.ml_features import LEAKAGE_COLUMNS, add_temporal_features, strict_feature_columns


def test_strict_predictors_exclude_lineage_and_coordinates():
    df = add_temporal_features(pd.DataFrame({"date": ["2026-01-01"], "B02": [.1],
        "B03": [.1], "B04": [.1], "B05": [.1], "B07": [.1], "B08": [.1],
        "B8A": [.1], "B11": [.1], "B12": [.1], "ndvi": [0], "ndwi": [0],
        "ndci": [0], "chl": [4], "fai": [0], "alta_presencia": [0], "lon": [-90]}))
    features = strict_feature_columns(df)
    assert not set(features) & LEAKAGE_COLUMNS
    assert "lon" not in features
    assert {"doy_sin", "doy_cos"}.issubset(features)
