"""Normalized plotting data and internal figure descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Mapping
from typing import Literal
from matplotlib.typing import ColorType
import numpy as np
from numpy.typing import ArrayLike, NDArray


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
    color: ColorType = "red"
    panel_title: str | None = None
    line_color: ColorType | None = None
    line_alpha: float = 1.0
    marker: str | None = "o"
    linestyle: str = "-"
    linewidth: float = 1.35
    markersize: float = 10 ** 0.5

    yaxis: Literal["left", "right"] = "left"
    tooltip: Callable[[TooltipContext], str] | None = None

    def __post_init__(self) -> None:
        try:
            frames = np.asarray(self.frames)
            values = np.asarray(self.values)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Series '{self.label}' must contain numeric arrays"
            ) from error

        if frames.ndim != 1 or values.ndim != 1:
            raise ValueError(
                f"Series '{self.label}' frames and values must be one-dimensional"
            )
        if frames.size == 0 or values.size == 0:
            raise ValueError(
                f"Series '{self.label}' frames and values must be non-empty"
            )
        if frames.size != values.size:
            raise ValueError(
                f"Series '{self.label}' frames and values must have equal length"
            )
        for field_name, array in (("frames", frames), ("values", values)):
            is_real_numeric = np.issubdtype(
                array.dtype, np.number
            ) and not np.issubdtype(array.dtype, np.complexfloating)
            if not is_real_numeric:
                raise ValueError(f"Series '{self.label}' {field_name} must be numeric")
        if not np.all(np.isfinite(frames)):
            raise ValueError(f"Series '{self.label}' frames must all be finite")
        if not np.any(np.isfinite(values)):
            raise ValueError(
                f"Series '{self.label}' must contain at least one valid value"
            )
        panel_is_valid = (
            isinstance(self.panel, tuple)
            and len(self.panel) == 2
            and all(
                isinstance(position, int)
                and not isinstance(position, bool)
                and position >= 0
                for position in self.panel
            )
        )
        if not panel_is_valid:
            raise ValueError(
                f"Series '{self.label}' panel must contain two non-negative integers"
            )

        frames = np.array(frames, copy=True)
        values = np.array(values, dtype=float, copy=True)
        frames.setflags(write=False)
        values.setflags(write=False)
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "values", values)

    @property
    def valid_mask(self) -> NDArray[np.bool_]:
        return np.isfinite(self.values)

    @property
    def plotting_values(self) -> NDArray[np.float64]:
        values = np.array(self.values, copy=True)
        values[~self.valid_mask] = np.nan
        return values


@dataclass(frozen=True, slots=True)
class TooltipContext:
    """A selected original-array point, including axis-formatted values."""

    series: SeriesData
    index: int
    x: float
    y: float
    x_text: str
    y_text: str


@dataclass(frozen=True, slots=True)
class SuptitleStyle:
    fontsize: float = 14
    fontweight: str = "semibold"
    linespacing: float = 1.3
    horizontalalignment: str = "center"


@dataclass(frozen=True, slots=True)
class PanelSpec:
    """One explicitly present panel, including panels without data."""

    panel: tuple[int, int]
    series: tuple[SeriesData, ...] = ()
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    right_ylabel: str | None = None
    y_enum: Mapping[float, str] | None = None
    right_y_enum: Mapping[float, str] | None = None
    legend_loc: str = "upper right"


@dataclass(frozen=True, slots=True)
class FigureSpec:
    """Complete construction input shared by public and compatibility callers."""

    rows: int
    cols: int
    panels: tuple[PanelSpec, ...]
    title: str = ""
    figsize: tuple[float, float] | None = None
    theme: str = "default"
    window_title: str | None = None
    suptitle_style: SuptitleStyle = SuptitleStyle()
