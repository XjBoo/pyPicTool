"""TODO ledger demo: dual y axes, enums, callbacks and MATLAB-like appearance.

Run: venv/bin/python -m examples.plot_features
Export: MPLBACKEND=Agg venv/bin/python -m examples.plot_features --save /tmp/features.png
"""
import argparse
import matplotlib.pyplot as plt
from interactive_plotting import figure, build_figure, SuptitleStyle


def make_figure():
    fig = figure(rows=2, theme="matlab", figsize=(11, 8),
                 window_title="pyPicTool · 绘图功能示例",
                 title="采集结果\n双轴、状态枚举与自定义提示",
                 suptitle_style=SuptitleStyle(fontsize=16, linespacing=1.4))
    panel = fig.subplot(1, title="温度与压力", xlabel="时间 / s",
                        ylabel="温度 / °C", right_ylabel="压力 / kPa",
                        legend_loc="upper left")
    panel.plot([0, 1, 2, 3, 4], [20, 24, 23, 27, 25], label="温度", marker="o",
               tooltip=lambda p: f"{p.series.label}\n时间: {p.x_text} s\n温度: {p.y_text} °C")
    panel.plot([0, 1, 2, 3, 4], [100, 130, 110, 140, 120], label="压力",
               yaxis="right", marker="s", linestyle="--")
    panel.plot([0, 1, 2, 3, 4], [40, 45, 48, 50, 44], label="可删除的高温曲线")
    fig.subplot(2, title="设备状态", xlabel="时间 / s", ylabel="状态",
                y_enum={0: "关闭", 1: "运行", 2: "故障"}, legend_loc="upper left").plot(
                    [0, 1, 2, 3, 4], [0, 1, 1, 2, 0], label="设备 A")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save")
    args = parser.parse_args()
    # Both make_figure().build() and the public spec entry point are supported.
    session = build_figure(make_figure().to_spec())
    try:
        if args.save:
            session.figure.savefig(args.save, dpi=150)
        else:
            plt.show()
    finally:
        session.close()


if __name__ == "__main__":
    main()
