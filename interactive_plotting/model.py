"""Temporary internal plotting model at the future adapter boundary."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike


@dataclass(frozen=True, slots=True)
class SeriesData:
    """Normalized data for one plotted series in one subplot panel.

    This is the plotting package's temporary internal format.  It is not a
    contract for the external data-producing script, whose format is unknown.
    """

    frames: ArrayLike
    values: ArrayLike
    label: str
    panel: tuple[int, int] = (0, 0)
    color: str = "red"
    panel_title: str | None = None
    line_color: str | None = None
    line_alpha: float = 1.0

    def __post_init__(self):
        object.__setattr__(self, "frames", np.asarray(self.frames))
        object.__setattr__(self, "values", np.asarray(self.values))
