"""Reusable Matplotlib construction and interaction controllers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import CloseEvent, DrawEvent, KeyEvent, MouseEvent
from matplotlib.figure import Figure
from matplotlib.legend import Legend

from .model import SeriesData


class DataCursor:
    """
    自定义游标类（支持多数据系列）：
    1. 鼠标悬停自动吸附到最近数据点
       （跨所有系列，基于屏幕像素的欧氏距离）。
    2. 所有未锁定的游标同步移动到同一帧位置，
       方便对比不同系列的数据。
    3. 支持方向键及 Home/End 键精确移动游标。
    4. 每个系列有一个默认游标，Shift+左键可新增锁定游标。
    """

    class Cursor:
        """单个游标实例（高亮点 + tooltip）。"""

        def __init__(
            self,
            ax: Axes,
            x0: float,
            y0: float,
            series_idx: int,
            color: str = "red",
            is_default: bool = True,
        ) -> None:
            self.ax = ax
            self.series_idx = series_idx
            self.current_index = 0
            self.locked = False
            self.is_default = is_default
            self.color = color

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

        def apply_style(self, selected: bool) -> None:
            self.highlight.set_marker("s" if self.locked else "o")
            self.highlight.set_markersize(10 if selected else 8)
            self.highlight.set_markeredgecolor("gold" if selected else self.color)
            self.highlight.set_markeredgewidth(2 if selected else 1)

    @dataclass(frozen=True, slots=True)
    class CursorState:
        cursor: DataCursor.Cursor
        current_index: int
        locked: bool
        tooltip_visible: bool
        tooltip_position: tuple[float, float]
        tooltip_text: str

    @dataclass(frozen=True, slots=True)
    class StateSnapshot:
        cursors: tuple[DataCursor.CursorState, ...]
        selected: DataCursor.Cursor | None

    def __init__(self, ax: Axes, series_list: Sequence[SeriesData]) -> None:
        self.ax = ax
        self.series_list = tuple(series_list)
        self._disp_xy_list: list[np.ndarray] | None = None
        self._disp_indices_list: list[np.ndarray] | None = None
        self._disp_cache_valid = False
        self._disp_cache_signature: tuple[float, ...] | None = None
        self._valid_indices_list: list[np.ndarray] = []
        self._sync_frames_list: list[np.ndarray] = []
        self._sync_indices_list: list[np.ndarray] = []
        self._selected: DataCursor.Cursor | None = None
        self._dragging_cursor: DataCursor.Cursor | None = None
        self._drag_start_mouse: tuple[float, float] | None = None
        self._drag_start_position: tuple[float, float] | None = None
        self.cursors: list[DataCursor.Cursor] = []

        for series_idx, series in enumerate(self.series_list):
            valid_indices = np.flatnonzero(series.valid_mask)
            valid_frames = series.frames[valid_indices]
            sync_frames, inverse = np.unique(valid_frames, return_inverse=True)
            sync_indices = np.full(sync_frames.size, series.frames.size, dtype=int)
            np.minimum.at(sync_indices, inverse, valid_indices)
            self._valid_indices_list.append(valid_indices)
            self._sync_frames_list.append(sync_frames)
            self._sync_indices_list.append(sync_indices)

            first_idx = int(valid_indices[0])
            x0, y0 = series.frames[first_idx], series.values[first_idx]
            color = series.color
            cursor = DataCursor.Cursor(ax, x0, y0, series_idx, color)
            cursor.current_index = first_idx
            self.cursors.append(cursor)

        self.fig = ax.figure
        self._axis_callback_ids = [
            self.ax.callbacks.connect("xlim_changed", self._invalidate_disp_cache),
            self.ax.callbacks.connect("ylim_changed", self._invalidate_disp_cache),
        ]
        self._connected = True

        for cursor in self.cursors:
            self._update_cursor_visuals(
                cursor, cursor.current_index, show_tooltip=False
            )
            cursor.apply_style(False)

    def _select_cursor(self, cursor: Cursor | None) -> bool:
        previous = self._selected
        if previous is cursor:
            return False
        self._selected = cursor
        if previous is not None and previous in self.cursors and previous is not cursor:
            previous.apply_style(False)
        if cursor is not None:
            cursor.apply_style(True)
        return True

    def _invalidate_disp_cache(self, _event: Axes | None = None) -> None:
        self._disp_cache_valid = False

    def _transform_signature(self) -> tuple[float, ...]:
        return tuple(float(value) for value in self.ax.transData.get_matrix().flat)

    def invalidate_if_transform_changed(self) -> None:
        if (
            self._disp_cache_valid
            and self._disp_cache_signature != self._transform_signature()
        ):
            self._disp_cache_valid = False

    def _ensure_disp_cache(self) -> None:
        signature = self._transform_signature()
        if self._disp_cache_valid and self._disp_cache_signature == signature:
            return
        self._disp_xy_list = []
        self._disp_indices_list = []
        for series, valid_indices in zip(
            self.series_list, self._valid_indices_list, strict=True
        ):
            xy = np.column_stack(
                [series.frames[valid_indices], series.values[valid_indices]]
            )
            self._disp_xy_list.append(self.ax.transData.transform(xy))
            self._disp_indices_list.append(valid_indices)
        self._disp_cache_valid = True
        self._disp_cache_signature = signature

    def _nearest_point_from_px(self, x_px: float, y_px: float) -> tuple[int, int]:
        self._ensure_disp_cache()
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
                best_local_idx = int(self._disp_indices_list[series_idx][min_idx])
        return best_series_idx, best_local_idx

    def _nearest_index_for_frame(self, series_idx: int, target_frame: float) -> int:
        frames = self._sync_frames_list[series_idx]
        original_indices = self._sync_indices_list[series_idx]
        insertion = int(np.searchsorted(frames, target_frame))
        candidate_positions = []
        if insertion > 0:
            candidate_positions.append(insertion - 1)
        if insertion < frames.size:
            candidate_positions.append(insertion)

        target_number = (
            target_frame.item()
            if isinstance(target_frame, np.generic)
            else target_frame
        )

        def distance_and_index(original_index: int) -> tuple[float, int]:
            candidate = self.series_list[series_idx].frames[original_index]
            candidate_number = (
                candidate.item() if isinstance(candidate, np.generic) else candidate
            )
            return abs(candidate_number - target_number), int(original_index)

        return int(
            min(
                (original_indices[position] for position in candidate_positions),
                key=distance_and_index,
            )
        )

    def _update_cursor_visuals(
        self, cursor: Cursor, local_idx: int, show_tooltip: bool = True
    ) -> None:
        series = self.series_list[cursor.series_idx]
        frames = series.frames
        values = series.values

        if not 0 <= local_idx < len(frames):
            return

        cursor.current_index = local_idx
        x_value, y_value = frames[local_idx], values[local_idx]
        cursor.highlight.set_data([x_value], [y_value])
        cursor.tooltip.xy = (x_value, y_value)
        label = series.label
        frame_text = self.ax.xaxis.get_major_formatter().format_data_short(x_value)
        cursor.tooltip.set_text(
            f"{label}\nFrame: {frame_text}\nValue: {y_value:.4f}"
        )
        if show_tooltip:
            cursor.tooltip.set_visible(True)

    def on_hover(self, event: MouseEvent) -> None:
        if self._dragging_cursor is not None:
            if event.x is None or event.y is None:
                return
            start_x, start_y = self._drag_start_mouse
            text_x, text_y = self._drag_start_position
            points_per_pixel = 72.0 / self.fig.dpi
            self._dragging_cursor.tooltip.set_position(
                (
                    text_x + (event.x - start_x) * points_per_pixel,
                    text_y + (event.y - start_y) * points_per_pixel,
                )
            )
            self.fig.canvas.draw_idle()
            return
        if event.inaxes != self.ax:
            return
        if event.x is None or event.y is None:
            return

        series_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
        target_frame = self.series_list[series_idx].frames[local_idx]
        selected_cursor = self.cursors[series_idx]
        need_draw = self._select_cursor(selected_cursor)

        for cursor in self.cursors:
            target_idx = (
                local_idx
                if cursor is selected_cursor
                else self._nearest_index_for_frame(cursor.series_idx, target_frame)
            )
            if not cursor.locked and (
                cursor.current_index != target_idx or not cursor.tooltip.get_visible()
            ):
                self._update_cursor_visuals(cursor, target_idx)
                need_draw = True
        if need_draw:
            self.fig.canvas.draw_idle()

    def on_click(self, event: MouseEvent) -> None:
        if getattr(event, "button", None) == 1:
            for cursor in self.cursors:
                contains, _ = cursor.tooltip.contains(event)
                if contains:
                    self._select_cursor(cursor)
                    self._dragging_cursor = cursor
                    self._drag_start_mouse = (event.x, event.y)
                    self._drag_start_position = cursor.tooltip.get_position()
                    return

        if event.inaxes != self.ax:
            return
        if getattr(event, "button", None) != 1:
            return

        is_shift = "shift" in str(getattr(event, "key", "")).lower()
        if is_shift:
            if event.x is None or event.y is None:
                return
            series_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
            series = self.series_list[series_idx]
            x_value = series.frames[local_idx]
            y_value = series.values[local_idx]
            color = series.color
            cursor = DataCursor.Cursor(
                self.ax, x_value, y_value, series_idx, color, is_default=False
            )
            cursor.locked = True
            self.cursors.append(cursor)
            self._select_cursor(cursor)
            self._update_cursor_visuals(cursor, local_idx)
            cursor.apply_style(True)
            self.fig.canvas.draw_idle()
            return

        series_idx, local_idx = self._nearest_point_from_px(event.x, event.y)
        cursor = self.cursors[series_idx]
        self._select_cursor(cursor)
        cursor.locked = not cursor.locked
        cursor.apply_style(True)
        self._update_cursor_visuals(cursor, local_idx)
        self.fig.canvas.draw_idle()

    def on_release(self, _event: MouseEvent) -> None:
        self._dragging_cursor = None
        self._drag_start_mouse = None
        self._drag_start_position = None

    def on_key(self, event: KeyEvent) -> None:
        if self._dragging_cursor is not None:
            return
        key = getattr(event, "key", "").lower()
        if key in ("delete", "backspace"):
            self.remove_selected_cursor()
            return

        cursor = self._selected
        if cursor is None:
            return
        if cursor.locked:
            return

        series = self.series_list[cursor.series_idx]
        valid_indices = self._valid_indices_list[cursor.series_idx]
        current_position = int(np.flatnonzero(valid_indices == cursor.current_index)[0])

        if key == "right":
            new_position = current_position + 1
        elif key == "left":
            new_position = current_position - 1
        elif key == "home":
            new_position = 0
        elif key == "end":
            new_position = len(valid_indices) - 1
        else:
            return

        if 0 <= new_position < len(valid_indices):
            selected_idx = int(valid_indices[new_position])
            target_frame = series.frames[selected_idx]
            for candidate in self.cursors:
                if candidate.locked:
                    continue
                target_idx = (
                    selected_idx
                    if candidate is cursor
                    else self._nearest_index_for_frame(
                        candidate.series_idx, target_frame
                    )
                )
                self._update_cursor_visuals(candidate, target_idx)
            self.fig.canvas.draw_idle()

    def remove_selected_cursor(self) -> bool:
        cursor = self._selected
        if cursor is None or cursor.is_default:
            return False
        owner_default = self.cursors[cursor.series_idx]
        cursor.highlight.remove()
        cursor.tooltip.remove()
        self.cursors.remove(cursor)
        self._select_cursor(owner_default)
        self.fig.canvas.draw_idle()
        return True

    def clear_extra_cursors(self, *, request_draw: bool = True) -> int:
        extras = [cursor for cursor in self.cursors if not cursor.is_default]
        for cursor in extras:
            cursor.highlight.remove()
            cursor.tooltip.remove()
            self.cursors.remove(cursor)
        if self._selected in extras:
            self._select_cursor(self.cursors[0])
        if extras and request_draw:
            self.fig.canvas.draw_idle()
        return len(extras)

    @property
    def is_dragging(self) -> bool:
        return self._dragging_cursor is not None

    def contains_tooltip(self, event: MouseEvent) -> bool:
        return any(cursor.tooltip.contains(event)[0] for cursor in self.cursors)

    def capture_state(self) -> StateSnapshot:
        return DataCursor.StateSnapshot(
            cursors=tuple(
                DataCursor.CursorState(
                    cursor=cursor,
                    current_index=cursor.current_index,
                    locked=cursor.locked,
                    tooltip_visible=cursor.tooltip.get_visible(),
                    tooltip_position=cursor.tooltip.get_position(),
                    tooltip_text=cursor.tooltip.get_text(),
                )
                for cursor in self.cursors
            ),
            selected=self._selected,
        )

    def restore_state(self, snapshot: StateSnapshot) -> None:
        captured_cursors = [state.cursor for state in snapshot.cursors]
        for cursor in tuple(self.cursors):
            if cursor in captured_cursors:
                continue
            cursor.highlight.remove()
            cursor.tooltip.remove()
        self.cursors = captured_cursors
        self._selected = snapshot.selected
        for state in snapshot.cursors:
            cursor = state.cursor
            cursor.locked = state.locked
            self._update_cursor_visuals(
                cursor, state.current_index, show_tooltip=False
            )
            cursor.tooltip.set_visible(state.tooltip_visible)
            cursor.tooltip.set_position(state.tooltip_position)
            cursor.tooltip.set_text(state.tooltip_text)
            cursor.apply_style(cursor is self._selected)
        self._dragging_cursor = None
        self._drag_start_mouse = None
        self._drag_start_position = None

    def disconnect(self) -> None:
        if not self._connected:
            return
        for callback_id in self._axis_callback_ids:
            self.ax.callbacks.disconnect(callback_id)
        self._axis_callback_ids.clear()
        self._dragging_cursor = None
        self._drag_start_mouse = None
        self._drag_start_position = None
        self._selected = None
        self._disp_xy_list = None
        self._disp_indices_list = None
        self._disp_cache_valid = False
        self._connected = False


@dataclass(frozen=True, slots=True)
class AxesLayoutState:
    """Captured state required to restore one axes exactly."""

    visible: bool
    in_layout: bool
    original_position: tuple[float, float, float, float]
    active_position: tuple[float, float, float, float]


class AxesLayoutManager:
    """Maximize one axes inside a figure and restore the captured layout."""

    def __init__(self, figure: Figure, axes: Sequence[Axes]) -> None:
        self.figure = figure
        self.axes = tuple(axes)
        self._states = {
            axis: AxesLayoutState(
                visible=axis.get_visible(),
                in_layout=axis.get_in_layout(),
                original_position=tuple(axis.get_position(original=True).bounds),
                active_position=tuple(axis.get_position().bounds),
            )
            for axis in self.axes
        }
        visible_states = [
            state for state in self._states.values() if state.visible
        ]
        left = min(state.active_position[0] for state in visible_states)
        bottom = min(state.active_position[1] for state in visible_states)
        right = max(
            state.active_position[0] + state.active_position[2]
            for state in visible_states
        )
        top = max(
            state.active_position[1] + state.active_position[3]
            for state in visible_states
        )
        self._maximized_position = (left, bottom, right - left, top - bottom)
        self.maximized_axes: Axes | None = None

    def toggle(self, axis: Axes) -> bool:
        if axis not in self._states:
            raise ValueError("axis does not belong to this PlotSession")
        if self.maximized_axes is axis:
            self.restore()
            return False
        if self.maximized_axes is not None:
            self.restore(request_draw=False)
        for candidate in self.axes:
            candidate.set_visible(candidate is axis)
            candidate.set_in_layout(False)
        axis.set_position(self._maximized_position, which="both")
        axis.set_in_layout(False)
        self.maximized_axes = axis
        self.figure.canvas.draw_idle()
        return True

    def restore(self, *, request_draw: bool = True) -> bool:
        if self.maximized_axes is None:
            return False
        for axis, state in self._states.items():
            axis.set_visible(state.visible)
            axis.set_position(state.original_position, which="original")
            axis.set_position(state.active_position, which="active")
            axis.set_in_layout(state.in_layout)
        self.maximized_axes = None
        if request_draw:
            self.figure.canvas.draw_idle()
        return True


@dataclass(frozen=True, slots=True)
class PendingAxesClick:
    controller: DataCursor
    axis: Axes
    snapshot: DataCursor.StateSnapshot
    previous_active_controller: DataCursor | None


class FigureDispatcher:
    """Route one set of canvas events to all panel controllers in a figure."""

    def __init__(
        self,
        figure: Figure,
        controllers: Sequence[DataCursor],
        axes: Sequence[Axes],
    ) -> None:
        self.figure = figure
        self.controllers = tuple(controllers)
        self._by_axes = {controller.ax: controller for controller in self.controllers}
        self.legends = tuple(
            legend
            for axis in axes
            if (legend := axis.get_legend()) is not None
        )
        self.active_controller: DataCursor | None = None
        self.dragging_controller: DataCursor | None = None
        self.dragging_legend: Legend | None = None
        self.layout = AxesLayoutManager(figure, axes)
        self._pending_axes_click: PendingAxesClick | None = None
        self.connected = True
        canvas = figure.canvas
        self._canvas_callback_ids = [
            canvas.mpl_connect("motion_notify_event", self.on_motion),
            canvas.mpl_connect("button_press_event", self.on_press),
            canvas.mpl_connect("button_release_event", self.on_release),
            canvas.mpl_connect("key_press_event", self.on_key),
            canvas.mpl_connect("draw_event", self.on_draw),
            canvas.mpl_connect("close_event", self.on_close),
        ]

    def _toolbar_is_active(self) -> bool:
        manager = getattr(self.figure.canvas, "manager", None)
        toolbar = getattr(manager, "toolbar", None)
        return bool(getattr(toolbar, "mode", ""))

    def _legend_at(self, event: MouseEvent) -> Legend | None:
        return next(
            (
                legend
                for legend in self.legends
                if legend.get_visible() and legend.contains(event)[0]
            ),
            None,
        )

    def on_motion(self, event: MouseEvent) -> None:
        if self._toolbar_is_active():
            return
        if self.dragging_legend is not None:
            return
        if self.dragging_controller is not None:
            self.dragging_controller.on_hover(event)
            return
        controller = self._by_axes.get(event.inaxes)
        if controller is None:
            return
        self.active_controller = controller
        controller.on_hover(event)

    def on_press(self, event: MouseEvent) -> None:
        if self._toolbar_is_active() or self.dragging_controller is not None:
            self._pending_axes_click = None
            return
        legend = self._legend_at(event)
        if legend is not None:
            self._pending_axes_click = None
            if getattr(event, "button", None) == 1:
                self.dragging_legend = legend
            return
        controller = next(
            (
                candidate
                for candidate in self.controllers
                if candidate.contains_tooltip(event)
            ),
            None,
        )
        if controller is not None:
            self._pending_axes_click = None
            self.active_controller = controller
            controller.on_click(event)
            if controller.is_dragging:
                self.dragging_controller = controller
            return
        if controller is None:
            controller = self._by_axes.get(event.inaxes)
        if controller is None:
            self._pending_axes_click = None
            return
        if getattr(event, "button", None) == 1 and getattr(
            event, "dblclick", False
        ):
            pending = self._pending_axes_click
            if (
                pending is not None
                and pending.controller is controller
                and pending.axis is event.inaxes
            ):
                controller.restore_state(pending.snapshot)
                self.active_controller = pending.previous_active_controller
            self._pending_axes_click = None
            self.layout.toggle(controller.ax)
            return
        self._pending_axes_click = None
        if getattr(event, "button", None) == 1:
            self._pending_axes_click = PendingAxesClick(
                controller=controller,
                axis=controller.ax,
                snapshot=controller.capture_state(),
                previous_active_controller=self.active_controller,
            )
        self.active_controller = controller
        controller.on_click(event)
        if controller.is_dragging:
            self.dragging_controller = controller

    def on_release(self, event: MouseEvent) -> None:
        if self.dragging_legend is not None:
            self.dragging_legend = None
            return
        controller = self.dragging_controller or self.active_controller
        if controller is not None:
            controller.on_release(event)
        self.dragging_controller = None

    def on_key(self, event: KeyEvent) -> None:
        if (
            self._toolbar_is_active()
            or self.dragging_controller is not None
            or self.dragging_legend is not None
        ):
            return
        self._pending_axes_click = None
        if getattr(event, "key", "").lower() in ("escape", "esc"):
            if self.layout.restore():
                return
            self.clear_extra_cursors()
            return
        if self.active_controller is not None:
            self.active_controller.on_key(event)

    def on_draw(self, _event: DrawEvent) -> None:
        for controller in self.controllers:
            controller.invalidate_if_transform_changed()

    def on_close(self, _event: CloseEvent) -> None:
        self.disconnect()

    def remove_selected_cursor(self) -> bool:
        if self.active_controller is None:
            return False
        return self.active_controller.remove_selected_cursor()

    def clear_extra_cursors(self) -> int:
        removed = sum(
            controller.clear_extra_cursors(request_draw=False)
            for controller in self.controllers
        )
        if removed:
            self.figure.canvas.draw_idle()
        return removed

    def toggle_axes_maximized(self, axis: Axes) -> bool:
        if not self.connected:
            return False
        return self.layout.toggle(axis)

    def restore_layout(self) -> bool:
        if not self.connected:
            return False
        return self.layout.restore()

    def disconnect(self) -> None:
        if not self.connected:
            return
        layout_changed = self.layout.restore(request_draw=False)
        for callback_id in self._canvas_callback_ids:
            self.figure.canvas.mpl_disconnect(callback_id)
        self._canvas_callback_ids.clear()
        for controller in self.controllers:
            controller.disconnect()
        for legend in self.legends:
            legend.set_draggable(False)
        self.active_controller = None
        self.dragging_controller = None
        self.dragging_legend = None
        self._by_axes.clear()
        self._pending_axes_click = None
        self.connected = False
        if layout_changed:
            self.figure.canvas.draw_idle()


@dataclass(slots=True)
class PlotSession:
    """Own the figure and controller references created for one plot."""

    figure: Figure
    controllers: tuple[DataCursor, ...]
    axes: tuple[Axes, ...]
    _dispatcher: FigureDispatcher
    _closed: bool = field(default=False, init=False)

    def disconnect(self) -> None:
        self._dispatcher.disconnect()

    def close(self) -> None:
        if self._closed:
            return
        self.disconnect()
        plt.close(self.figure)
        self._closed = True

    def remove_selected_cursor(self) -> bool:
        return self._dispatcher.remove_selected_cursor()

    def clear_extra_cursors(self) -> int:
        return self._dispatcher.clear_extra_cursors()

    def toggle_axes_maximized(self, axis: Axes) -> bool:
        """Toggle one axes between the captured layout and figure-filling mode."""

        return self._dispatcher.toggle_axes_maximized(axis)

    def restore_layout(self) -> bool:
        """Restore the captured axes layout, returning whether it changed."""

        return self._dispatcher.restore_layout()


def create_interactive_plot(series: Sequence[SeriesData]) -> PlotSession:
    """Construct an interactive plot without displaying or blocking."""

    series_items = list(series)
    if not series_items:
        raise ValueError("create_interactive_plot requires at least one series")

    row_count = max(item.panel[0] for item in series_items) + 1
    column_count = max(item.panel[1] for item in series_items) + 1
    figure, axes_grid = plt.subplots(row_count, column_count, squeeze=False)
    controllers: list[DataCursor] = []
    axes: list[Axes] = []
    legends: list[Legend] = []
    try:
        grouped: dict[tuple[int, int], list[SeriesData]] = {}
        for item in series_items:
            grouped.setdefault(item.panel, []).append(item)

        for row in range(row_count):
            for column in range(column_count):
                ax = axes_grid[row, column]
                axes.append(ax)
                panel_series = grouped.get((row, column), [])
                if not panel_series:
                    ax.set_visible(False)
                    continue

                for item in panel_series:
                    line_kwargs = {"alpha": item.line_alpha, "zorder": 1}
                    if item.line_color is not None:
                        line_kwargs["color"] = item.line_color
                    ax.plot(
                        item.frames,
                        item.plotting_values,
                        label=item.label,
                        **line_kwargs,
                    )
                    ax.scatter(
                        item.frames[item.valid_mask],
                        item.values[item.valid_mask],
                        c=item.color,
                        s=15,
                        zorder=2,
                        alpha=0.6,
                    )
                controller = DataCursor(ax, panel_series)
                controllers.append(controller)
                panel_title = next(
                    (item.panel_title for item in panel_series if item.panel_title),
                    None,
                )
                if panel_title:
                    ax.set_title(panel_title)
                ax.set_xlabel("Frame Number")
                ax.set_ylabel("Value")
                legend = ax.legend(loc="upper right")
                legend.set_draggable(True)
                legends.append(legend)
                ax.grid(True, linestyle="--", alpha=0.6)

        figure.tight_layout()
        dispatcher = FigureDispatcher(figure, controllers, axes)
        return PlotSession(figure, tuple(controllers), tuple(axes), dispatcher)
    except Exception:
        for controller in controllers:
            controller.disconnect()
        for legend in legends:
            legend.set_draggable(False)
        plt.close(figure)
        raise
