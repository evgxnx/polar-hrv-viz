from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .io import Recording, RecordingError, load_recording
from .plots import plot_phase_heart_rate, plot_poincare, plot_rr_histogram, plot_timeline
from .processing import flag_artifacts, phase_summary
from .report import build_report
from .style import DPI
from .synthetic import generate, write_recording


def _load(path: Path) -> Recording | None:
    try:
        return load_recording(path)
    except RecordingError as e:
        print(f"error: {e}", file=sys.stderr)
        return None


def _render(rec: Recording, name: str, out: Path) -> tuple[dict[str, bytes], pd.DataFrame | None]:
    out.mkdir(parents=True, exist_ok=True)
    figures = {
        "timeline": plot_timeline(rec, title=name),
        "rr_histogram": plot_rr_histogram(rec),
        "poincare": plot_poincare(rec),
        "phase_heart_rate": plot_phase_heart_rate(rec),
    }
    images = {}
    for key, fig in figures.items():
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=DPI)
        plt.close(fig)
        images[key] = buffer.getvalue()
        path = out / f"{key}.png"
        path.write_bytes(images[key])
        print(f"wrote {path}")

    summary = None
    if rec.phases is not None:
        summary = phase_summary(flag_artifacts(rec.rr), rec.hr, rec.phases)
        summary.to_csv(out / "phase_summary.csv", index=False, float_format="%.3f")
        print(summary.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    return images, summary


def _plot(args: argparse.Namespace) -> int:
    rec = _load(args.recording)
    if rec is None:
        return 2
    _render(rec, args.recording.name, args.out)
    return 0


def _report(args: argparse.Namespace) -> int:
    rec = _load(args.recording)
    if rec is None:
        return 2
    title = args.title or args.recording.resolve().name
    images, summary = _render(rec, title, args.out)
    page = build_report(rec, images, summary, title=title, subtitle=args.subtitle)
    path = args.out / args.name
    path.write_text(page, encoding="utf-8")
    print(f"wrote {path}")
    return 0


def _synth(args: argparse.Namespace) -> int:
    rec = generate(seed=args.seed)
    write_recording(rec, args.out)
    print(f"wrote synthetic recording to {args.out} ({len(rec.rr)} beats)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="polar-hrv-viz")
    sub = parser.add_subparsers(dest="command", required=True)
    recording_help = "directory with rr.csv, hr.csv[, motion.csv, phases.csv]"
    out_help = "output directory (default: out)"

    p = sub.add_parser("plot", help="render figures and a phase summary for one recording")
    p.add_argument("recording", type=Path, help=recording_help)
    p.add_argument("--out", type=Path, default=Path("out"), help=out_help)
    p.set_defaults(run=_plot)

    r = sub.add_parser("report", help="render figures and a self-contained HTML report")
    r.add_argument("recording", type=Path, help=recording_help)
    r.add_argument("--out", type=Path, default=Path("out"), help=out_help)
    r.add_argument("--name", default="report.html", help="report file name (default: report.html)")
    r.add_argument("--title", help="report title (default: the recording directory name)")
    r.add_argument("--subtitle", help="one line under the title")
    r.set_defaults(run=_report)

    s = sub.add_parser("synth", help="write a synthetic recording with a five-phase protocol")
    s.add_argument("out", type=Path, help="directory to write the CSV files to")
    s.add_argument("--seed", type=int, default=0, help="random seed (default: 0)")
    s.set_defaults(run=_synth)

    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
