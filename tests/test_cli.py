from __future__ import annotations

import pandas as pd

from polar_hrv_viz.cli import main


def test_cli_writes_figure_and_summary(steady_recording, tmp_path, capsys):
    out = tmp_path / "out"

    assert main(["plot", str(steady_recording), "--out", str(out)]) == 0

    for name in ["timeline", "rr_histogram", "poincare", "phase_heart_rate"]:
        assert (out / f"{name}.png").stat().st_size > 0
    summary = pd.read_csv(out / "phase_summary.csv")
    assert summary["phase"].tolist() == ["rest", "task"]


def test_cli_reports_a_broken_recording(tmp_path, capsys):
    assert main(["plot", str(tmp_path / "missing")]) == 2
    assert "rr.csv: file not found" in capsys.readouterr().err


def test_report_is_a_single_self_contained_page(steady_recording, tmp_path, capsys):
    out = tmp_path / "out"

    assert main(["report", str(steady_recording), "--out", str(out), "--title", "Session 1"]) == 0

    page = (out / "report.html").read_text(encoding="utf-8")
    assert "<h1>Session 1</h1>" in page
    assert page.count('src="data:image/png;base64,') == 4
    assert "<td>rest</td>" in page and "<td>task</td>" in page
    assert 'src="http' not in page and "<script" not in page


def test_report_uses_a_custom_file_name(steady_recording, tmp_path, capsys):
    out = tmp_path / "site"

    assert main(["report", str(steady_recording), "--out", str(out), "--name", "index.html"]) == 0

    assert (out / "index.html").exists()
    assert "<h1>steady</h1>" in (out / "index.html").read_text(encoding="utf-8")


def test_report_reports_a_broken_recording(tmp_path, capsys):
    assert main(["report", str(tmp_path / "missing")]) == 2
