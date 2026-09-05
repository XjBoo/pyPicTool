"""Local artist styling; never changes Matplotlib's global defaults."""

from matplotlib import font_manager
from matplotlib.axes import Axes


CANVAS = "#F3F5F7"
TEXT = "#243247"
MUTED = "#64748B"
GRID = "#E5EAF0"
BORDER = "#CCD5DF"


def font_families() -> list[str]:
    """Use bundled Latin glyphs with available system CJK fallbacks."""
    installed = {font.name for font in font_manager.fontManager.ttflist}
    candidates = (
        "Microsoft YaHei", "SimHei", "PingFang SC", "Heiti SC",
        "Noto Sans CJK SC", "Source Han Sans SC", "Arial Unicode MS",
    )
    return ["DejaVu Sans", *(name for name in candidates if name in installed)]


def style_axes(axis: Axes, families: list[str]) -> None:
    """Apply the shared hierarchy before layout and interaction capture."""
    axis.set_facecolor("white")
    axis.set_axisbelow(True)
    axis.grid(True, color=GRID, linewidth=0.65, linestyle="-", alpha=1)
    for side, spine in axis.spines.items():
        spine.set_visible(side in ("left", "bottom"))
        spine.set_color(BORDER)
        spine.set_linewidth(0.7)
    axis.tick_params(axis="both", colors=MUTED, labelsize=8.5, length=3,
                     width=0.6, pad=3)
    for coordinate_axis in (axis.xaxis, axis.yaxis):
        coordinate_axis.label.set_fontfamily(families)
        coordinate_axis.label.set_fontsize(9)
        coordinate_axis.label.set_color(MUTED)
        coordinate_axis.labelpad = 3
        coordinate_axis.offsetText.set_fontfamily(families)
        coordinate_axis.offsetText.set_fontsize(8.5)
        coordinate_axis.offsetText.set_color(MUTED)
        for tick in coordinate_axis.get_major_ticks() + coordinate_axis.get_minor_ticks():
            tick.label1.set_fontfamily(families)
            tick.label2.set_fontfamily(families)
