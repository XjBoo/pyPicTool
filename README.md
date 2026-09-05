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

- Hover shows one transient circular preview on the nearest data point within
  the shared 6 px hit radius. It has no tooltip and remains independent of all
  persistent selections, including other points on the same series. Hovering
  an already selected point reuses that point's marker instead of drawing a
  duplicate, and moving away hides only the preview.
- Left click creates the figure's single active selection with a circular
  marker and tooltip. Clicking a different unpinned point replaces the active
  selection across series and subplots; clicking the active point again
  cancels it. Existing pinned selections are preserved.
- Shift+left click adds a pinned circular marker and tooltip, and any number of
  pins may remain visible across panels. Left-click a pinned point to remove
  only that pin; Delete/Backspace removes the clicked pin, and Esc clears all
  pins when no axes is maximized. `remove_selected_cursor()` and
  `clear_extra_cursors()` expose the same single/all-pin operations.
- Left/Right and Home/End move only the cursor anchored by the last left
  click (a data-point click, a Shift+left-click extra cursor, or a click on
  its tooltip), without moving any other selection. Hovering never changes
  the keyboard target. The most recently clicked selection is the only
  persistent keyboard-focus target; a different persistent marker under the
  pointer may also temporarily use the gold hover-focus style. While a session
  is active, Left/Right/Home/Backspace are detached
  from the Matplotlib navigation toolbar's view history; the default
  bindings return once the last session disconnects.
- Drag a visible tooltip to reposition its text. Cursor interaction pauses
  while tooltip dragging or toolbar pan/zoom is active.
- Double-click a subplot background to make that axes fill the current
  Matplotlib figure. Double-click it again to restore the exact captured
  layout. Programmatic switching restores the previous axes before maximizing
  the next one.
- While an axes is maximized, Esc restores the six-panel layout and preserves
  pinned selections. Outside maximized mode, Esc clears all pins.
- Drag anywhere on a legend box or its labels to reposition the whole legend.
  Legend and tooltip gestures take priority over subplot maximization.

Tooltips stay hidden during initialization and hover. Active and pinned
selections each show a white tooltip containing only `Frame` and `Value`, both
formatted by the corresponding axis formatter. Hover never moves a tooltip;
keyboard movement of the clicked selection carries its tooltip to the new
point and refreshes the values. All cursor markers are circular; marker size
and a gold edge identify the current click or hover focus.

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

## Visual presentation and Windows

Plots use a light gray canvas, white panels, quiet grid lines and left-aligned
headings. The demo uses blue sine signals and orange cosine signals. A series'
line defaults to its point color; explicit `line_color` and `line_alpha` still
win. Styling is local to each figure and does not change global plotting defaults.
The six-panel demo opens at 12 × 10 inches; other grids scale with panel count.
Tooltips retain their drag behavior, circular gold focus and Frame/Value content.
Near an edge a tooltip can extend outside its panel; drag it into free space.

From the repository root on Windows, after installing the declared dependencies
in a Python 3.11+ environment, run:

```powershell
venv\Scripts\python.exe interactive_plot.py
```

The existing QtAgg/PySide6 backend is retained. Latin text and numeric minus
signs use Matplotlib's bundled DejaVu Sans; installed CJK fonts (including
Microsoft YaHei or SimHei on Windows) supply Chinese glyphs. No external font
download or platform-specific font path is required. If no CJK font is installed,
English and numbers still render, but Chinese glyph coverage is not guaranteed.

Windows acceptance checklist (not yet tested on a Windows machine):

- Launch and close the window; use Chinese panel titles and negative values.
- At 100%, 150% and 200% display scaling, resize the window and check text and
  point hit-testing. Confirm double-click/Esc restores the layout.
- Exercise hover, click, Shift+click, Left/Right/Home/End, Delete/Backspace,
  tooltip/legend dragging and toolbar pan/zoom.

See [visual examples and verification](docs/visual-design/verification.md) for
actual checks and remaining platform limitations.

The Qt navigation toolbar starts hidden. Click **工具栏** in the upper-right
corner of the canvas to show it, and click again to collapse it. Collapsing exits
pan/zoom mode so data-point interaction resumes; the current view and selections
are retained. This native window button does not appear in saved images. Agg
plots have no window controls. The test suite runs a separate Qt offscreen probe
for this control; that automated probe does not replace real desktop validation.
