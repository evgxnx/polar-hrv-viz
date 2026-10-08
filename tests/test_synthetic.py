from __future__ import annotations

import numpy as np
import pytest

from polar_hrv_viz.cli import main
from polar_hrv_viz.io import load_recording
from polar_hrv_viz.processing import flag_artifacts, phase_summary
from polar_hrv_viz.synthetic import DEFAULT_PROTOCOL, PhaseSpec, generate


@pytest.fixture(scope="module")
def recording():
    return generate(seed=1)


def test_same_seed_gives_the_same_recording():
    assert generate(seed=3).rr.equals(generate(seed=3).rr)
    assert not generate(seed=3).rr.equals(generate(seed=4).rr)


def test_phases_follow_the_protocol(recording):
    assert recording.phases["phase"].tolist() == [p.name for p in DEFAULT_PROTOCOL]
    assert recording.phases["end_s"].iloc[-1] == sum(p.duration_s for p in DEFAULT_PROTOCOL)
    assert recording.rr["t_s"].iloc[-1] <= recording.phases["end_s"].iloc[-1]


def test_beat_times_are_the_running_sum_of_intervals(recording):
    gaps = np.diff(recording.rr["t_s"].to_numpy()) * 1000
    assert gaps == pytest.approx(recording.rr["rr_ms"].to_numpy()[1:], abs=1.5)


def test_phase_means_match_the_protocol(recording):
    summary = phase_summary(flag_artifacts(recording.rr), recording.hr, recording.phases)
    for spec, row in zip(DEFAULT_PROTOCOL, summary.itertuples(), strict=True):
        assert row.mean_rr_ms == pytest.approx(spec.mean_rr_ms, rel=0.04)
        assert row.mean_hr_bpm == pytest.approx(60000 / spec.mean_rr_ms, rel=0.05)


def test_injected_artifacts_are_mostly_found():
    protocol = (PhaseSpec("noisy", 600, 900, 20, 10, 5, 0.1),)
    rec = generate(protocol, seed=2)
    flags = flag_artifacts(rec.rr)["artifact"]
    true_rr = 900 + 20 + 10 + 3 * 12

    injected = (rec.rr["rr_ms"] > true_rr * 1.2) | (rec.rr["rr_ms"] < 900 * 0.6)
    assert injected.sum() > 20
    assert flags[injected].mean() > 0.9
    assert flags[~injected].mean() < 0.1


def test_motion_is_higher_in_the_standup_phase(recording):
    m = recording.motion
    rest = m.loc[m["t_s"] < 300, "acc_rms_mg"].mean()
    standup = m.loc[m["t_s"] >= 1200, "acc_rms_mg"].mean()
    assert standup > 5 * rest


def test_synth_command_writes_a_loadable_recording(tmp_path):
    assert main(["synth", str(tmp_path / "syn"), "--seed", "5"]) == 0

    rec = load_recording(tmp_path / "syn")
    assert rec.rr.equals(generate(seed=5).rr)
