"""Local artist styling; never changes Matplotlib's global defaults."""

from dataclasses import dataclass

from matplotlib import font_manager
from matplotlib.axes import Axes


CANVAS = "#F3F5F7"
TEXT = "#243247"
MUTED = "#64748B"
GRID = "#E5EAF0"
BORDER = "#CCD5DF"


@dataclass(frozen=True, slots=True)
class PlotTheme:
    canvas: str
    text: str
    muted: str
    grid: str
    border: str
    colors: tuple[str, ...]
    boxed: bool = False


THEMES = {
    "default": PlotTheme(CANVAS, TEXT, MUTED, GRID, BORDER,
        ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
         "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")),
    "matlab": PlotTheme("#F0F0F0", "#262626", "#262626", "#D9D9D9", "#262626",
        ("#0072BD", "#D95319", "#EDB120", "#7E2F8E", "#77AC30",
         "#4DBEEE", "#A2142F"), boxed=True),
}


def get_theme(name: str) -> PlotTheme:
    if not isinstance(name, str) or name not in THEMES:
        raise ValueError("theme must be 'default' or 'matlab'")
    return THEMES[name]


def font_families() -> list[str]:
    """Use bundled Latin glyphs with available system CJK fallbacks."""
    installed = {font.name for font in font_manager.fontManager.ttflist}
    candidates = (
        "Microsoft YaHei", "SimHei", "PingFang SC", "Heiti SC",
        "Noto Sans CJK SC", "Source Han Sans SC", "Arial Unicode MS",
    )
    return ["DejaVu Sans", *(name for name in candidates if name in installed)]


def style_axes(axis: Axes, families: list[str], theme: PlotTheme | None = None) -> None:
    """Apply the shared hierarchy before layout and interaction capture."""
    theme = theme or THEMES["default"]
    axis.set_facecolor("white")
    axis.set_axisbelow(True)
    axis.grid(True, color=theme.grid, linewidth=0.65, linestyle="-", alpha=1)
    for side, spine in axis.spines.items():
        spine.set_visible(theme.boxed or side in ("left", "bottom"))
        spine.set_color(theme.border)
        spine.set_linewidth(0.7)
    axis.tick_params(axis="both", colors=theme.muted, labelsize=8.5, length=3,
                     width=0.6, pad=4)
    for coordinate_axis in (axis.xaxis, axis.yaxis):
        coordinate_axis.label.set_fontfamily(families)
        coordinate_axis.label.set_fontsize(9)
        coordinate_axis.label.set_color(theme.muted)
        coordinate_axis.labelpad = 5
        coordinate_axis.offsetText.set_fontfamily(families)
        coordinate_axis.offsetText.set_fontsize(8.5)
        coordinate_axis.offsetText.set_color(theme.muted)
        for tick in coordinate_axis.get_major_ticks() + coordinate_axis.get_minor_ticks():
            tick.label1.set_fontfamily(families)
            tick.label2.set_fontfamily(families)
