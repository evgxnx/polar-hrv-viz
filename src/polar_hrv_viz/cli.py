from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from .io import RecordingError, load_recording
from .plots import plot_phase_heart_rate, plot_poincare, plot_rr_histogram, plot_timeline
from .processing import flag_artifacts, phase_summary
from .synthetic import generate, write_recording


def _plot(args: argparse.Namespace) -> int:
    try:
        rec = load_recording(args.recording)
    except RecordingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    figures = {
        "timeline": plot_timeline(rec, title=args.recording.name),
        "rr_histogram": plot_rr_histogram(rec),
        "poincare": plot_poincare(rec),
        "phase_heart_rate": plot_phase_heart_rate(rec),
    }
    for name, fig in figures.items():
        path = args.out / f"{name}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"wrote {path}")

    if rec.phases is not None:
        summary = phase_summary(flag_artifacts(rec.rr), rec.hr, rec.phases)
        summary.to_csv(args.out / "phase_summary.csv", index=False, float_format="%.3f")
        print(summary.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    return 0


def _synth(args: argparse.Namespace) -> int:
    rec = generate(seed=args.seed)
    write_recording(rec, args.out)
    print(f"wrote synthetic recording to {args.out} ({len(rec.rr)} beats)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="polar-hrv-viz")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plot", help="render figures and a phase summary for one recording")
    p.add_argument(
        "recording", type=Path, help="directory with rr.csv, hr.csv[, motion.csv, phases.csv]"
    )
    p.add_argument("--out", type=Path, default=Path("out"), help="output directory (default: out)")
    p.set_defaults(run=_plot)

    s = sub.add_parser("synth", help="write a synthetic recording with a five-phase protocol")
    s.add_argument("out", type=Path, help="directory to write the CSV files to")
    s.add_argument("--seed", type=int, default=0, help="random seed (default: 0)")
    s.set_defaults(run=_synth)

    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
