from __future__ import annotations

import pandas as pd
import pytest

from polar_hrv_viz.io import load_recording
from polar_hrv_viz.plots import (
    plot_rr_histogram,
    plot_timeline,
)

from .conftest import write_recording


def test_timeline_has_a_panel_per_signal(steady_recording):
    fig = plot_timeline(load_recording(steady_recording))

    labels = [ax.get_ylabel() for ax in fig.axes]
    assert labels == ["Heart rate, bpm", "RR interval, ms", "Motion, mg"]


def test_timeline_without_motion_has_two_panels(tmp_path):
    rec = load_recording(write_recording(tmp_path / "r", [1000.0] * 30, motion=False))

    assert len(plot_timeline(rec).axes) == 2


def test_timeline_labels_phases_and_counts_artifacts(steady_recording):
    rr = pd.read_csv(steady_recording / "rr.csv")
    rr.loc[50, "rr_ms"] = 2500
    rr.to_csv(steady_recording / "rr.csv", index=False)

    fig = plot_timeline(load_recording(steady_recording))

    texts = [t.get_text() for t in fig.axes[0].texts]
    assert texts == ["rest", "task"]
    legend = [t.get_text() for t in fig.axes[1].get_legend().get_texts()]
    assert "Artifact (1 of 120)" in legend


def test_histogram_uses_50_ms_bins_and_sums_to_100(steady_recording):
    rr = pd.read_csv(steady_recording / "rr.csv")
    rr["rr_ms"] = [900.0, 1000.0, 1100.0] * 40
    rr.to_csv(steady_recording / "rr.csv", index=False)

    ax = plot_rr_histogram(load_recording(steady_recording)).axes[0]
    bars = ax.patches

    assert {round(b.get_width()) for b in bars} == {50}
    assert sum(b.get_height() for b in bars) == pytest.approx(100.0)
    assert ax.get_title(loc="left") == "RR interval distribution, 120 clean beats"


def test_histogram_of_a_constant_rhythm_has_one_bar(steady_recording):
    ax = plot_rr_histogram(load_recording(steady_recording)).axes[0]

    assert [round(b.get_height()) for b in ax.patches] == [100]
