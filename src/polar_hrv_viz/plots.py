from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .io import Recording
from .processing import assign_phase, clean_pairs, flag_artifacts, poincare_sd
from .style import (
    ARTIFACT,
    AXIS,
    BAND,
    INK,
    INK_SECONDARY,
    MOTION,
    SERIES,
    SURFACE,
    light_theme,
)

HIST_BIN_MS = 50


def _mark_phases(axes, phases) -> None:
    for i, row in enumerate(phases.itertuples(index=False)):
        start, end = row.start_s / 60, row.end_s / 60
        for ax in axes:
            if i % 2 == 0:
                ax.axvspan(start, end, color=BAND, lw=0, zorder=0)
        axes[0].text(
            (start + end) / 2,
            1.0,
            row.phase,
            transform=axes[0].get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=8,
            color=INK_SECONDARY,
        )


def plot_timeline(rec: Recording, title: str | None = None) -> Figure:
    rr = flag_artifacts(rec.rr)
    has_motion = rec.motion is not None and not rec.motion.empty
    n = 3 if has_motion else 2

    with light_theme():
        fig, axes = plt.subplots(
            n,
            1,
            sharex=True,
            figsize=(11, 2.2 * n + 0.9),
            height_ratios=[1, 1.4, 0.6][:n],
            layout="constrained",
        )
        ax_hr, ax_rr = axes[0], axes[1]

        ax_hr.plot(rec.hr["t_s"] / 60, rec.hr["hr_bpm"], color=SERIES, lw=1)
        ax_hr.set_ylabel("Heart rate, bpm")

        bad = rr[rr["artifact"]]
        ax_rr.plot(
            rr["t_s"] / 60,
            rr["rr_ms"].where(~rr["artifact"]),
            color=SERIES,
            lw=0.9,
            label="RR interval",
        )
        ax_rr.scatter(
            bad["t_s"] / 60,
            bad["rr_ms"],
            s=9,
            color=ARTIFACT,
            marker="x",
            lw=0.8,
            label=f"Artifact ({len(bad)} of {len(rr)})",
            zorder=3,
        )
        ax_rr.set_ylabel("RR interval, ms")
        ax_rr.legend(loc="upper left", ncols=2, bbox_to_anchor=(0, 1.0))

        if has_motion:
            ax_m = axes[2]
            ax_m.fill_between(rec.motion["t_s"] / 60, rec.motion["acc_rms_mg"], color=MOTION, lw=0)
            ax_m.set_ylabel("Motion, mg")
            ax_m.set_ylim(bottom=0)

        if rec.phases is not None:
            _mark_phases(axes, rec.phases)

        axes[-1].set_xlabel("Time, min")
        axes[-1].set_xlim(0, rec.duration_s / 60)
        if title:
            fig.suptitle(title, x=0.01, ha="left", fontsize=11, fontweight="bold")
    return fig


def _phase_groups(rec: Recording) -> list[tuple[str, pd.DataFrame]]:
    rr = flag_artifacts(rec.rr)
    if rec.phases is None:
        return [("recording", rr)]
    phase = assign_phase(rr["t_s"], rec.phases)
    return [(name, rr[phase == name]) for name in rec.phases["phase"]]


def plot_rr_histogram(rec: Recording) -> Figure:
    rr = flag_artifacts(rec.rr)
    values = rr.loc[~rr["artifact"], "rr_ms"].to_numpy(dtype=float)
    lo = np.floor(values.min() / HIST_BIN_MS) * HIST_BIN_MS
    hi = np.floor(values.max() / HIST_BIN_MS) * HIST_BIN_MS + HIST_BIN_MS
    edges = np.arange(lo, hi + HIST_BIN_MS / 2, HIST_BIN_MS)
    counts, _ = np.histogram(values, bins=edges)
    share = 100 * counts / counts.sum()

    with light_theme():
        fig, ax = plt.subplots(figsize=(7, 3.6), layout="constrained")
        ax.bar(
            edges[:-1],
            share,
            width=HIST_BIN_MS,
            align="edge",
            color=SERIES,
            edgecolor=SURFACE,
            linewidth=1,
        )
        mode = int(np.argmax(share))
        ax.annotate(
            f"Mode {edges[mode]:.0f}–{edges[mode + 1]:.0f} ms, {share[mode]:.0f} %",
            xy=(edges[mode] + HIST_BIN_MS / 2, share[mode]),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=INK_SECONDARY,
        )
        ax.set_title(f"RR interval distribution, {len(values)} clean beats")
        ax.set_xlabel(f"RR interval, ms ({HIST_BIN_MS} ms bins)")
        ax.set_ylabel("Share of beats, %")
        ax.set_ylim(0, share.max() * 1.15)
    return fig


def plot_poincare(rec: Recording) -> Figure:
    groups = _phase_groups(rec)
    pairs = [(name, *clean_pairs(beats)) for name, beats in groups]
    every = np.concatenate([np.concatenate([c, f]) for _, c, f in pairs if len(c)])
    lo, hi = np.percentile(every, [0.5, 99.5])
    pad = max((hi - lo) * 0.08, 25.0)
    lim = (lo - pad, hi + pad)

    with light_theme():
        fig, axes = plt.subplots(
            1,
            len(pairs),
            figsize=(2.6 * len(pairs) + 0.6, 3.9),
            sharex=True,
            sharey=True,
            squeeze=False,
            layout="constrained",
        )
        for ax, (name, current, following) in zip(axes[0], pairs, strict=True):
            ax.plot(lim, lim, color=AXIS, lw=0.8, zorder=1)
            ax.scatter(current, following, s=6, color=SERIES, alpha=0.45, lw=0, zorder=2)
            sd1, sd2 = poincare_sd(current, following)
            ax.text(
                0.97,
                0.04,
                f"SD1 {sd1:.0f} ms\nSD2 {sd2:.0f} ms",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=8,
                color=INK_SECONDARY,
            )
            ax.set_title(name, fontsize=9, color=INK, pad=6)
            ax.set_xlim(lim)
            ax.set_ylim(lim)
            ax.set_aspect("equal")
            ax.grid(axis="both")
            ax.set_xlabel("RR$_n$, ms")
        axes[0][0].set_ylabel("RR$_{n+1}$, ms")
        fig.suptitle(
            "Poincaré plot of consecutive clean beats",
            x=0.01,
            ha="left",
            fontsize=11,
            fontweight="bold",
        )
        fig.get_layout_engine().set(h_pad=0.06)
    return fig
