from __future__ import annotations

from contextlib import contextmanager

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

DPI = 150

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BAND = "#f4f3f0"
SERIES = "#2a78d6"
SERIES_LIGHT = "#cde2fb"
MOTION = "#c3c2b7"
ARTIFACT = "#d03b3b"

RC = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": ["DejaVu Sans"],
    "font.size": 9,
    "text.color": INK,
    "axes.labelcolor": INK_SECONDARY,
    "axes.labelsize": 9,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlecolor": INK,
    "axes.titlepad": 14,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": AXIS,
    "ytick.color": AXIS,
    "xtick.labelcolor": INK_MUTED,
    "ytick.labelcolor": INK_MUTED,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "ytick.left": False,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "legend.labelcolor": INK_SECONDARY,
}


@contextmanager
def light_theme():
    with plt.rc_context(RC):
        yield
