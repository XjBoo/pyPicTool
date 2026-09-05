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
from .style import BORDER, CANVAS, MUTED, TEXT, font_families, style_axes
from .qt_toolbar import install_toolbar_toggle

# Keyboard cursor navigation owns keys that Matplotlib's default keymap binds
# to navigation-toolbar view history (back/forward/home). Sessions claim the
# cleanup on creation and release it on disconnect; the last release restores
# the exact default bindings.
_VIEW_NAVIGATION_KEY_REMOVALS: dict[str, tuple[str, ...]] = {
    "keymap.back": ("left", "backspace"),
    "keymap.forward": ("right",),
    "keymap.home": ("home",),
}
_view_navigation_key_claims = 0
_view_navigation_key_snapshots: dict[str, list[str]] | None = None


def _suppress_view_navigation_keys() -> None:
    """Detach toolbar view-history keys so cursor navigation owns them."""

    global _view_navigation_key_claims, _view_navigation_key_snapshots
    if _view_navigation_key_claims == 0:
        snapshots: dict[str, list[str]] = {}
        for setting, keys in _VIEW_NAVIGATION_KEY_REMOVALS.items():
            snapshots[setting] = list(plt.rcParams[setting])
            for key in keys:
                if key in plt.rcParams[setting]:
                    plt.rcParams[setting].remove(key)
        _view_navigation_key_snapshots = snapshots
    _view_navigation_key_claims += 1


def _restore_view_navigation_keys() -> None:
    """Release one session claim and restore defaults on the last release."""

    global _view_navigation_key_claims, _view_navigation_key_snapshots
    if _view_navigation_key_claims == 0:
        return
    _view_navigation_key_claims -= 1
    if _view_navigation_key_claims == 0:
        for setting, snapshot in (_view_navigation_key_snapshots or {}).items():
            plt.rcParams[setting] = list(snapshot)
        _view_navigation_key_snapshots = None


