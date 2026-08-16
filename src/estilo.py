"""Estilo visual común a todas las figuras del laboratorio.

La paleta está elegida para que siga siendo legible en impresión y para
personas con daltonismo: los dos lagos se distinguen por un par azul/naranja
verificado (ΔE 24.7 bajo simulación de protanopía), y además cada serie lleva
marcador propio y etiqueta directa, de modo que la identidad nunca depende solo
del color.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

# --------------------------------------------------------------------------- #
# Paleta
# --------------------------------------------------------------------------- #
COLOR_LAGO = {
    "Atitlan": "#2a78d6",    # azul
    "Amatitlan": "#eb6834",  # naranja
}
MARCADOR_LAGO = {"Atitlan": "o", "Amatitlan": "s"}

TINTA = "#0b0b0b"
TINTA_SEC = "#52514e"
TINTA_TENUE = "#898781"
REJILLA = "#e1e0d9"
SUPERFICIE = "#fcfcfb"
EJE = "#c3c2b7"

CRITICO = "#d03b3b"
ALERTA = "#fab219"

# Rampa secuencial de un solo tono (naranja) para la clorofila-a: el agua limpia
# se ve casi blanca y la floración intensa se ve oscura y saturada.
CMAP_CHL = LinearSegmentedColormap.from_list(
    "cianobacteria",
    ["#fff4ec", "#fbd0b5", "#f5a678", "#eb6834", "#c04517", "#7a2c0d"],
)

# Rampa divergente para mapas de diferencia entre fechas: azul = bajó,
# gris = sin cambio, rojo = subió.
CMAP_DIF = LinearSegmentedColormap.from_list(
    "diferencia",
    ["#184f95", "#6da7ec", "#f0efec", "#e88b8a", "#a52424"],
)

COLOR_TIERRA = "#e8e6e0"  # todo lo que no es agua del lago


def aplicar_estilo() -> None:
    """Ajustes globales de matplotlib: ejes discretos, texto legible."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "savefig.facecolor": SUPERFICIE,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "axes.titlesize": 12.5,
            "axes.titleweight": "bold",
            "axes.titlecolor": TINTA,
            "axes.titlepad": 12,
            "axes.labelsize": 10,
            "axes.labelcolor": TINTA_SEC,
            "axes.edgecolor": EJE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": REJILLA,
            "grid.linewidth": 0.7,
            "xtick.color": TINTA_TENUE,
            "ytick.color": TINTA_TENUE,
            "xtick.labelcolor": TINTA_SEC,
            "ytick.labelcolor": TINTA_SEC,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "legend.fontsize": 9.5,
            "lines.linewidth": 2.0,
            "lines.markersize": 6,
        }
    )


def norma_divergente(vmin: float, vmax: float) -> TwoSlopeNorm:
    """Normalización centrada en cero, robusta a rangos asimétricos."""
    limite = max(abs(vmin), abs(vmax), 1e-6)
    return TwoSlopeNorm(vmin=-limite, vcenter=0.0, vmax=limite)


def guardar(fig, ruta, nota: str | None = None) -> None:
    """Guarda la figura, opcionalmente con una nota al pie."""
    if nota:
        fig.text(0.5, -0.02, nota, ha="center", fontsize=8.5, color=TINTA_TENUE)
    fig.savefig(ruta)
    plt.close(fig)
    print(f"  figura -> {ruta.name}")
