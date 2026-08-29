"""Shared artificial data for the throwaway backend comparison prototypes.

PROTOTYPE / THROWAWAY: this module is intentionally tiny and is not a
production data contract.  All three candidates receive the same in-memory
shape so that their native interaction affordances can be compared.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Curve:
    panel: tuple[int, int]
    label: str
    color: str
    frames: np.ndarray
    values: np.ndarray


def make_demo_data(seed: int = 7) -> list[Curve]:
    """Return six panels x two curves x 100 points, deterministically."""

    rng = np.random.default_rng(seed)
    frames = np.arange(100, dtype=float)
    result: list[Curve] = []
    for panel_index in range(6):
        panel = divmod(panel_index, 2)
        frequency = panel_index + 1
        result.extend(
            [
                Curve(
                    panel,
                    f"Signal {frequency} (red)",
                    "red",
                    frames.copy(),
                    np.sin(frames * 0.05 * frequency)
                    + rng.normal(0, 0.1, frames.size),
                ),
                Curve(
                    panel,
                    f"Signal {frequency} (blue)",
                    "blue",
                    frames.copy(),
                    np.cos(frames * 0.03 * frequency)
                    + rng.normal(0, 0.15, frames.size),
                ),
            ]
        )
    return result


def grouped_data(seed: int = 7) -> dict[tuple[int, int], list[Curve]]:
    grouped: dict[tuple[int, int], list[Curve]] = {}
    for curve in make_demo_data(seed):
        grouped.setdefault(curve.panel, []).append(curve)
    return grouped