class DataCursor:
    """Manage independent hover, active, and pinned point selections."""

    _HIT_RADIUS_PIXELS = 6.0

    class Cursor:
        """A persistent active or pinned point and its tooltip."""

        def __init__(
            self,
            ax: Axes,
            x0: float,
            y0: float,
            series_idx: int,
            color: str,
            role: str,
        ) -> None:
            self.ax = ax
            self.series_idx = series_idx
            self.current_index = 0
            self.role = role
            self.color = color

            (self.highlight,) = ax.plot(
                [x0], [y0], marker="o", color=color, markersize=8, zorder=5
            )
            self.highlight.set_visible(False)
            self.tooltip = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(20, 20),
                textcoords="offset points",
                fontsize=9,
                fontfamily=ax.xaxis.label.get_fontfamily(),
                color=TEXT,
                linespacing=1.5,
                bbox=dict(boxstyle="round,pad=0.6", fc="white", ec=BORDER,
                          lw=0.8, alpha=1),
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8),
                # Match the dispatcher's legend-first hit testing on overlap.
                zorder=4,
                visible=False,
            )

        def apply_style(self, selected: bool) -> None:
            self.highlight.set_marker("o")
            self.highlight.set_markersize(10 if selected else 8)
            self.highlight.set_markeredgecolor("gold" if selected else self.color)
            self.highlight.set_markeredgewidth(2 if selected else 1)

    @dataclass(frozen=True, slots=True)
    class CursorState:
        cursor: DataCursor.Cursor
        current_index: int
        series_idx: int
        color: str
        role: str
        marker_visible: bool
        tooltip_visible: bool
        tooltip_anchor: tuple[float, float]
        tooltip_position: tuple[float, float]
        tooltip_text: str

    @dataclass(frozen=True, slots=True)
    class StateSnapshot:
        cursors: tuple[DataCursor.CursorState, ...]
        active: DataCursor.Cursor | None
        pinned: tuple[DataCursor.Cursor, ...]
        selected: DataCursor.Cursor | None
        keyboard_target: DataCursor.Cursor | None
        hover_series_idx: int
        hover_index: int
        hover_active: bool

    def __init__(self, ax: Axes, series_list: Sequence[SeriesData]) -> None:
        self.ax = ax
        self.series_list = tuple(series_list)
        self._disp_xy_list: list[np.ndarray] | None = None
        self._disp_indices_list: list[np.ndarray] | None = None
        self._disp_cache_valid = False
        self._disp_cache_signature: tuple[float, ...] | None = None
        self._valid_indices_list: list[np.ndarray] = []
        self._active: DataCursor.Cursor | None = None
        self._pinned: list[DataCursor.Cursor] = []
        self._selected: DataCursor.Cursor | None = None
        self._keyboard_target: DataCursor.Cursor | None = None
        self._dragging_cursor: DataCursor.Cursor | None = None
        self._drag_start_mouse: tuple[float, float] | None = None
        self._drag_start_position: tuple[float, float] | None = None
        for series in self.series_list:
            valid_indices = np.flatnonzero(series.valid_mask)
            self._valid_indices_list.append(valid_indices)

        first_idx = int(self._valid_indices_list[0][0])
        first_series = self.series_list[0]
        (self.hover_highlight,) = ax.plot(
            [first_series.frames[first_idx]],
            [first_series.values[first_idx]],
            marker="o",
            color=first_series.color,
            markersize=10,
            markeredgecolor="gold",
            markeredgewidth=2,
            zorder=6,
        )
        self.hover_highlight.set_visible(False)
        self._hover_series_idx = 0
        self._hover_index = first_idx
        self._hover_active = False

        self.fig = ax.figure
        self._axis_callback_ids = [
            self.ax.callbacks.connect("xlim_changed", self._invalidate_disp_cache),
            self.ax.callbacks.connect("ylim_changed", self._invalidate_disp_cache),
        ]
        self._connected = True

    @property
    def cursors(self) -> list[Cursor]:
        """Persistent selections, retained for session inspection."""

        return ([self._active] if self._active is not None else []) + list(
            self._pinned
        )

    @property
    def active_selection(self) -> Cursor | None:
        if self._active is None or not self._active.highlight.get_visible():
            return None
        return self._active

    @property
    def pinned_selections(self) -> tuple[Cursor, ...]:
        return tuple(self._pinned)

    @property
    def keyboard_target(self) -> Cursor | None:
        return self._keyboard_target

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

    def clear_keyboard_focus(self) -> bool:
        """Relinquish this panel's clicked target and persistent focus style."""

        changed = self._keyboard_target is not None or self._selected is not None
        self._keyboard_target = None
        self._select_cursor(None)
        self._reconcile_hover_visuals()
        return changed

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

    def _nearest_point_from_px(
        self, x_px: float, y_px: float
    ) -> tuple[int, int, float]:
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
        return best_series_idx, best_local_idx, float(best_d2)

    def hide_hover(self) -> bool:
        """Hide the transient preview and restore persistent marker styling."""

        if not self._hover_active:
            return False
        self._hover_active = False
        self.hover_highlight.set_visible(False)
        overlap = self._selection_at(self._hover_series_idx, self._hover_index)
        if overlap is not None:
            overlap.apply_style(overlap is self._selected)
        return True

    def _selection_at(self, series_idx: int, local_idx: int) -> Cursor | None:
        for cursor in self.cursors:
            if (
                cursor.highlight.get_visible()
                and cursor.series_idx == series_idx
                and cursor.current_index == local_idx
            ):
                return cursor
        return None

    def _reconcile_hover_visuals(self) -> None:
        """Derive hover preview visibility and persistent marker focus."""

        overlap = (
            self._selection_at(self._hover_series_idx, self._hover_index)
            if self._hover_active
            else None
        )
        for cursor in self.cursors:
            cursor.apply_style(cursor is self._selected or cursor is overlap)

        if not self._hover_active or overlap is not None:
            self.hover_highlight.set_visible(False)
            return

        series = self.series_list[self._hover_series_idx]
        self.hover_highlight.set_data(
            [series.frames[self._hover_index]],
            [series.values[self._hover_index]],
        )
        self.hover_highlight.set_color(series.color)
        self.hover_highlight.set_markeredgecolor("gold")
        self.hover_highlight.set_visible(True)

    def _pinned_at(self, series_idx: int, local_idx: int) -> Cursor | None:
        return next(
            (
                cursor
                for cursor in self._pinned
                if cursor.series_idx == series_idx
                and cursor.current_index == local_idx
            ),
            None,
        )

    def _remove_pinned_cursor(
        self, cursor: Cursor, *, request_draw: bool = True
    ) -> None:
        if cursor is self._keyboard_target:
            self._keyboard_target = None
        was_selected = cursor is self._selected
        cursor.highlight.remove()
        cursor.tooltip.remove()
        self._pinned.remove(cursor)
        if was_selected:
            self._select_cursor(None)
        self._reconcile_hover_visuals()
        if request_draw:
            self.fig.canvas.draw_idle()

    def _new_cursor(self, series_idx: int, local_idx: int, role: str) -> Cursor:
        series = self.series_list[series_idx]
        cursor = DataCursor.Cursor(
            self.ax,
            series.frames[local_idx],
            series.values[local_idx],
            series_idx,
            series.color,
            role,
        )
        self._update_cursor_visuals(cursor, local_idx, show_tooltip=True)
        cursor.highlight.set_visible(True)
        return cursor

    def _update_cursor_visuals(
        self, cursor: Cursor, local_idx: int, show_tooltip: bool = False
    ) -> None:
        series = self.series_list[cursor.series_idx]
        frames = series.frames
        values = series.values

        if not 0 <= local_idx < len(frames):
            return

        cursor.current_index = local_idx
        x_value, y_value = frames[local_idx], values[local_idx]
        cursor.highlight.set_data([x_value], [y_value])
        if not show_tooltip:
            return

        cursor.tooltip.xy = (x_value, y_value)
        frame_text = self.ax.xaxis.get_major_formatter().format_data_short(x_value)
        value_text = self.ax.yaxis.get_major_formatter().format_data_short(y_value)
        cursor.tooltip.set_text(f"Frame: {frame_text}\nValue: {value_text}")
        cursor.tooltip.set_visible(True)

    def on_hover(self, event: MouseEvent) -> bool:
        """React to one motion event; return whether a redraw is needed."""

        if self._dragging_cursor is not None:
            if event.x is None or event.y is None:
                return False
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
            return False
        if event.inaxes is not self.ax:
            return self.hide_hover()
        if event.x is None or event.y is None:
            return False

        series_idx, local_idx, distance_squared = self._nearest_point_from_px(
            event.x, event.y
        )
        if distance_squared > self._HIT_RADIUS_PIXELS**2:
            return self.hide_hover()

        old_point = (self._hover_series_idx, self._hover_index)
        old_overlap = self._selection_at(
            self._hover_series_idx, self._hover_index
        )
        if old_overlap is not None:
            old_overlap.apply_style(old_overlap is self._selected)

        self._hover_series_idx = series_idx
        self._hover_index = local_idx
        self._hover_active = True
        overlap = self._selection_at(series_idx, local_idx)
        if overlap is not None:
            changed = self.hover_highlight.get_visible()
            self.hover_highlight.set_visible(False)
            overlap.apply_style(True)
            return changed or overlap is not old_overlap or old_point != (
                series_idx,
                local_idx,
            )

        series = self.series_list[series_idx]
        self.hover_highlight.set_data(
            [series.frames[local_idx]], [series.values[local_idx]]
        )
        self.hover_highlight.set_color(series.color)
        self.hover_highlight.set_markeredgecolor("gold")
        changed = not self.hover_highlight.get_visible()
        self.hover_highlight.set_visible(True)
        return changed or old_overlap is not None or old_point != (
            series_idx,
            local_idx,
        )

    def on_click(self, event: MouseEvent) -> Cursor | None:
        if getattr(event, "button", None) == 1:
            for cursor in self.cursors:
                contains, _ = cursor.tooltip.contains(event)
                if contains:
                    self._select_cursor(cursor)
                    self._keyboard_target = cursor
                    self._dragging_cursor = cursor
                    self._drag_start_mouse = (event.x, event.y)
                    self._drag_start_position = cursor.tooltip.get_position()
                    return cursor

        if event.inaxes != self.ax:
            return
        if getattr(event, "button", None) != 1:
            return
        if event.x is None or event.y is None:
            return

        series_idx, local_idx, distance_squared = self._nearest_point_from_px(
            event.x, event.y
        )
        if distance_squared > self._HIT_RADIUS_PIXELS**2:
            return

        is_shift = "shift" in str(getattr(event, "key", "")).lower()
        if is_shift:
            cursor = self._new_cursor(series_idx, local_idx, "pinned")
            self._pinned.append(cursor)
            self._select_cursor(cursor)
            self._keyboard_target = cursor
            cursor.apply_style(True)
            self.hide_hover()
            return cursor

        pinned = self._pinned_at(series_idx, local_idx)
        if pinned is not None:
            self._remove_pinned_cursor(pinned, request_draw=False)
            self.hide_hover()
            self.fig.canvas.draw_idle()
            return None

        active = self.active_selection
        if (
            active is not None
            and active.series_idx == series_idx
            and active.current_index == local_idx
        ):
            self.clear_active()
            self.hide_hover()
            self.fig.canvas.draw_idle()
            return None

        if self._active is None:
            self._active = self._new_cursor(series_idx, local_idx, "active")
        else:
            cursor = self._active
            cursor.series_idx = series_idx
            cursor.color = self.series_list[series_idx].color
            cursor.highlight.set_color(cursor.color)
            self._update_cursor_visuals(cursor, local_idx, show_tooltip=True)
            cursor.highlight.set_visible(True)
        cursor = self._active
        self._select_cursor(cursor)
        self._keyboard_target = cursor
        cursor.apply_style(True)
        self.hide_hover()
        return cursor

    def clear_active(self) -> bool:
        cursor = self.active_selection
        if cursor is None:
            return False
        cursor.highlight.set_visible(False)
        cursor.tooltip.set_visible(False)
        if self._selected is cursor:
            self._selected = None
        if self._keyboard_target is cursor:
            self._keyboard_target = None
        return True

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

        cursor = self._keyboard_target
        if cursor is None:
            return

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
            self._update_cursor_visuals(cursor, selected_idx, show_tooltip=True)
            cursor.highlight.set_visible(True)
            self._reconcile_hover_visuals()
            self.fig.canvas.draw_idle()

    def remove_selected_cursor(self) -> bool:
        cursor = self._selected
        if cursor is None or cursor.role != "pinned":
            return False
        self._remove_pinned_cursor(cursor)
        return True

    def clear_extra_cursors(self, *, request_draw: bool = True) -> int:
        extras = list(self._pinned)
        for cursor in extras:
            self._remove_pinned_cursor(cursor, request_draw=False)
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
                    series_idx=cursor.series_idx,
                    color=cursor.color,
                    role=cursor.role,
                    marker_visible=cursor.highlight.get_visible(),
                    tooltip_visible=cursor.tooltip.get_visible(),
                    tooltip_anchor=tuple(cursor.tooltip.xy),
                    tooltip_position=cursor.tooltip.get_position(),
                    tooltip_text=cursor.tooltip.get_text(),
                )
                for cursor in self.cursors
            ),
            active=self._active,
            pinned=tuple(self._pinned),
            selected=self._selected,
            keyboard_target=self._keyboard_target,
            hover_series_idx=self._hover_series_idx,
            hover_index=self._hover_index,
            hover_active=self._hover_active,
        )

    def restore_state(self, snapshot: StateSnapshot) -> None:
        captured_cursors = [state.cursor for state in snapshot.cursors]
        for cursor in tuple(self.cursors):
            if cursor in captured_cursors:
                continue
            cursor.highlight.remove()
            cursor.tooltip.remove()
        self._active = snapshot.active
        self._pinned = list(snapshot.pinned)
        self._selected = snapshot.selected
        self._keyboard_target = snapshot.keyboard_target
        for state in snapshot.cursors:
            cursor = state.cursor
            if cursor.highlight.axes is None:
                self.ax.add_line(cursor.highlight)
            if cursor.tooltip.axes is None:
                self.ax.add_artist(cursor.tooltip)
            cursor.series_idx = state.series_idx
            cursor.color = state.color
            cursor.highlight.set_color(state.color)
            cursor.role = state.role
            self._update_cursor_visuals(
                cursor, state.current_index, show_tooltip=False
            )
            cursor.highlight.set_visible(state.marker_visible)
            cursor.tooltip.xy = state.tooltip_anchor
            cursor.tooltip.set_visible(state.tooltip_visible)
            cursor.tooltip.set_position(state.tooltip_position)
            cursor.tooltip.set_text(state.tooltip_text)
            cursor.apply_style(cursor is self._selected)
        self._hover_series_idx = snapshot.hover_series_idx
        self._hover_index = snapshot.hover_index
        self._hover_active = snapshot.hover_active
        self._reconcile_hover_visuals()
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
        self._keyboard_target = None
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
        self._states: dict[Axes, AxesLayoutState] = {}
        self._maximized_position = (0.0, 0.0, 1.0, 1.0)
        self._capture_layout()
        self.maximized_axes: Axes | None = None

    def _capture_layout(self) -> None:
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

    def toggle(self, axis: Axes) -> bool:
        if axis not in self._states:
            raise ValueError("axis does not belong to this PlotSession")
        if self.maximized_axes is axis:
            self.restore()
            return False
        if self.maximized_axes is not None:
            self.restore(request_draw=False)
        else:
            self._capture_layout()
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
    snapshots: tuple[tuple[DataCursor, DataCursor.StateSnapshot], ...]
    previous_active_controller: DataCursor | None
    previous_keyboard_controller: DataCursor | None


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
        self.keyboard_controller: DataCursor | None = None
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
        _suppress_view_navigation_keys()

    def _toolbar_is_active(self) -> bool:
        manager = getattr(self.figure.canvas, "manager", None)
        toolbar = getattr(manager, "toolbar", None)
        return bool(getattr(toolbar, "mode", ""))

    def _set_keyboard_controller(self, controller: DataCursor | None) -> None:
        previous = self.keyboard_controller
        if previous is controller:
            return
        if previous is not None:
            previous.clear_keyboard_focus()
        self.keyboard_controller = controller

    def _sync_keyboard_controller(self, controller: DataCursor) -> None:
        if (
            self.keyboard_controller is controller
            and controller.keyboard_target is None
        ):
            self.keyboard_controller = None

    def _legend_at(self, event: MouseEvent) -> Legend | None:
        return next(
            (
                legend
                for legend in self.legends
                if legend.get_visible() and legend.contains(event)[0]
            ),
            None,
        )

    def _hide_transient_highlights(
        self, except_controller: DataCursor | None = None
    ) -> bool:
        changed = False
        for controller in self.controllers:
            if controller is except_controller:
                continue
            if controller.hide_hover():
                changed = True
        return changed

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
            if self._hide_transient_highlights():
                self.figure.canvas.draw_idle()
            return
        self.active_controller = controller
        need_draw = controller.on_hover(event)
        if self._hide_transient_highlights(controller):
            need_draw = True
        if need_draw:
            self.figure.canvas.draw_idle()

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
            clicked_cursor = controller.on_click(event)
            if clicked_cursor is not None:
                self._set_keyboard_controller(controller)
                self.figure.canvas.draw_idle()
            else:
                self._sync_keyboard_controller(controller)
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
                for snapshot_controller, snapshot in pending.snapshots:
                    snapshot_controller.restore_state(snapshot)
                self.active_controller = pending.previous_active_controller
                self.keyboard_controller = pending.previous_keyboard_controller
            self._pending_axes_click = None
            self.layout.toggle(controller.ax)
            return
        self._pending_axes_click = None
        if getattr(event, "button", None) == 1:
            self._pending_axes_click = PendingAxesClick(
                controller=controller,
                axis=controller.ax,
                snapshots=tuple(
                    (candidate, candidate.capture_state())
                    for candidate in self.controllers
                ),
                previous_active_controller=self.active_controller,
                previous_keyboard_controller=self.keyboard_controller,
            )
        self.active_controller = controller
        clicked_cursor = controller.on_click(event)
        if clicked_cursor is not None:
            if clicked_cursor.role == "active":
                for candidate in self.controllers:
                    if candidate is not controller:
                        candidate.clear_active()
            self._set_keyboard_controller(controller)
            self.figure.canvas.draw_idle()
        else:
            self._sync_keyboard_controller(controller)
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
        key = getattr(event, "key", "").lower()
        controller = (
            self.keyboard_controller
            if key
            in ("left", "right", "home", "end", "delete", "backspace")
            else self.active_controller
        )
        if controller is not None:
            controller.on_key(event)
            self._sync_keyboard_controller(controller)

    def on_draw(self, _event: DrawEvent) -> None:
        for controller in self.controllers:
            controller.invalidate_if_transform_changed()

    def on_close(self, _event: CloseEvent) -> None:
        self.disconnect()

    def remove_selected_cursor(self) -> bool:
        controller = self.keyboard_controller
        if controller is None:
            return False
        removed = controller.remove_selected_cursor()
        self._sync_keyboard_controller(controller)
        return removed

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
        _restore_view_navigation_keys()
        layout_changed = self.layout.restore(request_draw=False)
        for callback_id in self._canvas_callback_ids:
            self.figure.canvas.mpl_disconnect(callback_id)
        self._canvas_callback_ids.clear()
        for controller in self.controllers:
            controller.disconnect()
        for legend in self.legends:
            legend.set_draggable(False)
        self.active_controller = None
        self.keyboard_controller = None
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
    figure, axes_grid = plt.subplots(
        row_count, column_count, squeeze=False,
        figsize=(6 * column_count, max(4, 10 * row_count / 3)),
        facecolor=CANVAS,
    )
    controllers: list[DataCursor] = []
    axes: list[Axes] = []
    legends: list[Legend] = []
    try:
        families = font_families()
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

                style_axes(ax, families)

                for item in panel_series:
                    line_kwargs = {
                        "alpha": item.line_alpha, "zorder": 2,
                        "color": item.line_color if item.line_color is not None
                        else item.color,
                        "linewidth": 1.35, "solid_capstyle": "round",
                    }
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
                        s=10,
                        linewidths=0,
                        zorder=3,
                        alpha=0.75,
                    )
                controller = DataCursor(ax, panel_series)
                controllers.append(controller)
                panel_title = next(
                    (item.panel_title for item in panel_series if item.panel_title),
                    None,
                )
                if panel_title:
                    ax.set_title(panel_title, pad=9, fontsize=11,
                                 fontweight="semibold", color=TEXT,
                                 fontfamily=families)
                    ax.title.set_horizontalalignment("left")
                    ax.title.set_x(0)
                ax.set_xlabel("Frame Number")
                ax.set_ylabel("Value")
                legend = ax.legend(
                    loc="upper right", prop={"family": families, "size": 8},
                    facecolor="white", edgecolor=BORDER, framealpha=0.95,
                    labelcolor=TEXT, borderpad=0.7, labelspacing=0.45,
                    handlelength=2, handletextpad=0.7,
                )
                legend.get_frame().set_linewidth(0.6)
                legend.set_draggable(True)
                legends.append(legend)

        figure.tight_layout(pad=1.4, h_pad=1.7, w_pad=1.7)
        install_toolbar_toggle(figure)
        dispatcher = FigureDispatcher(figure, controllers, axes)
        return PlotSession(figure, tuple(controllers), tuple(axes), dispatcher)
    except Exception:
        for controller in controllers:
            controller.disconnect()
        for legend in legends:
            legend.set_draggable(False)
        plt.close(figure)
        raise
