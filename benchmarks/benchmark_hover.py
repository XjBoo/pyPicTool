"""Repeatable Agg benchmark for vectorized nearest-point hover handling."""

from __future__ import annotations

import argparse
import json
import platform
from unittest.mock import patch
from contextlib import ExitStack
import statistics
import time

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import MouseEvent

from interactive_plotting import SeriesData, create_interactive_plot


CANVAS_EVENTS = (
    "motion_notify_event",
    "button_press_event",
    "button_release_event",
    "key_press_event",
    "draw_event",
    "close_event",
)


def make_benchmark_series(points: int, panels: int) -> list[SeriesData]:
    frames = np.arange(points, dtype=float)
    series: list[SeriesData] = []
    for panel_index in range(panels):
        panel = divmod(panel_index, 2)
        for series_index, color in enumerate(("red", "blue")):
            values = np.sin(frames * 0.01 + panel_index + series_index)
            series.append(
                SeriesData(
                    frames=frames,
                    values=values,
                    label=f"panel-{panel_index}-{color}",
                    panel=panel,
                    color=color,
                )
            )
    return series


def measure(
    points: int,
    panels: int,
    event_count: int,
    repeats: int,
    include_render: bool,
) -> dict[str, object]:
    timings: list[float] = []
    event_timings = []
    draw_counts = []
    blit_counts = []
    callback_counts: dict[str, int] | None = None
    for _ in range(repeats):
        session = create_interactive_plot(make_benchmark_series(points, panels))
        canvas = session.figure.canvas
        axis = session.controllers[0].ax
        canvas.draw()
        pin_x, pin_y = axis.transData.transform((0.0, 0.0))
        pin_event = MouseEvent(
            "button_press_event",
            canvas,
            pin_x,
            pin_y,
            button=1,
            key="shift",
        )
        canvas.callbacks.process("button_press_event", pin_event)
        canvas.draw()
        sample_indices = np.linspace(0, points - 1, event_count, dtype=int)
        events = []
        for number, index in enumerate(sample_indices):
            panel_index = number % panels
            target_axis = session.controllers[panel_index].ax
            x_pixel, y_pixel = target_axis.transData.transform(
                (float(index), float(np.sin(index * 0.01 + panel_index)))
            )
            if number % 5 == 1:
                x_pixel += 9 * canvas.device_pixel_ratio
            elif number % 5 == 2:
                x_pixel, y_pixel = 0, 0
            events.append(MouseEvent("motion_notify_event", canvas, x_pixel, y_pixel))

        callbacks = canvas.callbacks.callbacks
        callback_counts = {
            name: len(callbacks.get(name, {})) for name in CANVAS_EVENTS
        }
        with ExitStack() as stack:
            draw = stack.enter_context(patch.object(canvas, "draw", wraps=canvas.draw))
            blit = stack.enter_context(patch.object(canvas, "blit", wraps=canvas.blit))
            if not include_render:
                stack.enter_context(patch.object(canvas, "draw_idle"))
                layer = getattr(session, "_layer", None)
                if layer is not None and hasattr(layer, "refresh"):
                    stack.enter_context(patch.object(layer, "refresh"))
            started = time.perf_counter()
            for event in events:
                event_started = time.perf_counter()
                canvas.callbacks.process("motion_notify_event", event)
                event_timings.append(time.perf_counter() - event_started)
            timings.append(time.perf_counter() - started)
            draw_counts.append(draw.call_count)
            blit_counts.append(blit.call_count)
        environment = {
            "python": platform.python_version(), "platform": platform.platform(),
            "matplotlib": matplotlib.__version__, "backend": matplotlib.get_backend(),
            "physical_size": list(canvas.get_width_height(physical=True)),
            "logical_size": list(canvas.get_width_height()),
            "device_pixel_ratio": canvas.device_pixel_ratio,
        }
        close = getattr(session, "close", None)
        if close is None:
            plt.close(session.figure)
        else:
            close()

    return {
        "points_per_series": points,
        "panels": panels,
        "series": panels * 2,
        "events": event_count,
        "repeats": repeats,
        "pinned_per_measured_panel": 1,
        "render_included": include_render,
        "environment": environment,
        "input_pattern": "cross-panel exact / offset-9-logical-pixels / outside / exact / exact",
        "event_median_seconds": statistics.median(event_timings),
        "event_p95_seconds": float(np.percentile(event_timings, 95)),
        "full_draws_per_repeat": draw_counts,
        "blits_per_repeat": blit_counts,
        "median_seconds": statistics.median(timings),
        "all_seconds": timings,
        "canvas_callback_counts": callback_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=int, nargs="+", default=[1_000, 10_000])
    parser.add_argument("--panels", type=int, default=6)
    parser.add_argument("--events", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--include-render", action="store_true")
    args = parser.parse_args()
    results = [
        measure(points, args.panels, args.events, args.repeats, args.include_render)
        for points in args.points
    ]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
