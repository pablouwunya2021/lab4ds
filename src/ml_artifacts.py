"""Tablas y figuras finales derivadas de datos y modelos ejecutados."""
from __future__ import annotations

import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
from sklearn.model_selection import train_test_split

from src.config import (DIR_PARTE2_DATA, DIR_PARTE2_FIGURES, DIR_PARTE2_MAPS,
                        DIR_PARTE2_METRICS, DIR_PARTE2_MODELS, DIR_PARTE2_TABLES)
from src.ml_explain import permutation_table, shap_summary
from src.ml_features import strict_feature_columns
from src.ml_maps import error_map, probability_map
from src.ml_models import SEED
from src.ml_validation import bootstrap_intervals


def eda(data):
    counts = data.groupby(["lake", "date", "alta_presencia"]).size().rename("n").reset_index()
    counts.to_csv(DIR_PARTE2_TABLES / "counts_lake_date_class.csv", index=False)
    data.describe(include="all").transpose().to_csv(DIR_PARTE2_TABLES / "descriptive_statistics.csv")
    data.isna().mean().rename("missing_fraction").to_csv(DIR_PARTE2_TABLES / "missing_values.csv")
    fig, ax = plt.subplots(figsize=(11, 5)); sns.barplot(data=counts, x="date", y="n", hue="alta_presencia", ax=ax)
    ax.tick_params(axis="x", rotation=55); ax.set_yscale("log"); ax.set_title("Distribución de clases por fecha (escala log)")
    fig.tight_layout(); fig.savefig(DIR_PARTE2_FIGURES / "class_distribution.png", dpi=180); plt.close(fig)
    blocks = pd.read_csv(DIR_PARTE2_TABLES / "spatial_block_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (lake, group) in zip(axes, data.groupby("lake")):
        one = group.drop_duplicates("spatial_block")
        ax.scatter(one["x_utm"], one["y_utm"], c=pd.factorize(one["spatial_block"])[0], s=10, cmap="tab20")
        ax.set_title(f"Bloques 1 km · {lake}"); ax.set_aspect("equal"); ax.ticklabel_format(style="plain")
    fig.tight_layout(); fig.savefig(DIR_PARTE2_FIGURES / "spatial_blocks.png", dpi=180); plt.close(fig)


def main():
    data = pd.read_parquet(DIR_PARTE2_DATA / "observations_master.parquet"); eda(data)
    features = strict_feature_columns(data)
    tr, te = train_test_split(range(len(data)), test_size=.30, stratify=data["alta_presencia"], random_state=SEED)
    model = joblib.load(DIR_PARTE2_MODELS / "random_forest.joblib")
    test = data.iloc[te]; prob_test = model.predict_proba(test[features])[:, 1]
    ci = bootstrap_intervals(test["alta_presencia"], prob_test)
    (DIR_PARTE2_METRICS / "winner_bootstrap_ci.json").write_text(json.dumps(ci, indent=2), encoding="utf-8")
    sample = test.sample(min(50000, len(test)), random_state=SEED)
    table = permutation_table(model, sample[features], sample["alta_presencia"], features)
    table.to_csv(DIR_PARTE2_TABLES / "permutation_importance.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 5)); top = table.head(12).sort_values("importance_mean")
    ax.barh(top["feature"], top["importance_mean"], xerr=top["importance_std"]); ax.set_xlabel("Disminución de PR-AUC")
    ax.set_title("Importancia por permutación · test no usado en ajuste"); fig.tight_layout()
    fig.savefig(DIR_PARTE2_FIGURES / "permutation_importance.png", dpi=180); plt.close(fig)
    shap_summary(model, sample[features].head(500), DIR_PARTE2_FIGURES / "shap_summary.png", max_rows=500)
    random = pd.read_csv(DIR_PARTE2_METRICS / "random_metrics.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for ax, (_, row) in zip(axes, random.iterrows()):
        cm = np.array([[row.tn, row.fp], [row.fn, row.tp]])
        ConfusionMatrixDisplay(cm).plot(ax=ax, colorbar=False); ax.set_title(row["model"])
    fig.tight_layout(); fig.savefig(DIR_PARTE2_FIGURES / "confusion_matrices.png", dpi=180); plt.close(fig)
    prob_all = model.predict_proba(data[features])[:, 1]
    for lake in sorted(data["lake"].unique()):
        date = sorted(data.loc[data["lake"].eq(lake), "date"].unique())[-1]
        probability_map(data, prob_all, lake, date, DIR_PARTE2_MAPS / f"probability_{lake}_{date}.png")
        error_map(data, prob_all, lake, date, DIR_PARTE2_MAPS / f"errors_{lake}_{date}.png")
    pd.DataFrame({"observation_id": data["observation_id"], "probability": prob_all.astype("float32")}).to_parquet(
        DIR_PARTE2_DATA / "predictions_random_forest.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
