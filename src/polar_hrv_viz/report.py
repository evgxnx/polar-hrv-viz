from __future__ import annotations

import base64
import html
import struct
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from . import __version__
from .io import Recording
from .processing import clean_pairs, flag_artifacts
from .style import DPI

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CSS_DPI = 96

FIGURES = [
    ("timeline", "Timeline", "Heart rate, RR intervals with flagged artifacts, and motion."),
    ("rr_histogram", "RR interval distribution", "Clean beats in 50 ms bins."),
    ("poincare", "Poincaré plot", "Each clean beat against the next one, per phase."),
    ("phase_heart_rate", "Heart rate by phase", "Heart rate derived from clean RR intervals."),
]

SUMMARY_COLUMNS = {
    "phase": "Phase",
    "mean_hr_bpm": "Mean HR, bpm",
    "mean_rr_ms": "Mean RR, ms",
    "rmssd_ms": "RMSSD, ms",
    "beats": "Beats",
    "artifact_share": "Artifacts, %",
}

METHOD = [
    "A beat is an artifact when its RR interval is outside 300–2000 ms, differs by more "
    "than 20 % from the median of the 11 beats around it, or was marked by the sensor.",
    "Artifacts are excluded from every statistic. RMSSD uses only pairs of consecutive "
    "clean beats.",
    "SD1 and SD2 are the spreads of the Poincaré plot across and along the identity line: "
    "short-term and long-term variability.",
    "Heart rate by phase is 60000 / RR of clean beats, not the value reported by the sensor.",
]

STYLE = """
:root {
  color-scheme: light;
  --surface: #fcfcfb;
  --page: #f9f9f7;
  --ink: #0b0b0b;
  --ink-2: #52514e;
  --muted: #898781;
  --line: #e1e0d9;
  --accent: #2a78d6;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
}
main { max-width: 1080px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { font-size: 26px; margin: 0 0 6px; overflow-wrap: anywhere; }
h2 { font-size: 17px; margin: 0 0 4px; }
p { margin: 0; color: var(--ink-2); }
a { color: var(--accent); }
.lead { margin-bottom: 24px; max-width: 75ch; }
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.tile {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
}
.tile .label { color: var(--muted); font-size: 13px; }
.tile .value { font-size: 24px; font-weight: 600; }
.tile .unit { color: var(--ink-2); font-size: 14px; font-weight: 400; }
section {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
}
section > p { margin-bottom: 14px; }
figure { margin: 0; }
img { display: block; max-width: 100%; height: auto; }
figcaption { color: var(--muted); font-size: 13px; margin-top: 10px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--muted); font-weight: 600; font-size: 13px; }
.scroll { overflow-x: auto; }
ul { margin: 0; padding-left: 20px; color: var(--ink-2); }
li + li { margin-top: 6px; }
footer { color: var(--muted); font-size: 13px; }
@media print {
  body { background: #fff; }
  main { padding: 0; }
  section, .tile { break-inside: avoid; }
}
"""


def _number(value: float, digits: int = 1) -> str:
    return "–" if value is None or np.isnan(value) else f"{value:.{digits}f}"


def overview(rec: Recording) -> list[tuple[str, str, str]]:
    rr = flag_artifacts(rec.rr)
    clean = rr.loc[~rr["artifact"], "rr_ms"].to_numpy(dtype=float)
    current, following = clean_pairs(rr)
    rmssd = float(np.sqrt(np.mean((following - current) ** 2))) if len(current) else np.nan
    mean_hr = float(np.mean(60000 / clean)) if len(clean) else np.nan
    return [
        ("Duration", _number(rec.duration_s / 60), "min"),
        ("Beats", f"{len(rr)}", ""),
        ("Artifacts", _number(100 * rr["artifact"].mean()), "%"),
        ("Mean heart rate", _number(mean_hr), "bpm"),
        ("RMSSD", _number(rmssd), "ms"),
    ]


def _tiles(rec: Recording) -> str:
    tiles = []
    for label, value, unit in overview(rec):
        unit_html = f' <span class="unit">{unit}</span>' if unit else ""
        tiles.append(
            f'<div class="tile"><div class="label">{label}</div>'
            f'<div class="value">{value}{unit_html}</div></div>'
        )
    return f'<div class="tiles">{"".join(tiles)}</div>'


def _summary(summary: pd.DataFrame | None) -> str:
    if summary is None or summary.empty:
        return ""
    head = "".join(f"<th>{label}</th>" for label in SUMMARY_COLUMNS.values())
    rows = []
    for row in summary.itertuples(index=False):
        cells = [f"<td>{html.escape(str(row.phase))}</td>"]
        for key in list(SUMMARY_COLUMNS)[1:]:
            value = getattr(row, key)
            if key == "beats":
                text = f"{value:.0f}"
            elif key == "artifact_share":
                text = _number(100 * value)
            else:
                text = _number(value)
            cells.append(f"<td>{text}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        "<section><h2>Phase summary</h2><p>Statistics of clean beats in each phase.</p>"
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def display_width(png: bytes) -> int | None:
    if not png.startswith(PNG_SIGNATURE) or len(png) < 24:
        return None
    width, _ = struct.unpack(">II", png[16:24])
    return round(width * CSS_DPI / DPI)


def _figures(images: dict[str, bytes]) -> str:
    parts = []
    for key, title, caption in FIGURES:
        if key not in images:
            continue
        data = base64.b64encode(images[key]).decode("ascii")
        width = display_width(images[key])
        size = f' style="width: {width}px"' if width else ""
        parts.append(
            f'<section><figure><img src="data:image/png;base64,{data}" alt="{title}"{size}>'
            f"<figcaption>{caption}</figcaption></figure></section>"
        )
    return "".join(parts)


def build_report(
    rec: Recording,
    images: dict[str, bytes],
    summary: pd.DataFrame | None = None,
    title: str = "Recording",
    subtitle: str | None = None,
) -> str:
    built = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    phases = "" if rec.phases is None else f", {len(rec.phases)} phases"
    lead = html.escape(subtitle) if subtitle else f"Polar optical sensor recording{phases}."
    method = "".join(f"<li>{item}</li>" for item in METHOD)
    name = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · polar-hrv-viz</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>{name}</h1>
<p class="lead">{lead}</p>
{_tiles(rec)}
{_summary(summary)}
{_figures(images)}
<section><h2>Method</h2><ul>{method}</ul></section>
<footer>polar-hrv-viz {__version__} · generated {built} ·
descriptive only, not a diagnosis</footer>
</main>
</body>
</html>
"""
