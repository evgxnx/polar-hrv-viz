from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

RR_COLUMNS = ["t_s", "rr_ms"]
HR_COLUMNS = ["t_s", "hr_bpm"]
MOTION_COLUMNS = ["t_s", "acc_rms_mg"]
PHASE_COLUMNS = ["phase", "start_s", "end_s"]


class RecordingError(ValueError):
    pass


@dataclass
class Recording:
    rr: pd.DataFrame
    hr: pd.DataFrame
    motion: pd.DataFrame | None = None
    phases: pd.DataFrame | None = None

    @property
    def duration_s(self) -> float:
        ends = [self.rr["t_s"].max(), self.hr["t_s"].max()]
        if self.motion is not None and not self.motion.empty:
            ends.append(self.motion["t_s"].max())
        return float(max(ends))


def _read(path: Path, required: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise RecordingError(f"{path.name}: file not found")
    df = pd.read_csv(path)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RecordingError(f"{path.name}: missing columns {missing}")
    return df


def _numeric(df: pd.DataFrame, name: str, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=columns)
    if df.empty:
        raise RecordingError(f"{name}: no valid rows")
    return df.sort_values("t_s", kind="stable").reset_index(drop=True)


def load_phases(path: Path) -> pd.DataFrame:
    df = _read(path, PHASE_COLUMNS)
    df = df.copy()
    df["start_s"] = pd.to_numeric(df["start_s"], errors="coerce")
    df["end_s"] = pd.to_numeric(df["end_s"], errors="coerce")
    if df[["start_s", "end_s"]].isna().any().any():
        raise RecordingError(f"{path.name}: start_s/end_s must be numbers")
    if (df["end_s"] <= df["start_s"]).any():
        raise RecordingError(f"{path.name}: every phase must end after it starts")
    df = df.sort_values("start_s").reset_index(drop=True)
    if (df["start_s"].iloc[1:].to_numpy() < df["end_s"].iloc[:-1].to_numpy()).any():
        raise RecordingError(f"{path.name}: phases overlap")
    return df


def load_recording(directory: str | Path) -> Recording:
    d = Path(directory)
    rr = _numeric(_read(d / "rr.csv", RR_COLUMNS), "rr.csv", RR_COLUMNS)
    hr = _numeric(_read(d / "hr.csv", HR_COLUMNS), "hr.csv", HR_COLUMNS)
    motion = None
    if (d / "motion.csv").exists():
        motion = _numeric(_read(d / "motion.csv", MOTION_COLUMNS), "motion.csv", MOTION_COLUMNS)
    phases = load_phases(d / "phases.csv") if (d / "phases.csv").exists() else None
    return Recording(rr=rr, hr=hr, motion=motion, phases=phases)
