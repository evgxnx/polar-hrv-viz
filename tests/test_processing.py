from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from polar_hrv_viz.processing import assign_phase, flag_artifacts, phase_summary, rmssd


def rr_table(values, blocker=None) -> pd.DataFrame:
    values = np.asarray(values, dtype=float)
    df = pd.DataFrame({"t_s": np.cumsum(values) / 1000, "rr_ms": values})
    if blocker is not None:
        df["blocker"] = blocker
    return df


def test_steady_rhythm_has_no_artifacts():
    assert not flag_artifacts(rr_table([1000.0] * 30))["artifact"].any()


def test_natural_variability_is_not_an_artifact():
    values = 1000 + 100 * np.sin(np.arange(60) / 3)
    assert not flag_artifacts(rr_table(values))["artifact"].any()


@pytest.mark.parametrize("bad", [250.0, 2500.0])
def test_impossible_interval_is_an_artifact(bad):
    values = [1000.0] * 20
    values[10] = bad
    flags = flag_artifacts(rr_table(values))["artifact"]
    assert flags.tolist() == [i == 10 for i in range(20)]


def test_missed_beat_is_an_artifact():
    values = [800.0] * 20
    values[7] = 1600.0
    flags = flag_artifacts(rr_table(values))["artifact"]
    assert flags.tolist() == [i == 7 for i in range(20)]


def test_sensor_flag_is_an_artifact():
    blocker = [0] * 10
    blocker[3] = 1
    flags = flag_artifacts(rr_table([1000.0] * 10, blocker=blocker))["artifact"]
    assert flags.tolist() == [i == 3 for i in range(10)]


def test_assign_phase_uses_half_open_intervals():
    phases = pd.DataFrame({"phase": ["a", "b"], "start_s": [0, 10], "end_s": [10, 20]})
    t = pd.Series([-1.0, 0.0, 9.99, 10.0, 19.99, 20.0])

    assert assign_phase(t, phases).fillna("-").tolist() == ["-", "a", "a", "b", "b", "-"]


def test_rmssd_of_alternating_series():
    assert rmssd(np.array([1000, 1100] * 10, dtype=float)) == pytest.approx(100.0)


def test_rmssd_needs_two_beats():
    assert np.isnan(rmssd(np.array([1000.0])))


def test_phase_summary_values():
    values = np.array([1000.0, 1100.0] * 30)
    rr = rr_table(values)
    hr = pd.DataFrame({"t_s": np.arange(0, 64, dtype=float), "hr_bpm": [60.0] * 30 + [80.0] * 34})
    phases = pd.DataFrame({"phase": ["first", "second"], "start_s": [0, 30], "end_s": [30, 64]})

    summary = phase_summary(rr, hr, phases).set_index("phase")

    assert summary.loc["first", "mean_hr_bpm"] == pytest.approx(60.0)
    assert summary.loc["second", "mean_hr_bpm"] == pytest.approx(80.0)
    assert summary.loc["first", "rmssd_ms"] == pytest.approx(100.0)
    assert summary["beats"].sum() == 60
    assert (summary["artifact_share"] == 0).all()


def test_rmssd_skips_pairs_that_touch_an_artifact():
    values = [1000.0] * 30
    values[15] = 2500.0
    rr = flag_artifacts(rr_table(values))
    hr = pd.DataFrame({"t_s": [0.0], "hr_bpm": [60.0]})
    phases = pd.DataFrame({"phase": ["all"], "start_s": [0], "end_s": [100]})

    row = phase_summary(rr, hr, phases).iloc[0]

    assert row["rmssd_ms"] == pytest.approx(0.0)
    assert row["artifact_share"] == pytest.approx(1 / 30)
