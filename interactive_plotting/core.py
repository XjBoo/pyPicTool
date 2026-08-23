"""Reusable Matplotlib construction and interaction controllers."""

from dataclasses import dataclass
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .model import SeriesData


class DataCursor:
    """
    自定义游标类（支持多数据系列）：
    1. 鼠标悬停自动吸附到最近数据点（跨所有系列，基于屏幕像素的欧氏距离）。
    2. 所有未锁定的游标同步移动到同一帧位置，方便对比不同系列的数据。
    3. 支持方向键及 Home/End 键精确移动游标。
    4. 每个系列有一个默认游标，Shift+左键可新增锁定游标。
    """

    active = None

    class Cursor:
        """单个游标实例（竖线 + 高亮点 + tooltip）。"""

        def __init__(self, ax, x0, y0, series_idx, color="red"):
            self.ax = ax
            self.series_idx = series_idx
            self.current_index = 0
            self.locked = False

            (self.vline,) = ax.plot(
                [x0, x0], [y0, y0], "k--", alpha=0.5, zorder=4
            )
            (self.highlight,) = ax.plot(
                [x0], [y0], marker="o", color=color, markersize=8, zorder=5
            )
            self.tooltip = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
                arrowprops=dict(arrowstyle="->"),
                visible=False,
            )
            self.tooltip.draggable(True)

    def __init__(self, ax, series_list):
        self.ax = ax
        self.series_list = series_list
        for series in self.series_list:
            series["frames"] = np.asarray(series["frames"])
            series["values"] = np.asarray(series["values"])
        self._disp_xy_list = None
        self._last_mouse_px = None
        self._selected = None
        self.cursors = []

        for series_idx, series in enumerate(self.series_list):
            x0, y0 = series["frames"][0], series["values"][0]
            color = series.get("color", "red")
            cursor = DataCursor.Cursor(ax, x0, y0, series_idx, color)
            self.cursors.append(cursor)

        self._selected = self.cursors[0]
        self.fig = ax.figure
        self.cid_motion = self.fig.canvas.mpl_connect(
            "motion_notify_event", self.on_hover
        )
        self.cid_key = self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        self.cid_click = self.fig.canvas.mpl_connect(
            "button_press_event", self.on_click
        )
        self.cid_draw = self.fig.canvas.mpl_connect(
            "draw_event", self._refresh_disp_cache
        )
        self.ax.callbacks.connect("xlim_changed", self._refresh_disp_cache)
        self.ax.callbacks.connect("ylim_changed", self._refresh_disp_cache)

        self._refresh_disp_cache()
        for cursor in self.cursors:
            self._update_cursor_visuals(cursor, 0)

    def _refresh_disp_cache(self, _event=None):
        self._disp_xy_list = []
        for series in self.series_list:
            xy = np.column_stack([series["frames"], series["values"]])
            self._disp_xy_list.append(self.ax.transData.transform(xy))

    def _nearest_point_from_px(self, x_px, y_px):
        if self._disp_xy_list is None:
            self._refresh_disp_cache()
        best_d2 = None
        best_series_idx = None
        best_local_idx = None
        for series_idx, disp_xy in enumerate(self._disp_xy_list):
            dx = disp_xy[:, 0] - x_px
            dy = disp_xy[:, 1] - y_px
            distances_squared = dx * dx + dy * dy
            min_idx = int(np.argmin(distances_squared))
            min_distance_squared = distances_squared[min_idx]
            if best_d2 is None or min_distance_squared < best_d2:
                best_d2 = min_distance_squared
                best_series_idx = series_idx
                best_local_idx = min_idx
        return best_series_idx, best_local_idx

    def _cursor_point_px(self, cursor):
        if self._disp_xy_list is None:
            self._refresh_disp_cache()
        return self._disp_xy_list[cursor.series_idx][cursor.current_index]

    def _select_nearest_cursor_to_mouse(self):
        if self._last_mouse_px is None or not self.cursors:
            return self._selected
        mouse_x, mouse_y = self._last_mouse_px
        best = None
        best_d2 = None
        for cursor in self.cursors:
            point_x, point_y = self._cursor_point_px(cursor)
            distance_squared = (point_x - mouse_x) ** 2 + (point_y - mouse_y) ** 2
            if best_d2 is None or distance_squared < best_d2:
                best_d2 = distance_squared
                best = cursor
        if best is not None:
            self._selected = best
        return self._selected

    def _update_cursor_visuals(self, cursor, local_idx):
        series = self.series_list[cursor.series_idx]
        frames = series["frames"]
        values = series["values"]

        if not 0 <= local_idx < len(frames):
            return

        cursor.current_index = local_idx
        x_value, y_value = frames[local_idx], values[local_idx]
        y_min, y_max = self.ax.get_ylim()

        cursor.vline.set_data([x_value, x_value], [y_min, y_max])
        cursor.highlight.set_data([x_value], [y_value])
        cursor.tooltip.xy = (x_value, y_value)
        label = series.get("label", f"Series {cursor.series_idx}")
        cursor.tooltip.set_text(
            f"{label}\nFrame: {int(x_value)}\nValue: {y_value:.4f}"
        )
        cursor.tooltip.set_visible(True)

    def on_hover(self, event):
        if event.inaxes != self.ax:
            if DataCursor.active is self:
                DataCursor.active = None
            return
        if event.x is None or event.y is None:
            return

        DataCursor.active = self
        self._last_mouse_px = (event.x, event.y)
        _, local_idx = self._nearest_point_from_px(event.x, event.y)
        self._select_nearest_cursor_to_mouse()

        need_draw = False
        for cursor in self.cursors:
            if not cursor.locked and cursor.current_index != local_idx:
                self._update_cursor_visuals(cursor, local_idx)
                need_draw = True
        if need_draw:
            self.fig.canvas.draw_idle()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        if getattr(event, "button", None) != 1:
            return

        DataCursor.active = self
        if event.x is not None and event.y is not None:
            self._last_mouse_px = (event.x, event.y)

        for cursor in self.cursors:
            contains, _ = cursor.tooltip.contains(event)
            if contains:
                self._selected = cursor
                return

        is_shift = "shift" in str(getattr(event, "key", "")).lower()
        if is_shift:
            if event.x is None or event.y is None:
                return
            series_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
            series = self.series_list[series_idx]
            x_value = series["frames"][local_idx]
            y_value = series["values"][local_idx]
            color = series.get("color", "red")
            cursor = DataCursor.Cursor(
                self.ax, x_value, y_value, series_idx, color
            )
            cursor.locked = True
            self.cursors.append(cursor)
            self._selected = cursor
            self._update_cursor_visuals(cursor, local_idx)
            self.fig.canvas.draw_idle()
            return

        cursor = self._select_nearest_cursor_to_mouse()
        if cursor is None:
            return
        cursor.locked = not cursor.locked

        if cursor.locked:
            if event.x is None or event.y is None:
                return
            series_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
            if cursor.series_idx != series_idx:
                cursor.series_idx = series_idx
                color = self.series_list[series_idx].get("color", "red")
                cursor.highlight.set_color(color)
            self._update_cursor_visuals(cursor, local_idx)
            self.fig.canvas.draw_idle()
        else:
            self.fig.canvas.draw_idle()

    def on_key(self, event):
        if DataCursor.active is not self:
            return
        cursor = self._select_nearest_cursor_to_mouse()
        if cursor is None:
            return

        key = getattr(event, "key", "").lower()
        frames = self.series_list[cursor.series_idx]["frames"]

        if key == "right":
            new_idx = cursor.current_index + 1
        elif key == "left":
            new_idx = cursor.current_index - 1
        elif key == "home":
            new_idx = 0
        elif key == "end":
            new_idx = len(frames) - 1
        else:
            return

        if 0 <= new_idx < len(frames):
            self._update_cursor_visuals(cursor, new_idx)
            self.fig.canvas.draw_idle()


