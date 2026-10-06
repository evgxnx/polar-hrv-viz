from __future__ import annotations

import pytest

from polar_hrv_viz.io import RecordingError, load_recording

from .conftest import write_recording


def test_loads_all_files(steady_recording):
    rec = load_recording(steady_recording)

    assert len(rec.rr) == 120
    assert rec.motion is not None
    assert list(rec.phases["phase"]) == ["rest", "task"]
    assert rec.duration_s == pytest.approx(120.0)


def test_motion_and_phases_are_optional(tmp_path):
    rec = load_recording(write_recording(tmp_path / "r", [1000.0] * 10, motion=False))

    assert rec.motion is None
    assert rec.phases is None


def test_missing_rr_file_is_reported(steady_recording):
    (steady_recording / "rr.csv").unlink()

    with pytest.raises(RecordingError, match="rr.csv: file not found"):
        load_recording(steady_recording)


def test_missing_column_is_reported(steady_recording):
    (steady_recording / "hr.csv").write_text("t_s,bpm\n1,60\n")

    with pytest.raises(RecordingError, match=r"hr.csv: missing columns \['hr_bpm'\]"):
        load_recording(steady_recording)


def test_broken_rows_are_dropped_and_rows_sorted(steady_recording):
    (steady_recording / "rr.csv").write_text("t_s,rr_ms\n2.0,1000\noops,1000\n1.0,1000\n3.0,\n")

    rec = load_recording(steady_recording)

    assert rec.rr["t_s"].tolist() == [1.0, 2.0]


def test_file_without_valid_rows_is_an_error(steady_recording):
    (steady_recording / "rr.csv").write_text("t_s,rr_ms\nx,y\n")

    with pytest.raises(RecordingError, match="no valid rows"):
        load_recording(steady_recording)


@pytest.mark.parametrize(
    ("phases", "message"),
    [
        ("phase,start_s,end_s\na,0,10\nb,5,20\n", "overlap"),
        ("phase,start_s,end_s\na,10,10\n", "end after it starts"),
        ("phase,start_s,end_s\na,zero,10\n", "must be numbers"),
    ],
)
def test_invalid_phases_are_rejected(steady_recording, phases, message):
    (steady_recording / "phases.csv").write_text(phases)

    with pytest.raises(RecordingError, match=message):
        load_recording(steady_recording)
