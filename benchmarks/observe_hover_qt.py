"""Observe real Qt hover timing without synthesizing mouse input.

Run with PYTHONPATH=. and close the window to print the collected JSON.
Paint completion is a software proxy, not physical display latency.
"""
import argparse
import json
import time
import statistics

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.qt_compat import QT_API, QtCore
from interactive_plotting import create_interactive_plot, make_demo_series, figure
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dual", action="store_true")
    args = parser.parse_args()
    samples = []
    original_motion = FigureCanvasQTAgg.mouseMoveEvent
    original_paint = FigureCanvasQTAgg.paintEvent
    original_draw = FigureCanvasQTAgg.draw

    def motion(canvas, event):
        started = time.perf_counter()
        record = {'received': started, 'device_pixel_ratio': canvas.device_pixel_ratio}
        canvas._hover_observation = record
        samples.append(record)
        try:
            return original_motion(canvas, event)
        finally:
            record['handler_ms'] = (time.perf_counter() - started) * 1000

    def draw(canvas):
        started = time.perf_counter()
        result = original_draw(canvas)
        record = getattr(canvas, '_hover_observation', None)
        if record is not None:
            record['full_draw_ms'] = (time.perf_counter() - started) * 1000
        return result

    def paint(canvas, event):
        started = time.perf_counter()
        result = original_paint(canvas, event)
        record = getattr(canvas, '_hover_observation', None)
        if record is not None and 'paint_completed_ms' not in record:
            record['paint_started_ms'] = (started - record['received']) * 1000
            record['paint_completed_ms'] = (time.perf_counter() - record['received']) * 1000
        return result

    FigureCanvasQTAgg.mouseMoveEvent = motion
    FigureCanvasQTAgg.paintEvent = paint
    FigureCanvasQTAgg.draw = draw
    if args.dual:
        builder = figure(rows=2)
        panel = builder.subplot(1, right_ylabel='Right axis')
        panel.plot([0, 1, 2, 3], [0, 1, 0, 1], label='Left')
        panel.plot([0, 1, 2, 3], [100, 120, 110, 100], label='Right', yaxis='right')
        builder.subplot(2).plot([0, 1, 2, 3], [1, 0, 1, 0], label='Other panel')
        session = builder.build()
    else:
        session = create_interactive_plot(make_demo_series(seed=42))
    canvas = session.figure.canvas
    canvas.manager.set_window_title('Hover responsiveness verification')
    canvas.draw()
    environment = {
        'matplotlib': matplotlib.__version__, 'qt_api': QT_API,
        'qt_version': QtCore.qVersion(), 'device_pixel_ratio': canvas.device_pixel_ratio,
        'physical_size': canvas.get_width_height(physical=True),
        'logical_size': canvas.get_width_height(),
    }
    try:
        plt.show()
    finally:
        # Qt adopts the screen's scale after showing the window. Report the
        # final live canvas dimensions, not the pre-show defaults.
        environment.update(
            device_pixel_ratio=canvas.device_pixel_ratio,
            physical_size=canvas.get_width_height(physical=True),
            logical_size=canvas.get_width_height(),
        )
        session.close()
        FigureCanvasQTAgg.mouseMoveEvent = original_motion
        FigureCanvasQTAgg.paintEvent = original_paint
        FigureCanvasQTAgg.draw = original_draw
    durations = [s['paint_completed_ms'] for s in samples if 'paint_completed_ms' in s]
    print(json.dumps({
        'environment': environment, 'mouse_events': len(samples),
        'events_with_paint': len(durations),
        'paint_proxy_median_ms': statistics.median(durations) if durations else None,
        'note': 'Real input only. Time to next paint may include other UI actions; it is not physical display latency or isolated hover latency.',
        'samples': samples,
    }, indent=2))


if __name__ == '__main__':
    main()
