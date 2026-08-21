"""Pipelines comparables para los tres clasificadores obligatorios."""
from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 3084


def model_specs():
    return {
        "logistic_regression": (
            Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("scale", StandardScaler()),
                      ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))]),
            {"model__C": [0.1, 1.0, 10.0]},
        ),
        "random_forest": (
            Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("model", RandomForestClassifier(n_estimators=150, class_weight="balanced_subsample",
                                                       n_jobs=-1, random_state=SEED))]),
            {"model__max_depth": [8, 16, None], "model__min_samples_leaf": [1, 5]},
        ),
        "hist_gradient_boosting": (
            Pipeline([("imputer", SimpleImputer(strategy="median")),
                      ("model", HistGradientBoostingClassifier(random_state=SEED))]),
            {"model__learning_rate": [0.05, 0.1], "model__max_leaf_nodes": [15, 31],
             "model__l2_regularization": [0.0, 1.0]},
        ),
    }
