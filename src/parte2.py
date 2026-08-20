"""Orquestador idempotente de la Parte 2 (requiere los 22 GeoTIFF ML v1)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

from src.config import (DIR_ML_RAW, DIR_PARTE2_DATA, DIR_PARTE2_METRICS,
                        DIR_PARTE2_MODELS, DIR_PARTE2_TABLES, FECHAS, LAGOS)
from src.descarga import ruta_ml
from src.ml_dataset import deterministic_sample, raster_to_observations
from src.ml_features import add_temporal_features, predictor_audit, strict_feature_columns
from src.ml_models import SEED, model_specs
from src.ml_validation import (assert_no_group_overlap, classification_metrics,
                               spatial_folds, temporal_holdout)


def expected_rasters():
    return [ruta_ml(lake, date) for lake in LAGOS for date, _, _ in FECHAS[lake]]


def build_dataset() -> pd.DataFrame:
    missing = [p for p in expected_rasters() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Faltan {len(missing)} rasters ML v1. Ejecute: python -m src.descarga --ml")
    frames, logs = [], []
    for lake in LAGOS:
        for date, _, _ in FECHAS[lake]:
            frame, log = raster_to_observations(ruta_ml(lake, date), lake, date)
            frames.append(frame); logs.append(log)
    data = add_temporal_features(pd.concat(frames, ignore_index=True))
    pd.concat(logs, ignore_index=True).to_csv(DIR_PARTE2_TABLES / "filter_log.csv", index=False)
    data.to_parquet(DIR_PARTE2_DATA / "observations_master.parquet", index=False)
    predictor_audit().to_csv(DIR_PARTE2_TABLES / "predictor_audit.csv", index=False)
    return data


def train_random(data: pd.DataFrame, max_train_rows=200000):
    features = strict_feature_columns(data); y = data["alta_presencia"]
    train_idx, test_idx = train_test_split(range(len(data)), test_size=.30, stratify=y,
                                           random_state=SEED)
    train = deterministic_sample(data.iloc[train_idx], max_train_rows, SEED)
    X_train, y_train = train[features], train["alta_presencia"]
    X_test, y_test = data.iloc[test_idx][features], data.iloc[test_idx]["alta_presencia"]
    cv = StratifiedKFold(3, shuffle=True, random_state=SEED)
    rows = []
    for name, (pipeline, grid) in model_specs().items():
        search = GridSearchCV(pipeline, grid, scoring="average_precision", cv=cv, n_jobs=-1)
        search.fit(X_train, y_train)
        prob = search.best_estimator_.predict_proba(X_test)[:, 1]
        rows.append({"strategy": "random_70_30", "model": name,
                     **classification_metrics(y_test, prob),
                     "best_params": json.dumps(search.best_params_, sort_keys=True)})
        joblib.dump(search.best_estimator_, DIR_PARTE2_MODELS / f"{name}.joblib")
    result = pd.DataFrame(rows)
    result.to_csv(DIR_PARTE2_METRICS / "random_metrics.csv", index=False)
    return result


def evaluate_validations(data: pd.DataFrame, max_train_rows=200000):
    """Espacial por fold, temporal y transferencia; destino nunca participa en ajuste."""
    features = strict_feature_columns(data); rows = []
    specs = model_specs()
    folds = spatial_folds(data)
    for fold, (tr, te) in enumerate(folds, 1):
        assert_no_group_overlap(tr, te, data["spatial_block"])
        train = deterministic_sample(data.iloc[tr], max_train_rows, SEED)
        for name, (model, _) in specs.items():
            fitted = clone(model).fit(train[features], train["alta_presencia"])
            prob = fitted.predict_proba(data.iloc[te][features])[:, 1]
            rows.append({"strategy": "spatial", "fold": fold, "model": name,
                         **classification_metrics(data.iloc[te]["alta_presencia"], prob)})
    tr, te = temporal_holdout(data)
    for lake in LAGOS:
        a = pd.to_datetime(data.iloc[tr].loc[data.iloc[tr]["lake"].eq(lake), "date"])
        b = pd.to_datetime(data.iloc[te].loc[data.iloc[te]["lake"].eq(lake), "date"])
        if len(a) and len(b) and a.max() >= b.min():
            raise AssertionError(f"Split temporal inválido para {lake}")
    for name, (model, _) in specs.items():
        train = deterministic_sample(data.iloc[tr], max_train_rows, SEED)
        fitted = clone(model).fit(train[features], train["alta_presencia"])
        prob = fitted.predict_proba(data.iloc[te][features])[:, 1]
        rows.append({"strategy": "temporal", "fold": 1, "model": name,
                     **classification_metrics(data.iloc[te]["alta_presencia"], prob)})
    for source, target in [("Atitlan", "Amatitlan"), ("Amatitlan", "Atitlan")]:
        train = deterministic_sample(data[data["lake"].eq(source)], max_train_rows, SEED)
        test = data[data["lake"].eq(target)]
        if train.empty or test.empty:
            raise ValueError("Ambos lagos deben tener observaciones")
        for name, (model, _) in specs.items():
            fitted = clone(model).fit(train[features], train["alta_presencia"])
            prob = fitted.predict_proba(test[features])[:, 1]
            rows.append({"strategy": f"cross_lake_{source}_to_{target}", "fold": 1,
                         "model": name, **classification_metrics(test["alta_presencia"], prob)})
    result = pd.DataFrame(rows)
    result.to_csv(DIR_PARTE2_METRICS / "validation_metrics_by_fold.csv", index=False)
    summary = (result.groupby(["strategy", "model"], dropna=False)
               .agg({c: ["mean", "std"] for c in ["accuracy", "balanced_accuracy", "precision",
                                                    "recall", "f1", "roc_auc", "pr_auc"]}))
    summary.to_csv(DIR_PARTE2_METRICS / "validation_metrics_summary.csv")
    pd.DataFrame({"lake": list(LAGOS), "train_dates": [
        ",".join(sorted(data.iloc[tr].loc[data.iloc[tr]["lake"].eq(l), "date"].unique())) for l in LAGOS],
        "test_dates": [",".join(sorted(data.iloc[te].loc[data.iloc[te]["lake"].eq(l), "date"].unique())) for l in LAGOS]
    }).to_csv(DIR_PARTE2_TABLES / "temporal_split.csv", index=False)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    data_path = DIR_PARTE2_DATA / "observations_master.parquet"
    data = pd.read_parquet(data_path) if data_path.exists() else build_dataset()
    if not args.build_only:
        train_random(data)
        evaluate_validations(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
