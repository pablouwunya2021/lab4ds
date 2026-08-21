import numpy as np
import pandas as pd

from src.ml_validation import (assert_no_group_overlap, classification_metrics,
                               spatial_folds, temporal_holdout)


def synthetic():
    rows = []
    for lake in ["A", "B"]:
        for d in range(5):
            for block in range(5):
                for y in [0, 1]:
                    rows.append((lake, f"2026-01-{d+1:02d}", f"{lake}_{block}", y))
    return pd.DataFrame(rows, columns=["lake", "date", "spatial_block", "alta_presencia"])


def test_spatial_folds_never_share_blocks():
    df = synthetic()
    for tr, te in spatial_folds(df, n_splits=5):
        assert_no_group_overlap(tr, te, df["spatial_block"])


def test_temporal_split_keeps_dates_and_order_per_lake():
    df = synthetic(); tr, te = temporal_holdout(df, 2)
    for lake in df["lake"].unique():
        train = pd.to_datetime(df.iloc[tr].query("lake == @lake")["date"])
        test = pd.to_datetime(df.iloc[te].query("lake == @lake")["date"])
        assert train.max() < test.min()
        assert not set(train) & set(test)


def test_metrics_confusion_counts():
    m = classification_metrics([0, 0, 1, 1], [.1, .9, .8, .2])
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (1, 1, 1, 1)
    assert np.isclose(m["accuracy"], .5)
