import numpy as np
import pandas as pd

from src.ml_dataset import deterministic_sample, spatial_block_ids
from src.ml_maps import reconstruct


def test_blocks_include_lake_and_are_deterministic():
    result = spatial_block_ids(["A", "B", "A"], [100, 100, 1100], [100, 100, 100])
    assert result.tolist() == ["A_1000m_0_0", "B_1000m_0_0", "A_1000m_1_0"]


def test_sampling_reproducible_and_stratified():
    df = pd.DataFrame({"lake": ["A"]*50+["B"]*50, "date": ["2026-01-01"]*100,
                       "alta_presencia": [0, 1]*50, "observation_id": [f"x{i}" for i in range(100)]})
    a = deterministic_sample(df, 40); b = deterministic_sample(df, 40)
    assert a["observation_id"].tolist() == b["observation_id"].tolist()
    assert set(a["alta_presencia"]) == {0, 1}


def test_reconstruction_does_not_interpolate():
    out = reconstruct([.2, .8], [0, 1], [0, 1], (3, 3))
    assert np.isnan(out[0, 1]) and out[1, 1] == .8
