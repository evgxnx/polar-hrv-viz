from __future__ import annotations

import html
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from polar_hrv_viz import __version__

FIGURES = [
    ("timeline.png", "Timeline", "Heart rate, RR intervals with flagged artifacts, and motion."),
    ("rr_histogram.png", "RR interval distribution", "Clean beats in 50 ms bins."),
    ("poincare.png", "Poincaré plot", "Each clean beat against the next one, per phase."),
    ("phase_heart_rate.png", "Heart rate by phase", "Heart rate derived from clean RR intervals."),
]

COLUMNS = {
    "phase": "Phase",
    "mean_hr_bpm": "Mean HR, bpm",
    "mean_rr_ms": "Mean RR, ms",
    "rmssd_ms": "RMSSD, ms",
    "beats": "Beats",
    "artifact_share": "Artifacts, %",
}

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
h1 { font-size: 26px; margin: 0 0 6px; }
h2 { font-size: 17px; margin: 0 0 4px; }
p { margin: 0; color: var(--ink-2); }
a { color: var(--accent); }
.lead { margin-bottom: 28px; max-width: 70ch; }
section {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
}
section p { margin-bottom: 14px; }
img { display: block; width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--muted); font-weight: 600; font-size: 13px; }
.scroll { overflow-x: auto; }
footer { color: var(--muted); font-size: 13px; }
"""


def summary_table(path: Path) -> str:
    df = pd.read_csv(path)
    df["artifact_share"] = df["artifact_share"] * 100
    head = "".join(f"<th>{html.escape(label)}</th>" for label in COLUMNS.values())
    rows = []
    for row in df.itertuples(index=False):
        cells = [f"<td>{html.escape(str(row.phase))}</td>"]
        for key in list(COLUMNS)[1:]:
            value = getattr(row, key)
            text = f"{value:.0f}" if key == "beats" else f"{value:.1f}"
            cells.append(f"<td>{text}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build(site: Path) -> Path:
    figures = []
    for file, title, caption in FIGURES:
        if (site / file).exists():
            figures.append(
                f"<section><h2>{title}</h2><p>{caption}</p>"
                f'<img src="{file}" alt="{title}" loading="lazy"></section>'
            )
    summary = ""
    if (site / "phase_summary.csv").exists():
        summary = (
            "<section><h2>Phase summary</h2>"
            '<p>Also as <a href="phase_summary.csv">CSV</a>.</p>'
            f'<div class="scroll">{summary_table(site / "phase_summary.csv")}</div></section>'
        )
    built = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>polar-hrv-viz gallery</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>polar-hrv-viz gallery</h1>
<p class="lead">Figures rendered by CI from a synthetic five-phase recording
(<a href="synthetic/rr.csv">rr.csv</a>, <a href="synthetic/hr.csv">hr.csv</a>,
<a href="synthetic/motion.csv">motion.csv</a>, <a href="synthetic/phases.csv">phases.csv</a>).
The data are generated, not measured.</p>
{summary}
{"".join(figures)}
<footer>polar-hrv-viz {__version__} · built {built}</footer>
</main>
</body>
</html>
"""
    out = site / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(f"wrote {build(Path(sys.argv[1] if len(sys.argv) > 1 else 'site'))}")
