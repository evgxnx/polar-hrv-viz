from __future__ import annotations

import numpy as np
import pandas as pd

RR_RANGE_MS = (300.0, 2000.0)
LOCAL_WINDOW = 11
LOCAL_TOLERANCE = 0.20


def flag_artifacts(rr: pd.DataFrame) -> pd.DataFrame:
    out = rr.copy()
    values = out["rr_ms"].astype(float)
    lo, hi = RR_RANGE_MS
    out_of_range = (values < lo) | (values > hi)
    local = values.where(~out_of_range).rolling(LOCAL_WINDOW, center=True, min_periods=1).median()
    deviates = (values - local).abs() > LOCAL_TOLERANCE * local
    flagged = out["blocker"].fillna(0).astype(bool) if "blocker" in out else False
    out["artifact"] = out_of_range | deviates | flagged
    return out


def assign_phase(t_s: pd.Series, phases: pd.DataFrame | None) -> pd.Series:
    result = pd.Series(np.nan, index=t_s.index, dtype=object)
    if phases is None:
        return result
    for row in phases.itertuples(index=False):
        inside = (t_s >= row.start_s) & (t_s < row.end_s)
        result[inside] = row.phase
    return result


def rmssd(rr_ms: np.ndarray) -> float:
    if len(rr_ms) < 2:
        return float("nan")
    return float(np.sqrt(np.mean(np.diff(rr_ms) ** 2)))


def phase_summary(rr: pd.DataFrame, hr: pd.DataFrame, phases: pd.DataFrame) -> pd.DataFrame:
    rr = rr if "artifact" in rr else flag_artifacts(rr)
    rr_phase = assign_phase(rr["t_s"], phases)
    hr_phase = assign_phase(hr["t_s"], phases)
    rows = []
    for name in phases["phase"]:
        beats = rr[rr_phase == name]
        clean = ~beats["artifact"].to_numpy()
        values = beats["rr_ms"].to_numpy(dtype=float)
        pairs = clean[1:] & clean[:-1]
        diffs = np.diff(values)[pairs]
        rows.append(
            {
                "phase": name,
                "mean_hr_bpm": hr.loc[hr_phase == name, "hr_bpm"].mean(),
                "mean_rr_ms": values[clean].mean() if clean.any() else np.nan,
                "rmssd_ms": float(np.sqrt(np.mean(diffs**2))) if len(diffs) else np.nan,
                "beats": len(beats),
                "artifact_share": float(1 - clean.mean()) if len(beats) else np.nan,
            }
        )
    return pd.DataFrame(rows)
