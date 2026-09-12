"""Panel-local legend placement without changing Matplotlib's normal best mode."""
from __future__ import annotations

import numpy as np
from matplotlib.legend import Legend, DraggableLegend
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox


def _segment_hits(vertices, bounds):
    """Count finite segments intersecting a rectangle (including boundary)."""
    starts, ends = vertices[:-1], vertices[1:]
    valid = np.isfinite(starts).all(axis=1) & np.isfinite(ends).all(axis=1)
    starts, ends = starts[valid], ends[valid]
    delta = ends - starts
    low, high = np.zeros(len(starts)), np.ones(len(starts))
    for dim, minimum, maximum in ((0, bounds.x0, bounds.x1), (1, bounds.y0, bounds.y1)):
        moving = delta[:, dim] != 0
        outside = (~moving) & ((starts[:, dim] < minimum) | (starts[:, dim] > maximum))
        low[outside] = np.inf
        a = np.full(len(starts), -np.inf)
        b = np.full(len(starts), np.inf)
        a[moving] = (minimum - starts[moving, dim]) / delta[moving, dim]
        b[moving] = (maximum - starts[moving, dim]) / delta[moving, dim]
        low = np.maximum(low, np.minimum(a, b))
        high = np.minimum(high, np.maximum(a, b))
    return np.count_nonzero(low <= high)


class _PanelDrag(DraggableLegend):
    def save_offset(self):
        self._original_loc = self.legend._loc
        self._moved = False
        super().save_offset()

    def update_offset(self, dx, dy):
        self._moved = self._moved or dx != 0 or dy != 0
        super().update_offset(dx, dy)

    def finalize_offset(self):
        if self._moved:
            self.legend._corner_auto = False
            super().finalize_offset()
        else:
            # Matplotlib normally turns even a click into an axes coordinate.
            self.legend._set_loc(self._original_loc)


class OverlayLegend(Legend):
    """Keep picking while drawing in the overlay; cache four-corner placement."""

    def __init__(self, *args, data_records=(), **kwargs):
        self._corner_auto = kwargs.get('loc') == 'best_corner'
        if self._corner_auto:
            kwargs['loc'] = 'upper right'
        self._data_records = tuple(data_records)
        self._corner_key = None
        self._corner = None
        super().__init__(*args, **kwargs)

    def set_loc(self, loc=None):
        # Explicit low-level position changes should also override automatic mode.
        if hasattr(self, '_loc_real'):
            self._corner_auto = loc == 'best_corner'
            self._corner_key = None
        super().set_loc('upper right' if loc == 'best_corner' else loc)

    def set_draggable(self, state, use_blit=False, update='loc'):
        if state and self._draggable is None:
            self._draggable = _PanelDrag(self, use_blit=use_blit, update=update)
        elif not state and self._draggable is not None:
            self._draggable.disconnect()
            self._draggable = None
        return self._draggable

    def release_placement(self):
        self._data_records = ()
        self._corner_key = None
        self._corner_auto = False

    def _geometry_key(self, renderer, width, height):
        result = [width, height, renderer.points_to_pixels(1),
                  tuple(self.get_bbox_to_anchor().bounds), self.borderaxespad,
                  self._fontsize]
        for record in self._data_records:
            result.append(record.removed)
            for artist in record.artists:
                result.extend((artist.get_visible(), artist.axes.get_visible(),
                               artist.get_alpha(), tuple(artist.axes.bbox.bounds),
                               tuple(artist.axes.viewLim.bounds),
                               tuple(artist.get_transform().get_matrix().flat)))
                if isinstance(artist, Line2D):
                    result.extend((id(artist.get_path()), artist.get_linestyle(),
                                   artist.get_linewidth(), str(artist.get_color())))
                else:
                    result.extend((id(artist.get_offsets()),
                                   tuple(artist.get_offset_transform().get_matrix().flat),
                                   tuple(artist.get_sizes()), tuple(artist.get_linewidths()),
                                   tuple(map(id, artist.get_paths())),
                                   artist.get_facecolors().tobytes(),
                                   artist.get_edgecolors().tobytes()))
        return tuple(result)

    def _score_corners(self, boxes, renderer):
        scores = np.zeros(4, dtype=np.int64)
        for record in self._data_records:
            if record.removed:
                continue
            for artist in record.artists:
                if (not artist.get_visible() or not artist.axes.get_visible()
                        or artist.get_alpha() == 0):
                    continue
                if isinstance(artist, Line2D):
                    if artist.get_linestyle() in ('None', '', ' ') or artist.get_linewidth() == 0:
                        continue
                    from matplotlib.colors import to_rgba
                    if to_rgba(artist.get_color(), artist.get_alpha())[3] == 0:
                        continue
                    vertices = artist.get_transform().transform_path(artist.get_path()).vertices
                    radius = renderer.points_to_pixels(artist.get_linewidth()) / 2
                    for index, box in enumerate(boxes):
                        clipped = Bbox.intersection(box, artist.axes.bbox)
                        if clipped is not None:
                            scores[index] += _segment_hits(vertices, clipped.padded(radius))
                else:
                    offsets = np.asarray(artist.get_offsets())
                    points = artist.get_offset_transform().transform(offsets)
                    sizes = artist.get_sizes()
                    if not len(sizes) or not len(points):
                        continue
                    # Scatter paths are normalized in marker units. Include their
                    # actual asymmetric extent and stroke in pixel coordinates.
                    paths = artist.get_paths()
                    if not paths:
                        continue
                    ext = paths[0].get_extents()
                    scale = renderer.points_to_pixels(np.sqrt(np.resize(sizes, len(points))))
                    widths = artist.get_linewidths()
                    stroke = renderer.points_to_pixels(np.resize(widths, len(points))) / 2 if len(widths) else 0
                    left = points[:, 0] + ext.x0 * scale - stroke
                    right = points[:, 0] + ext.x1 * scale + stroke
                    bottom = points[:, 1] + ext.y0 * scale - stroke
                    top = points[:, 1] + ext.y1 * scale + stroke
                    visible = np.isfinite(points).all(axis=1)
                    colors = artist.get_facecolors()
                    edges = artist.get_edgecolors()
                    face = np.resize(colors[:, 3], len(points)) > 0 if len(colors) else False
                    edge = np.resize(edges[:, 3], len(points)) > 0 if len(edges) else False
                    visible &= face | edge
                    for index, box in enumerate(boxes):
                        clipped = Bbox.intersection(box, artist.axes.bbox)
                        if clipped is not None:
                            scores[index] += np.count_nonzero(visible & (left <= clipped.x1)
                                & (right >= clipped.x0) & (bottom <= clipped.y1) & (top >= clipped.y0))
        return scores

    def _findoffset(self, width, height, xdescent, ydescent, renderer):
        if self._corner_auto:
            key = self._geometry_key(renderer, width, height)
            if key != self._corner_key:
                codes = (1, 2, 3, 4)
                size = Bbox.from_bounds(0, 0, width, height)
                boxes = [Bbox.from_bounds(*self._get_anchored_bbox(
                    code, size, self.get_bbox_to_anchor(), renderer), width, height) for code in codes]
                scores = self._score_corners(boxes, renderer)
                best = np.flatnonzero(scores == scores.min())
                previous = codes.index(self._corner) if self._corner in codes else -1
                self._corner = codes[previous if previous in best else best[0]]
                self._loc_real = self._corner
                self._corner_key = key
        return super()._findoffset(width, height, xdescent, ydescent, renderer)

    def draw(self, renderer):
        layer = getattr(self, '_interaction_layer', None)
        if layer is None or layer.drawing:
            super().draw(renderer)
