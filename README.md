# Interactive plotting

The package has three layers: `model` defines the temporary internal
`SeriesData` format, `core` owns reusable Matplotlib construction and cursor
interactions, and `demo` owns artificial data plus the only blocking
`plt.show()` call. The real producer's format is still unknown; a future
adapter should map it into `SeriesData` without changing the plotting core.

## Reusable API

Callers construct series, retain the returned session for the whole figure
lifetime, and decide when to show or close it:

```python
from interactive_plotting import SeriesData, create_interactive_plot

series = [SeriesData(frames=[0, 1], values=[0.0, 1.0], label="example")]
session = create_interactive_plot(series)
session.figure.show()
session.close()
```

`PlotSession` exposes `disconnect()`, `close()`,
`remove_selected_cursor()`, `clear_extra_cursors()`,
`toggle_axes_maximized(axis)`, and `restore_layout()`. Disconnect and close are
idempotent; close also removes the figure from Matplotlib. `SeriesData` copies
its arrays and makes them read-only. Dynamic updates are intentionally
unsupported for now: create a new session when the source data changes.

## Data rules

- `frames` and `values` must be non-empty, one-dimensional, real numeric arrays
  of equal length. Frames must all be finite.
- Non-finite values are missing points: lines break at them, and scatter,
  hit-testing, and tooltips skip them. Every series needs at least one finite
  value.

The normalized arrays are an internal plotting representation, not a promise
about the future business-data interface.

## Interaction

- Hover highlights only the series whose data point lies within the shared hit
  radius (6 px, the same radius clicks use): that series' unlocked cursor
  becomes visible, snaps to the point, and takes the gold selection. Series
  are independent — hovering never moves or reveals another series' cursor.
  Beyond the radius from every point there is no highlight at all; an
  unlocked cursor hides again once the mouse leaves the radius, and the
  figure starts with every cursor hidden. Locked cursors stay visible.
- Left click selects that series' permanent default cursor, toggles its locked
  state, and shows the figure's only tooltip at the clicked point. The next
  data-point click replaces that tooltip, including across subplots. Locked
  cursors ignore mouse-hover following but stay keyboard-navigable while
  selected.
- Shift+left click adds a locked extra cursor. Delete/Backspace removes the
  selected extra cursor. Default cursors cannot be deleted.
- Left/Right and Home/End move only the cursor anchored by the last left
  click (a data-point click, a Shift+left-click extra cursor, or a click on
  its tooltip), whether it is locked or not, without moving any other
  series' cursor. Hovering moves the gold selection but never the keyboard
  target. While a session is active, Left/Right/Home/Backspace are detached
  from the Matplotlib navigation toolbar's view history; the default
  bindings return once the last session disconnects.
- Drag a visible tooltip to reposition its text. Cursor interaction pauses
  while tooltip dragging or toolbar pan/zoom is active.
- Double-click a subplot background to make that axes fill the current
  Matplotlib figure. Double-click it again to restore the exact captured
  layout. Programmatic switching restores the previous axes before maximizing
  the next one.
- While an axes is maximized, Esc restores the six-panel layout and preserves
  extra cursors. Outside maximized mode, Esc clears all extra cursors.
- Drag anywhere on a legend box or its labels to reposition the whole legend.
  Legend and tooltip gestures take priority over subplot maximization.

Tooltips stay hidden during initialization and hover. A data-point left click
shows one white tooltip containing only `Frame` and `Value`, both formatted by
the corresponding axis formatter. Hover never moves a tooltip; keyboard
movement of the clicked cursor carries its visible tooltip to the new point
and refreshes the values. Cursors use only point markers and tooltips. A gold
marker edge identifies the selected cursor, while a square marker identifies
a locked cursor.

## GUI stack

Interactive windows run Matplotlib's QtAgg backend on PySide6, the only Qt
binding declared and installed. This combination was selected after a
backend-comparison prototype (silx and plotpy were rejected because their
application-layer abstractions constrain the custom tooltip, subplot-focus,
and draggable-legend interactions). The repository-root `matplotlibrc` pins
`backend: qtagg` because plain runs on macOS would otherwise resolve the
native macosx backend; `MPLBACKEND` still overrides it. Automated checks
stay on the Agg backend and never require Qt.

## Demo, tests, and performance

For manual testing in VS Code, run `interactive_plot.py` directly.
`make_demo_series(seed=...)` produces a reproducible six-panel data set without
opening a window. Automated checks use the Agg backend:

```console
MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py
```

The core registers one canvas-event dispatcher per figure and lazily rebuilds
screen-coordinate caches only after transform changes. Nearest-point search is
still vectorized O(N) per series per hover event; the benchmark records this
known boundary without imposing machine-dependent timing thresholds. By
default the benchmark suppresses `draw_idle()` to isolate dispatch and
hit-testing; pass `--include-render` to include Agg redraw cost.

Runtime dependencies and the supported Python version are declared in
`pyproject.toml`. Ruff and mypy configuration is included for future use, but
those tools are not installed or claimed as part of the current verification.
