"""Repeatable Agg benchmark for vectorized nearest-point hover handling."""

from __future__ import annotations

import argparse
import json
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
    callback_counts: dict[str, int] | None = None
    for _ in range(repeats):
        session = create_interactive_plot(make_benchmark_series(points, panels))
        canvas = session.figure.canvas
        axis = session.controllers[0].ax
        canvas.draw()
        sample_indices = np.linspace(0, points - 1, event_count, dtype=int)
        events = []
        for index in sample_indices:
            x_pixel, y_pixel = axis.transData.transform(
                (float(index), float(np.sin(index * 0.01)))
            )
            events.append(MouseEvent("motion_notify_event", canvas, x_pixel, y_pixel))

        callbacks = canvas.callbacks.callbacks
        callback_counts = {
            name: len(callbacks.get(name, {})) for name in CANVAS_EVENTS
        }
        original_draw_idle = canvas.draw_idle
        if not include_render:
            canvas.draw_idle = lambda: None
        started = time.perf_counter()
        for event in events:
            callbacks_registry = canvas.callbacks
            callbacks_registry.process("motion_notify_event", event)
        timings.append(time.perf_counter() - started)
        canvas.draw_idle = original_draw_idle
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
        "render_included": include_render,
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
