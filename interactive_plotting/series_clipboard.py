"""Process-local clipboard holding one independent curve snapshot."""

from dataclasses import replace

from .model import SeriesData


_current_series: SeriesData | None = None
_active = False


def store_series(series: SeriesData) -> SeriesData:
    """Replace the clipboard with a deep snapshot and arm paste targeting."""
    if not isinstance(series, SeriesData):
        raise ValueError("series must be SeriesData")
    global _current_series, _active
    snapshot = replace(series)
    _current_series = snapshot
    _active = True
    return snapshot


def get_series() -> SeriesData | None:
    """Return the retained snapshot even while paste targeting is inactive."""
    return _current_series


def arm() -> bool:
    """Re-activate paste targeting when a snapshot is still available."""
    global _active
    _active = _current_series is not None
    return _active


def disarm() -> None:
    """Keep the snapshot but stop accepting new paste targets."""
    global _active
    _active = False


def is_active() -> bool:
    """Whether the copied snapshot currently accepts paste targets."""
    return _active and _current_series is not None


def clear() -> None:
    """Reset module state for isolated tests and process teardown."""
    global _current_series, _active
    _current_series = None
    _active = False
