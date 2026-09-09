# Interactive plotting

The package separates figure descriptions (`api` and `model`), Matplotlib
construction and cursor interactions (`core`), and artificial example data (`demo`).
Callers describe their figures with `figure → subplot → plot`, then build each
interactive session once. No business-data format is required beyond x/y arrays.

## Reusable interface

```python
from interactive_plotting import figure
import matplotlib.pyplot as plt

fig = figure(rows=2, cols=1, title="Experiment", figsize=(10, 8))
top = fig.subplot(1, title="Temperature", xlabel="Time / s", ylabel="Temperature / °C")
top.plot([0, 1, 2], [20, 22, 21], label="Sensor A", color="blue", marker="o")
top.plot([0, 1, 2], [19, 21, 23], label="Sensor B", color="orange", marker="s")
fig.subplot(2, title="Pressure", xlabel="Time / s", ylabel="Pressure / kPa").plot(
    [0, 1, 2], [100, 102, 101], label="Pressure", marker="^", linestyle="--",
)
session = fig.build()
try:
    plt.show()
finally:
    session.close()
```

For one subplot, use `figure()` and `fig.subplot(1)`. For multiple windows,
create several independent descriptions and call `build()` on each, then call
`plt.show()` once. Keep each returned session alive while using its window.
For export without a GUI event loop, use `session.figure.savefig("result.png")`.

- `figure(rows=1, cols=1, title="", figsize=None)` fixes the rectangular grid.
  Width and height are in inches. Rows and columns must be positive integers.
- `fig.subplot(index, title=None, xlabel=None, ylabel=None)` uses **1-based,
  row-major numbering**: a 2×2 grid contains 1/2 in the top row and 3/4 below.
  Reusing an index returns the same subplot. Supplied text updates that subplot;
  omitted/None text stays unchanged, and `""` clears it. Titles align left.
  Explicitly created empty subplots are visible; unused grid cells are hidden.
  A figure with no subplots can also be built, with every grid cell hidden.
- `ax.plot(x, y, label=None, color=None, marker="o", linestyle="-",
  linewidth=1.35, markersize=10**0.5)` always appends one curve and returns `ax`.
  Repeated calls set the curve count. Colors cycle independently in each subplot;
  explicit colors use Matplotlib color names, hex strings or RGB(A) tuples.
  Named curves appear in a draggable legend; unnamed curves do not.
- Point symbols: `o s ^ v < > D d p h H * + x . , | _ 1 2 3 4 8 P X`.
  Use `marker=None` for a line alone. Line styles are `-`, `--`, `-.`, `:`
  (or `solid`, `dashed`, `dashdot`, `dotted`); `"None"`, `"none"` or `""`
  hides the connecting line.
  At least the line or points must be enabled. Line width and marker size are
  finite positive numbers in points.
- The description creates no windows or event bindings. `build()` renders without
  showing or blocking, then freezes the description. Further additions or text
  edits raise `RuntimeError`; repeated builds return the same session, including
  after it has closed. Invalid input raises `ValueError` without partial changes;
  failed construction cleans up resources and permits a retry.

`PlotSession` exposes the underlying Matplotlib `figure`, row-major `axes`,
`disconnect()`, `close()`, `remove_selected_cursor()`, `clear_extra_cursors()`,
`toggle_axes_maximized(axis)`, and `restore_layout()`. Disconnect and close are
idempotent. Use the description to configure plots before building: direct
Matplotlib data/structure edits after build are outside the interaction contract.
Live updates and adding curves after build are unsupported; create a new figure.

Run the two-window example (custom grid, empty panel, Chinese headings and styles):

```console
venv/bin/python -m examples.flexible_plot
MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.flexible_plot --save-dir /tmp/flexible-plot-example
```

### Compatibility entry point

Existing callers keep their inferred layout, colors and Frame Number/Value labels:

```python
from interactive_plotting import SeriesData, create_interactive_plot

session = create_interactive_plot([
    SeriesData(frames=[0, 1], values=[0.0, 1.0], label="example"),
])
session.close()
```

`SeriesData` copies its arrays and makes them read-only. It remains the
normalization format for legacy callers and future business-data adapters.

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
- While an axes is maximized, Esc restores the original subplot layout and preserves
  pinned selections. Outside maximized mode, Esc clears all pins.
- Drag anywhere on a legend box or its labels to reposition the whole legend.
  Legend and tooltip gestures take priority over subplot maximization.

Tooltips stay hidden during initialization and hover. Active and pinned
selections each show a white tooltip containing only `Frame` and `Value`, both
formatted by the corresponding axis formatter. Hover never moves a tooltip;
keyboard movement of the clicked selection carries its tooltip to the new
point and refreshes the values. Data-point shapes are configurable; all cursor markers are circular; marker size
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

