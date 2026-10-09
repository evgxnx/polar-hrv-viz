# polar-hrv-viz

[![CI](https://github.com/evgxnx/polar-hrv-viz/actions/workflows/ci.yml/badge.svg)](https://github.com/evgxnx/polar-hrv-viz/actions/workflows/ci.yml)
[![Gallery](https://github.com/evgxnx/polar-hrv-viz/actions/workflows/pages.yml/badge.svg)](https://evgxnx.github.io/polar-hrv-viz/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11–3.13](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)

Visualise heart rate, RR intervals and motion recorded with a Polar optical sensor (Verity Sense, OH1), split by the phases of an experiment.

The package was written for research on **multimodal emotional AI for assessing the professional preparation of educators**. One of the modalities in that work is cardiac activity measured during an assessment session: rest, a task, recovery and so on. Before any model looks at this signal, a researcher needs to see it, to check its quality and to compare the phases. This tool does exactly that and nothing more.

**[Open the gallery →](https://evgxnx.github.io/polar-hrv-viz/)** (rebuilt by CI on every push from a synthetic recording)

![Timeline of a synthetic recording](https://evgxnx.github.io/polar-hrv-viz/timeline.png)

## Features

- Loads a recording from plain CSV files and validates it: missing files and columns, broken rows, overlapping phases.
- Flags RR artifacts: physiologically impossible intervals, outliers against the local median, and beats the sensor itself marked as unreliable.
- Summarises every phase: mean heart rate, mean RR, RMSSD and the share of artifacts.
- Renders four figures in a light, print-friendly style:

  | Figure | What it shows |
  |---|---|
  | `timeline.png` | Heart rate, RR intervals with artifacts marked, and motion on one time axis, phases shaded |
  | `rr_histogram.png` | Distribution of clean RR intervals in 50 ms bins, with the mode labelled |
  | `poincare.png` | Each clean RR interval against the next one, one panel per phase, with SD1 and SD2 |
  | `phase_heart_rate.png` | Heart rate derived from clean RR intervals, one box per phase |

- Generates a reproducible synthetic recording with a five-phase protocol, for demos and tests.

## Installation

Python 3.11 or newer and [uv](https://docs.astral.sh/uv/) are required.

```bash
git clone https://github.com/evgxnx/polar-hrv-viz.git
cd polar-hrv-viz
uv sync
```

A built wheel is also attached to every [release](https://github.com/evgxnx/polar-hrv-viz/releases):

```bash
pip install polar_hrv_viz-0.1.0-py3-none-any.whl
```

## Quick start

```bash
uv run polar-hrv-viz synth data/synthetic
uv run polar-hrv-viz plot data/synthetic --out out/synthetic
```

The second command writes the four figures and `phase_summary.csv` to `out/synthetic` and prints the summary:

```
   phase  mean_hr_bpm  mean_rr_ms  rmssd_ms  beats  artifact_share
    rest        63.23      949.21     48.89    314            0.01
    task        74.56      803.94     23.46    370            0.03
recovery        67.16      894.42     37.19    332            0.02
  typing        69.64      859.44     26.49    343            0.06
 standup        76.04      775.09     21.69    213            0.19
```

The functions can also be used from Python:

```python
from polar_hrv_viz.io import load_recording
from polar_hrv_viz.plots import plot_poincare

rec = load_recording("data/synthetic")
plot_poincare(rec).savefig("poincare.png", dpi=150)
```

## Input format

A recording is a directory of CSV files. Times are in seconds from the start of the recording.

| File | Required columns | Optional columns | Notes |
|---|---|---|---|
| `rr.csv` | `t_s`, `rr_ms` | `blocker` | One row per beat; `t_s` is the end of the interval; `blocker = 1` if the sensor marked the beat as unreliable |
| `hr.csv` | `t_s`, `hr_bpm` | | Heart rate reported by the sensor |
| `motion.csv` | `t_s`, `acc_rms_mg` | | Optional. Accelerometer magnitude, milli-g |
| `phases.csv` | `phase`, `start_s`, `end_s` | | Optional. Non-overlapping intervals, start inclusive |

Rows whose values are not numbers are dropped. A file left with no valid rows is an error.

Recordings stay on your machine: the `data/` directory is ignored by git.

## Method

**Artifacts.** A beat is flagged when any of these holds:

1. its interval is outside 300–2000 ms (200–30 bpm);
2. it differs by more than 20 % from the median of the 11 beats around it, a local-median variant of the 20 % rule of Malik et al. (1989);
3. the sensor marked it (`blocker = 1`).

Flagged beats are shown as red crosses and become gaps in the RR line. They are excluded from every statistic.

**RMSSD** is the root mean square of differences between consecutive clean beats. A pair that touches an artifact is skipped, so a removed beat never creates a false jump (Task Force, 1996).

**Poincaré descriptors.** For consecutive clean pairs (RR<sub>n</sub>, RR<sub>n+1</sub>):

- SD1 = SD((RR<sub>n+1</sub> − RR<sub>n</sub>) / √2) is the spread across the identity line, short-term variability;
- SD2 = SD((RR<sub>n+1</sub> + RR<sub>n</sub>) / √2) is the spread along it, long-term variability (Brennan et al., 2001).

**Heart rate by phase** is 60000 / RR of clean beats rather than the sensor's own value. Optical sensors keep reporting a heart rate during movement even when the beats behind it are lost. The timeline makes this visible.

**Synthetic recording.** Beats are generated one by one: a phase mean RR with a 20 s transition between phases, respiratory modulation at 0.25 Hz, a Mayer wave at 0.1 Hz and Gaussian noise. Artifacts (missed and extra beats) are injected at a phase-specific rate, half of them marked by the "sensor". The output is fully determined by `--seed`.

## Technology choices

| Choice | Why |
|---|---|
| **Python** | The standard language for scientific data processing. The rest of the research pipeline (signal processing, ML models) is in Python too, so this module plugs into it without glue. |
| **pandas** | Recordings are small time-indexed tables. CSV parsing with type coercion, rolling medians and grouping by phase are one-liners. |
| **NumPy** | Vectorised arithmetic for RMSSD, Poincaré descriptors and the synthetic generator. |
| **matplotlib** | Static, publication-quality figures that go straight into a paper or a thesis. It is deterministic and headless (`Agg` backend), so figures render identically in CI. One `rc_context` keeps the whole style in a single module. |
| **argparse** | The command line has two subcommands. The standard library is enough, and it adds no dependency. |
| **uv** | One tool for the virtual environment, the lock file (`uv.lock`) and the build. `uv sync --locked` in CI reproduces the exact environment from the lock file. |
| **hatchling** | A minimal standards-based (PEP 517) build backend with a `src/` layout and no configuration code. |
| **pytest + pytest-cov** | Plain-function tests, fixtures for temporary recordings, parametrised cases. Coverage is enforced at 90 %. |
| **ruff** | Linter and formatter in one fast tool, so style is checked in CI rather than argued about in review. |
| **GitHub Actions** | Hosted next to the code and free for public repositories. It also covers GitHub Pages (gallery) and releases. |

## Testing

```bash
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

The tests use signals whose correct answer is known in advance:

- a perfectly steady rhythm has no artifacts and RMSSD = 0;
- an alternating 1000/1100 ms series has RMSSD = 100 ms and SD1 = 100/√2 ms with SD2 = 0;
- a slow linear drift has SD1 = 0;
- a single missed beat (one doubled interval) is flagged, and the beats around it are not;
- on the synthetic recording, the phase means recover the protocol values, and more than 90 % of the injected artifacts are found.

Input validation, every figure (panels, labels, bar widths, phase titles) and both CLI commands are covered as well.

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | push to `main`, pull requests | ruff lint and format check; pytest with coverage on Python 3.11, 3.12 and 3.13; builds the wheel and sdist, installs the wheel into a clean environment and runs both commands |
| [`pages.yml`](.github/workflows/pages.yml) | push to `main` | generates the synthetic recording, renders all figures and deploys the [gallery](https://evgxnx.github.io/polar-hrv-viz/) to GitHub Pages |
| [`release.yml`](.github/workflows/release.yml) | tag `v*` | runs the tests, checks that the tag matches the package version, builds and publishes a GitHub release with the wheel and sdist |

To release: bump `version` in `pyproject.toml`, commit, then `git tag v0.2.0 && git push --tags`.

## Project structure

```
src/polar_hrv_viz/
  io.py          loading and validation
  processing.py  artifacts, phases, RMSSD, Poincaré descriptors
  plots.py       figures
  style.py       light theme
  synthetic.py   synthetic recording generator
  cli.py         polar-hrv-viz plot | synth
scripts/
  build_gallery.py  HTML page for GitHub Pages
tests/
```

## Limitations

- The tool describes and visualises a signal. It does not diagnose stress or any other state. Phase differences in one recording are not evidence of an effect.
- Optical RR intervals are less accurate than ECG, especially during movement. Read the motion panel together with the RR panel.
- Frequency-domain HRV (LF/HF) is out of scope: it needs longer stationary windows and its interpretation is disputed.
- Converting the export of the Polar Sensor Logger app to this CSV format is not built in yet.

## Citation

If you use this software, please cite it using [CITATION.cff](CITATION.cff) (GitHub shows a "Cite this repository" button).

## References

- Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. *Circulation*, 93(5), 1043–1065.
- Malik, M., Cripps, T., Farrell, T., & Camm, A. J. (1989). Prognostic value of heart rate variability after myocardial infarction. A comparison of different data-processing methods. *Medical & Biological Engineering & Computing*, 27(6), 603–611.
- Brennan, M., Palaniswami, M., & Kamen, P. (2001). Do existing measures of Poincaré plot geometry reflect nonlinear features of heart rate variability? *IEEE Transactions on Biomedical Engineering*, 48(11), 1342–1347.

## License

[MIT](LICENSE) © 2026 Yevgeniy Barkovskiy
