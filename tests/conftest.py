from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def write_recording(
    directory: Path,
    rr_ms: list[float] | np.ndarray,
    *,
    hr_bpm: float = 60.0,
    phases: list[tuple[str, float, float]] | None = None,
    motion: bool = True,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    rr_ms = np.asarray(rr_ms, dtype=float)
    t = np.cumsum(rr_ms) / 1000
    pd.DataFrame({"t_s": t, "rr_ms": rr_ms, "error_ms": 10, "blocker": 0}).to_csv(
        directory / "rr.csv", index=False
    )
    seconds = np.arange(0, int(t[-1]) + 1, dtype=float)
    pd.DataFrame({"t_s": seconds, "hr_bpm": hr_bpm}).to_csv(directory / "hr.csv", index=False)
    if motion:
        pd.DataFrame({"t_s": seconds, "acc_rms_mg": 5.0, "acc_peak_mg": 12.0}).to_csv(
            directory / "motion.csv", index=False
        )
    if phases is not None:
        pd.DataFrame(phases, columns=["phase", "start_s", "end_s"]).to_csv(
            directory / "phases.csv", index=False
        )
    return directory


@pytest.fixture
def steady_recording(tmp_path: Path) -> Path:
    return write_recording(
        tmp_path / "steady", [1000.0] * 120, phases=[("rest", 0, 60), ("task", 60, 121)]
    )
