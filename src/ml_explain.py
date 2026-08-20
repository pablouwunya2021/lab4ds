"""Importancia por permutación y SHAP sobre muestras determinísticas."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


def permutation_table(model, X, y, feature_names, seed=3084) -> pd.DataFrame:
    result = permutation_importance(model, X, y, scoring="average_precision", n_repeats=10,
                                    random_state=seed, n_jobs=-1)
    return pd.DataFrame({"feature": feature_names, "importance_mean": result.importances_mean,
                         "importance_std": result.importances_std}).sort_values("importance_mean", ascending=False)


def shap_summary(model, X: pd.DataFrame, output, max_rows=2000, seed=3084) -> None:
    import shap
    sample = X.sample(min(max_rows, len(X)), random_state=seed)
    transformed = model[:-1].transform(sample)
    estimator = model[-1]
    explainer = shap.Explainer(estimator, transformed, feature_names=list(X.columns))
    values = explainer(transformed)
    shap.summary_plot(values, transformed, feature_names=list(X.columns), show=False)
    plt.tight_layout(); plt.savefig(output, dpi=180, bbox_inches="tight"); plt.close()