## 扩展绘图功能（pyPicTool TODO Ledger）

```python
from interactive_plotting import figure, build_figure, SuptitleStyle

fig = figure(theme="matlab", window_title="实验数据",
             title="实验结果\n第二行说明",
             suptitle_style=SuptitleStyle(fontsize=16, linespacing=1.4))
ax = fig.subplot(1, xlabel="时间 / s", ylabel="温度 / °C",
                 right_ylabel="设备状态", right_y_enum={0: "关闭", 1: "运行"},
                 legend_loc="upper left")
ax.plot([0, 1, 2], [20, 25, 23], label="温度",
        tooltip=lambda p: f"{p.series.label}\n时间: {p.x_text}\n温度: {p.y_text} °C")
ax.plot([0, 1, 2], [0, 1, 1], label="状态", yaxis="right")
session = fig.build()
# 也可先获取描述，再在其他调用层构建：
# spec = fig.to_spec()
# session = build_figure(spec)
```

- `yaxis="left" | "right"` 指定曲线所属 Y 轴，共享同一 X 轴。右侧曲线或
  `right_ylabel` / `right_y_enum` 会创建右轴。`session.axes` 保持原有行优先主轴列表，
  `session.right_axes[1]` 按 1 起始面板编号访问右轴。双轴合并图例位于右轴上，
  通过 `session.right_axes[1].get_legend()` 访问。
- `y_enum={0: "关闭", 1: "运行"}` 设置左轴枚举，`right_y_enum` 设置右轴枚举。
  键必须是有限数值，值必须是字符串。映射复制保存，空字典清除枚举设置；
  未列出的值在 tooltip 中仍显示数值。数据数组仍使用数值。
- `tooltip` 接受 `TooltipContext`，字段为 `series`、`index`、`x`、`y`、
  `x_text`、`y_text`。`index` 为原始数组的零起始索引，不因 NaN 缺失点而重编号。
  回调返回字符串，允许换行；点击、钉选与键盘移动时调用，悬停不调用。
  回调异常或返回非字符串会产生 `RuntimeWarning` 并回退为 Frame/Value。
- `theme="default"` 保留既有外观；`theme="matlab"` 使用 MATLAB 风格七色循环、
  浅灰画布和四边边框。显式曲线颜色优先。主题仅作用于当前图。
- `window_title` 控制原生窗口标题；`title` 控制图内总标题。`SuptitleStyle` 支持
  `fontsize`、`fontweight`、`linespacing`、`horizontalalignment`（left/center/right）。
  `legend_loc` 支持 Matplotlib 命名位置，如 upper left、lower right、best。

点击窗口右上角 **选线**，或按 **L**，进入整线选择模式。点击曲线的线段、数据点或
图例条目，金色描边表示整条曲线已选中；按 **Delete/Backspace** 删除。
**Esc** 退出整线模式。普通点选择模式中 Delete/Backspace 仍只删除钉选游标。
工具栏处于 pan/zoom 时数据交互暂停；点击“选线”会退出 pan/zoom。
缺失值之间的断线区域不会被当作线段选中。

程序化删除使用稳定句柄：`session.remove_series(session.series[0])`。
`session.series` 按面板行优先、面板内添加顺序保留所有句柄，删除后不重编号；
`handle.removed` 表示是否已删除，`handle.data` / `handle.axis` 用于查看数据和所属轴。
同名及未命名曲线都可独立删除。重复删除返回 False，传入其他会话的句柄抛 ValueError，
关闭或断开后不再删除。删除会清理对应游标与图例、保留其他曲线的选择，并自动适配
剩余数据范围；无数据的轴恢复 0..1。仅影响所属面板，不改变其他面板视图。
新增曲线、实时更新数据以及直接修改 Matplotlib 图元仍不属于会话接口。

公开规格也可直接构建：

```python
from interactive_plotting import FigureSpec, PanelSpec, SeriesData, build_figure

spec = FigureSpec(rows=1, cols=1, panels=(
    PanelSpec(panel=(0, 0), ylabel="值", series=(
        SeriesData([0, 1], [10, 20], "A", panel=(0, 0)),
    )),
), theme="matlab")
session = build_figure(spec)
```

规格中的 `panel=(row, col)` 使用零起始坐标，序列的 panel 必须与所属 PanelSpec 一致。
`build_figure` 完成参数验证后创建窗口资源，不调用 show；每次调用创建独立会话。
`fig.to_spec()` 不创建窗口，返回当前描述快照；`fig.build()` 仍保持构建后冻结和幂等行为。

完整示例：`venv/bin/python -m examples.plot_features`。
无头导出：`MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.plot_features --save /tmp/plot-features.png`。
