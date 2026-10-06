from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .io import Recording
from .processing import flag_artifacts
from .style import ARTIFACT, BAND, INK_SECONDARY, MOTION, SERIES, light_theme


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
