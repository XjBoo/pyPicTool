"""Temporary internal plotting model at the future adapter boundary."""

from dataclasses import dataclass
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
    color: str = "red"
    panel_title: str | None = None
    line_color: str | None = None
    line_alpha: float = 1.0

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
        if len(self.panel) != 2 or any(
            not isinstance(position, int) or position < 0 for position in self.panel
        ):
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