@dataclass(slots=True)
class PlotSession:
    """Own the figure and controller references created for one plot."""

    figure: Figure
    controllers: tuple[DataCursor, ...]
    axes: tuple[Axes, ...]


def create_interactive_plot(series: Sequence[SeriesData]) -> PlotSession:
    """Construct an interactive plot without displaying or blocking."""

    series_items = list(series)
    if not series_items:
        raise ValueError("create_interactive_plot requires at least one series")

    row_count = max(item.panel[0] for item in series_items) + 1
    column_count = max(item.panel[1] for item in series_items) + 1
    figure, axes_grid = plt.subplots(row_count, column_count, squeeze=False)
    grouped: dict[tuple[int, int], list[SeriesData]] = {}
    for item in series_items:
        grouped.setdefault(item.panel, []).append(item)

    controllers = []
    axes = []
    for row in range(row_count):
        for column in range(column_count):
            ax = axes_grid[row, column]
            axes.append(ax)
            panel_series = grouped.get((row, column), [])
            if not panel_series:
                ax.set_visible(False)
                continue

            cursor_series = []
            for item in panel_series:
                line_kwargs = {"alpha": item.line_alpha, "zorder": 1}
                if item.line_color is not None:
                    line_kwargs["color"] = item.line_color
                ax.plot(
                    item.frames,
                    item.values,
                    label=item.label,
                    **line_kwargs,
                )
                ax.scatter(
                    item.frames,
                    item.values,
                    c=item.color,
                    s=15,
                    zorder=2,
                    alpha=0.6,
                )
                cursor_series.append(
                    {
                        "frames": item.frames,
                        "values": item.values,
                        "label": item.label,
                        "color": item.color,
                    }
                )

            controller = DataCursor(ax, cursor_series)
            controllers.append(controller)
            panel_title = next(
                (item.panel_title for item in panel_series if item.panel_title), None
            )
            if panel_title:
                ax.set_title(panel_title)
            ax.set_xlabel("Frame Number")
            ax.set_ylabel("Value")
            ax.legend(loc="upper right")
            ax.grid(True, linestyle="--", alpha=0.6)

    figure.tight_layout()
    return PlotSession(figure, tuple(controllers), tuple(axes))
