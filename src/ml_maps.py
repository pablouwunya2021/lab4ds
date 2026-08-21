"""Mapas estáticos sin interpolar píxeles no observados."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap


PROB_BOUNDS = [0, .25, .5, .75, 1]


def reconstruct(values, rows, cols, shape):
    out = np.full(shape, np.nan, dtype=float)
    out[np.asarray(rows, int), np.asarray(cols, int)] = values
    return out


def probability_map(df, probabilities, lake, date, output):
    part = df[(df["lake"] == lake) & (df["date"] == date)].copy()
    p = np.asarray(probabilities)[part.index]
    shape = (int(part["row"].max()) + 1, int(part["col"].max()) + 1)
    grid = reconstruct(p, part["row"], part["col"], shape)
    cmap = ListedColormap(["#2166ac", "#67a9cf", "#fdae61", "#b2182b"])
    norm = BoundaryNorm(PROB_BOUNDS, cmap.N)
    fig, ax = plt.subplots(figsize=(8, 6)); im = ax.imshow(grid, cmap=cmap, norm=norm)
    cbar = fig.colorbar(im, ax=ax, ticks=[.125, .375, .625, .875])
    cbar.ax.set_yticklabels(["muy baja", "baja", "alta", "muy alta"])
    ax.set_title(f"{lake} · {date} · probabilidad de alta presencia"); ax.axis("off")
    fig.savefig(output, dpi=180, bbox_inches="tight"); plt.close(fig)


def error_map(df, probabilities, lake, date, output, threshold=.5):
    part = df[(df["lake"] == lake) & (df["date"] == date)].copy()
    pred = (np.asarray(probabilities)[part.index] >= threshold).astype(int)
    truth = part["alta_presencia"].to_numpy()
    code = truth * 2 + pred  # 0 TN, 1 FP, 2 FN, 3 TP
    shape = (int(part["row"].max()) + 1, int(part["col"].max()) + 1)
    grid = reconstruct(code, part["row"], part["col"], shape)
    cmap = ListedColormap(["#d9d9d9", "#fdae61", "#d7191c", "#1a9641"])
    fig, ax = plt.subplots(figsize=(8, 6)); im = ax.imshow(grid, cmap=cmap, vmin=-.5, vmax=3.5)
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3]); cbar.ax.set_yticklabels(["TN", "FP", "FN", "TP"])
    ax.set_title(f"{lake} · {date} · errores a umbral {threshold:.2f}"); ax.axis("off")
    fig.savefig(output, dpi=180, bbox_inches="tight"); plt.close(fig)
