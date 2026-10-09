from __future__ import annotations

import pytest

from polar_hrv_viz.io import load_recording
from polar_hrv_viz.processing import flag_artifacts, phase_summary
from polar_hrv_viz.report import PNG_SIGNATURE, build_report, display_width, overview

from .conftest import write_recording


def test_overview_of_a_steady_rhythm(steady_recording):
    tiles = {
        label: (value, unit) for label, value, unit in overview(load_recording(steady_recording))
    }

    assert tiles["Duration"] == ("2.0", "min")
    assert tiles["Beats"] == ("120", "")
    assert tiles["Artifacts"] == ("0.0", "%")
    assert tiles["Mean heart rate"] == ("60.0", "bpm")
    assert tiles["RMSSD"] == ("0.0", "ms")


def test_text_is_escaped(tmp_path):
    rec = load_recording(
        write_recording(tmp_path / "r", [1000.0] * 60, phases=[("<b>rest</b>", 0, 61)])
    )
    summary = phase_summary(flag_artifacts(rec.rr), rec.hr, rec.phases)

    page = build_report(rec, {}, summary, title="A & B", subtitle="<script>")

    assert "<h1>A &amp; B</h1>" in page
    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "<td>&lt;b&gt;rest&lt;/b&gt;</td>" in page


def test_report_without_phases_has_no_summary_table(tmp_path):
    rec = load_recording(write_recording(tmp_path / "r", [1000.0] * 60))

    page = build_report(rec, {"timeline": b"png"})

    assert "<table" not in page
    assert page.count("data:image/png;base64,") == 1


@pytest.mark.parametrize("missing", ["rr_histogram", "poincare"])
def test_only_given_figures_are_embedded(steady_recording, missing):
    images = {k: b"png" for k in ["timeline", "rr_histogram", "poincare", "phase_heart_rate"]}
    del images[missing]

    page = build_report(load_recording(steady_recording), images)

    assert page.count("data:image/png;base64,") == 3


def test_figures_are_shown_at_their_physical_size():
    png = (
        PNG_SIGNATURE + b"\x00\x00\x00\rIHDR" + (1050).to_bytes(4, "big") + (540).to_bytes(4, "big")
    )

    assert display_width(png) == 672
    assert display_width(b"not a png") is None
