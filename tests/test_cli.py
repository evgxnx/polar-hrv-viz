from __future__ import annotations

import pandas as pd

from polar_hrv_viz.cli import main


def test_cli_writes_figure_and_summary(steady_recording, tmp_path, capsys):
    out = tmp_path / "out"

    assert main(["plot", str(steady_recording), "--out", str(out)]) == 0

    assert (out / "timeline.png").stat().st_size > 0
    summary = pd.read_csv(out / "phase_summary.csv")
    assert summary["phase"].tolist() == ["rest", "task"]


def test_cli_reports_a_broken_recording(tmp_path, capsys):
    assert main(["plot", str(tmp_path / "missing")]) == 2
    assert "rr.csv: file not found" in capsys.readouterr().err
