from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .io import Recording


@dataclass(frozen=True)
class PhaseSpec:
    name: str
    duration_s: float
    mean_rr_ms: float
    hf_amp_ms: float
    lf_amp_ms: float
    motion_mg: float
    artifact_rate: float


DEFAULT_PROTOCOL = (
    PhaseSpec("rest", 300, 950, 45, 25, 3, 0.01),
    PhaseSpec("task", 300, 800, 15, 30, 4, 0.02),
    PhaseSpec("recovery", 300, 900, 35, 25, 3, 0.01),
    PhaseSpec("typing", 300, 860, 20, 25, 18, 0.05),
    PhaseSpec("standup", 180, 760, 15, 20, 60, 0.20),
)

BREATHING_HZ = 0.25
MAYER_HZ = 0.1
NOISE_MS = 12
HR_WINDOW_S = 5
TRANSITION_S = 20


def _phase_table(protocol: tuple[PhaseSpec, ...]) -> pd.DataFrame:
    ends = np.cumsum([p.duration_s for p in protocol])
    starts = np.concatenate([[0.0], ends[:-1]])
    return pd.DataFrame(
        {"phase": [p.name for p in protocol], "start_s": starts, "end_s": ends.astype(float)}
    )


def _at(t: float, phases: pd.DataFrame, protocol: tuple[PhaseSpec, ...]) -> PhaseSpec:
    i = int(np.searchsorted(phases["end_s"].to_numpy(), t, side="right"))
    return protocol[min(i, len(protocol) - 1)]


def _smooth_mean(t: float, phases: pd.DataFrame, protocol: tuple[PhaseSpec, ...]) -> float:
    current = _at(t, phases, protocol)
    i = protocol.index(current)
    if i == 0:
        return current.mean_rr_ms
    since = t - phases["start_s"].iloc[i]
    if since >= TRANSITION_S:
        return current.mean_rr_ms
    w = since / TRANSITION_S
    return (1 - w) * protocol[i - 1].mean_rr_ms + w * current.mean_rr_ms


def generate(protocol: tuple[PhaseSpec, ...] = DEFAULT_PROTOCOL, seed: int = 0) -> Recording:
    rng = np.random.default_rng(seed)
    phases = _phase_table(protocol)
    total = float(phases["end_s"].iloc[-1])
    lf_phase = rng.uniform(0, 2 * np.pi)

    times, rr, blocker = [], [], []
    t = 0.0
    while True:
        spec = _at(t, phases, protocol)
        value = (
            _smooth_mean(t, phases, protocol)
            + spec.hf_amp_ms * np.sin(2 * np.pi * BREATHING_HZ * t)
            + spec.lf_amp_ms * np.sin(2 * np.pi * MAYER_HZ * t + lf_phase)
            + rng.normal(0, NOISE_MS)
        )
        flagged = 0
        if rng.random() < spec.artifact_rate:
            value *= rng.choice([0.55, 1.8, 2.0])
            flagged = int(rng.random() < 0.5)
        if t + value / 1000 > total:
            break
        t += value / 1000
        times.append(t)
        rr.append(round(value))
        blocker.append(flagged)

    rr_df = pd.DataFrame({"t_s": np.round(times, 3), "rr_ms": rr, "blocker": blocker})

    seconds = np.arange(HR_WINDOW_S, int(total), dtype=float)
    beat_t = rr_df["t_s"].to_numpy()
    true_rr = pd.Series(rr, dtype=float).where(rr_df["blocker"] == 0)
    hr = []
    for s in seconds:
        window = true_rr[(beat_t > s - HR_WINDOW_S) & (beat_t <= s)].dropna()
        hr.append(round(60000 / window.median()) if len(window) else np.nan)
    hr_df = pd.DataFrame({"t_s": seconds, "hr_bpm": hr}).dropna()

    motion_t = np.arange(0, int(total), dtype=float)
    level = np.array([_at(s, phases, protocol).motion_mg for s in motion_t])
    motion = level * rng.gamma(2.0, 0.5, size=len(motion_t))
    motion_df = pd.DataFrame({"t_s": motion_t, "acc_rms_mg": np.round(motion, 1)})

    return Recording(rr=rr_df, hr=hr_df.reset_index(drop=True), motion=motion_df, phases=phases)


def write_recording(rec: Recording, directory: str | Path) -> Path:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    rec.rr.to_csv(d / "rr.csv", index=False)
    rec.hr.to_csv(d / "hr.csv", index=False)
    if rec.motion is not None:
        rec.motion.to_csv(d / "motion.csv", index=False)
    if rec.phases is not None:
        rec.phases.to_csv(d / "phases.csv", index=False)
    return d
