"""Run with python -m examples.flexible_plot [--save-dir DIRECTORY]."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from interactive_plotting import figure


def make_figures():
    """Build two independent figures, including an empty and an unused panel."""
    x = np.linspace(0, 10, 21)
    comparison = figure(rows=2, cols=2, title="实验结果 / Experiment overview",
                        figsize=(11, 8))
    temperature = comparison.subplot(
        1, title="温度变化 / Temperature", xlabel="Time / s", ylabel="Temperature / °C",
    )
    temperature.plot(x, 20 + np.sin(x), label="Sensor A", color="#3478A8", marker="o")
    temperature.plot(x, 20 + np.cos(x), label="Sensor B", color="#D58945",
                     marker="s", linestyle="--")
    comparison.subplot(3, title="Reserved panel", xlabel="Time / s", ylabel="Value")
    comparison.subplot(4, title="Pressure", xlabel="Time / s", ylabel="Pressure / kPa").plot(
        x, 100 + 2 * np.sin(x / 2), label="Pressure", marker="^", markersize=5,
    )

    detail = figure(title="Independent figure", figsize=(8, 5))
    detail.subplot(1, title="Line and point styles", xlabel="Time / s", ylabel="Amplitude").plot(
        x, np.sin(x), label="Line", marker=None,
    ).plot(x, np.cos(x), label="Points", marker="x", linestyle="None", markersize=6)
    sessions = []
    try:
        sessions.append(comparison.build())
        sessions.append(detail.build())
        return sessions
    except Exception:
        for session in sessions:
            session.close()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-dir", type=Path)
    args = parser.parse_args()
    sessions = make_figures()
    try:
        if args.save_dir:
            args.save_dir.mkdir(parents=True, exist_ok=True)
            for index, session in enumerate(sessions, start=1):
                session.figure.savefig(args.save_dir / f"figure-{index}.png", dpi=120)
        else:
            plt.show()
    finally:
        for session in sessions:
            session.close()


if __name__ == "__main__":
    main()
