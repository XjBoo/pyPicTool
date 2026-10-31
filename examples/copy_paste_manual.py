"""Manual acceptance scene for same-figure and cross-window curve paste.

Run without arguments to open both figures and follow the printed steps.
Run with --check to build and validate the scene without showing windows.
"""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from interactive_plotting import figure


INSTRUCTIONS = """
曲线复制粘贴手工验收
====================

1. 同一 Figure 的跨子图粘贴，不退出选线模式
   在“源图”子图 1 按 L，点击蓝色 Source A 曲线，按 Ctrl+C（macOS 也可 Cmd+C）。
   保持整线模式，移动到源图子图 2 的空白区域：应出现浅色虚线预览，点击后出现蓝色目标框，
   按 Ctrl+V。确认曲线、标签和图例出现在子图 2，源子图 1 不变。再按一次 Ctrl+V，
   确认同图连续粘贴生成同名独立副本。点击曲线本身时仍应选线，而不是确认粘贴目标。

2. 任意窗口 Esc 退出所有整线模式
   回到源图子图 1 选择 Source A 并复制。切换到“目标图”，在子图 2 的空白区域悬停并点击，
   按 Ctrl+V。确认曲线和标签出现且目标框保留。现在在“目标图”按 Esc：
   源图的“选线”按钮和金色选择应同时退出，所有窗口的目标预览和目标框应消失，
   粘贴快捷键不应再新增曲线，但剪贴板快照仍保留。
   在目标图按 L 重新进入整线模式：已有快照应重新激活，点击空白区域后可按 Ctrl+V 再次粘贴。

3. 动态右轴
   在源图按 L，进入子图 3 选择右轴 Pressure Source 并复制。切换到目标图子图 3
   （当前只有左轴），点击空白区域后按 Ctrl+V。确认自动新增右轴、共享 X 范围，
   并出现合并图例。

4. 关闭源窗口后粘贴
   在源图子图 1 再选择并复制一次 Source A，然后关闭“源图”窗口。在目标图子图 1
   点击空白区域并按 Ctrl+V，确认复制会话仍有效、快照不依赖源窗口，曲线仍带原标签。

提示：只要还有任意 Figure 处于整线模式，在目标窗口按 Esc 也会退出所有整线模式。
关闭两个 Figure 结束本场景。
"""


def make_sessions():
    """Build two independent acceptance figures without showing them."""
    x = np.linspace(0, 10, 81)
    source_description = figure(
        rows=2, cols=2, figsize=(11, 8),
        title="源图：同一 Figure 跨子图与跨窗口复制",
        window_title="曲线复制粘贴 - 源图",
    )
    source_left = source_description.subplot(
        1, title="源 1：左轴曲线（选择并复制）",
        xlabel="Time / s", ylabel="Amplitude",
    )
    source_left.plot(
        x, np.sin(x), label="Source A", color="#3478A8",
        marker=None, linewidth=2,
    )
    source_description.subplot(
        2, title="源 2：空白目标子图（同图粘贴）",
        xlabel="Time / s", ylabel="Amplitude",
    )
    source_right = source_description.subplot(
        3, title="源 3：右轴曲线（测试动态右轴）",
        xlabel="Time / s", ylabel="Temperature", right_ylabel="Pressure / kPa",
    )
    source_right.plot(
        x, 100 + 8 * np.cos(x / 2), label="Pressure Source",
        color="#D58945", marker="^", markersize=5, yaxis="right",
    )

    target_description = figure(
        rows=2, cols=2, figsize=(11, 8),
        title="目标图：已有曲线、空白子图与单轴面板",
        window_title="曲线复制粘贴 - 目标图",
    )
    target_existing = target_description.subplot(
        1, title="目标 1：已有曲线（接收跨窗口粘贴）",
        xlabel="Time / s", ylabel="Amplitude",
    )
    target_existing.plot(
        x, np.cos(x), label="Target Existing", color="#2CA02C",
        marker=None, linewidth=1.8,
    )
    target_description.subplot(
        2, title="目标 2：空白子图（接收同图或跨窗口粘贴）",
        xlabel="Time / s", ylabel="Amplitude",
    )
    target_single_axis = target_description.subplot(
        3, title="目标 3：单轴面板（接收右轴曲线）",
        xlabel="Time / s", ylabel="Level",
    )
    target_single_axis.plot(
        x, 50 + 3 * np.sin(x), label="Target Left",
        color="#9467BD", marker=".", linestyle="--",
    )

    sessions = []
    try:
        sessions.append(source_description.build())
        sessions.append(target_description.build())
        return tuple(sessions)
    except Exception:
        for session in sessions:
            session.close()
        raise


def check_scene(sessions) -> None:
    """Fail fast when the acceptance scene no longer contains required targets."""
    source, target = sessions
    assert len(source.axes) == 4 and len(target.axes) == 4
    assert source.right_axes.get(3) is not None
    assert not target.right_axes
    assert target.axes[3].get_visible() is False
    source_empty = source.axes[1]
    target_empty = target.axes[1]
    assert not any(record.primary_axis is source_empty for record in source.series)
    assert not any(record.primary_axis is target_empty for record in target.series)
    print(
        "验收场景构建成功：源图 4 个子图（含空白与右轴），"
        "目标图 3 个显式子图（含空白与未使用隐藏格子）。"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="build and validate the scene without showing windows",
    )
    args = parser.parse_args()
    sessions = make_sessions()
    try:
        check_scene(sessions)
        if args.check:
            return
        print(INSTRUCTIONS)
        plt.show()
    finally:
        for session in sessions:
            session.close()


if __name__ == "__main__":
    main()
