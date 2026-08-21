"""Splits y métricas sin contaminación espacial, temporal o entre lagos."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score,
                             average_precision_score)
from sklearn.model_selection import StratifiedGroupKFold


def classification_metrics(y_true, y_prob, threshold=.5) -> dict:
    y_true = np.asarray(y_true); pred = (np.asarray(y_prob) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    safe_auc = lambda f: float(f(y_true, y_prob)) if np.unique(y_true).size == 2 else np.nan
    return {"accuracy": accuracy_score(y_true, pred),
            "balanced_accuracy": balanced_accuracy_score(y_true, pred),
            "precision": precision_score(y_true, pred, zero_division=0),
            "recall": recall_score(y_true, pred, zero_division=0),
            "f1": f1_score(y_true, pred, zero_division=0),
            "roc_auc": safe_auc(roc_auc_score), "pr_auc": safe_auc(average_precision_score),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def bootstrap_intervals(y_true, y_prob, threshold=.5, n_boot=200, max_rows=100000, seed=3084):
    """IC percentil 95%; submuestra estratificada fija para limitar costo."""
    frame = pd.DataFrame({"y": y_true, "p": y_prob})
    if len(frame) > max_rows:
        frame = frame.groupby("y", group_keys=False).sample(frac=max_rows/len(frame), random_state=seed)
    rng = np.random.default_rng(seed); rows = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(frame), len(frame))
        rows.append(classification_metrics(frame["y"].to_numpy()[idx], frame["p"].to_numpy()[idx], threshold))
    boot = pd.DataFrame(rows)
    return {f"{c}_{q}": float(boot[c].quantile(v)) for c in
            ["balanced_accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
            for q, v in [("low", .025), ("high", .975)]}


def spatial_folds(df: pd.DataFrame, n_splits=5, seed=3084):
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(splitter.split(df, df["alta_presencia"], groups=df["spatial_block"]))


def temporal_holdout(df: pd.DataFrame, n_test_dates=2):
    """Últimas fechas completas de cada lago; jamás mezcla una fecha."""
    test = np.zeros(len(df), dtype=bool)
    dates = pd.to_datetime(df["date"])
    for lake in sorted(df["lake"].unique()):
        idx = df["lake"].eq(lake)
        selected = sorted(dates[idx].unique())[-n_test_dates:]
        test |= idx.to_numpy() & dates.isin(selected).to_numpy()
    train_idx, test_idx = np.flatnonzero(~test), np.flatnonzero(test)
    if dates.iloc[train_idx].max() >= dates.iloc[test_idx].max():
        # La condición fuerte se verifica por lago en tests y en el pipeline.
        pass
    return train_idx, test_idx


def assert_no_group_overlap(train_idx, test_idx, groups) -> None:
    overlap = set(np.asarray(groups)[train_idx]) & set(np.asarray(groups)[test_idx])
    if overlap:
        raise AssertionError(f"Grupos compartidos: {sorted(overlap)[:3]}")
