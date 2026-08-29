# PROTOTYPE / THROWAWAY — backend comparison

This directory is an isolated technical-selection prototype. It is not part of
the production `interactive_plotting` package and should be deleted after the
selection decision. No production abstraction is shared beyond the tiny
deterministic data generator in `data.py`.

## Question

Which existing toolkit is closest to: an upstream Python script passes curve
data, a Windows desktop window shows a 3×2 six-panel figure, and interaction is
similar to a MATLAB Figure?

## Shared fixture

All candidates use `make_demo_data(seed=7)`: 6 panels × 2 curves × 100 points,
with identical labels, colors, and shape. `run_demo.py --help` is the single
launcher entry point:

```console
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/dataanalysis-mpl \
  venv/bin/python -m prototypes.plot_backend_comparison.run_demo --help
PYTHONPATH=. venv/bin/python -m prototypes.plot_backend_comparison.run_demo matplotlib --smoke
PYTHONPATH=. venv/bin/python -m prototypes.plot_backend_comparison.smoke
```

Use `python -m prototypes.plot_backend_comparison.run_demo {silx|plotpy|matplotlib}`
for a GUI attempt. Set `QT_API=pyqt6` (or `pyside6`) for the Qt candidates when
more than one Qt binding is installed. No macOS native GUI was started during
this prototype.

## Candidate notes

| Candidate | Native strengths observed/expected | Prototype glue | Gaps / evidence |
| --- | --- | --- | --- |
| silx + PyQt6 (original request was PySide6) | `PlotWindow` gives curves, axes, pan/zoom/reset-style toolbar and a Qt widget; six widgets fit naturally in a Qt grid | Qt main window/grid, titles, resetZoom and offscreen event processing; click tooltip/focus are intentionally minimal | Offscreen six-panel build/close passed with silx 3.1.1 + PyQt6; legend/point tooltip/maximize semantics need a real Qt run |
| PlotPy + PyQt6 (original request was PySide6) | `PlotWindow`/`PlotWidget` gives curve tools and toolbar; Qt embedding is straightforward | six windows in a grid; titles and colors | Offscreen six-panel build/close passed with plotpy 2.11.0; selection/tooltip, whole-legend drag and per-panel maximize need backend-specific event glue |
| Matplotlib + mplcursors + QtAgg | Existing plotting implementation is closest to requested artists/formatters; mplcursors supplies click selection/annotation; Matplotlib legend is draggable | click-only white Frame/Value annotation, double-click focus, Esc restore, legend draggable | `mplcursors` 0.7.1 and PyQt6 QtAgg offscreen build passed; no real Windows GUI run |

## Dependency and Windows expectations

The attempted venv install first requested `silx plotpy PySide6`. The first attempt
failed with PyPI certificate verification; a trusted-host retry downloaded
metadata and macOS wheels (`silx 3.1.1`, `plotpy 2.11.0`, `PySide6 6.11.2`) but
was cancelled after PySide6 Addons (332 MB) reported roughly 65 minutes at the
observed transfer rate. No PySide6 package remained installed. A smaller Qt
binding was then used: PyQt6 6.11.0 + PyQt6-Qt6 6.11.2 + sip 13.12.0 installed
in 122 seconds; silx 3.1.1 and plotpy 2.11.0 installed with their dependency
trees. silx additionally needs `qtawesome` for `PlotWindow` imports, which is
recorded as a follow-up dependency if the GUI smoke requires it. Existing
versions include Python 3.13.3, Matplotlib 3.10.8, NumPy 2.4.4, and
mplcursors 0.7.1.

These are macOS wheel observations only. They are not Windows evidence.
Windows validation still needs a clean Python/venv, a PyQt6 or PySide6 wheel, Qt plugin
deployment, DPI/font check, and real event-loop run. PlotPy/silx also bring
larger dependency trees than the Matplotlib candidate.

## Provisional selection signal

Matplotlib has the lowest incremental dependency cost and already matches the
existing figure semantics, but still needs QtAgg/PyQt6 (or PySide6) packaging
and GUI verification. silx and PlotPy may offer stronger native desktop toolbars, yet
both require a larger Qt/scientific stack and more glue for a six-panel,
single-tooltip, per-panel-focus contract. This is a provisional prototype
signal, not a Windows acceptance result.
