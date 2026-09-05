# 视觉改造验证记录

日期：2026-09-05。变更：`refine-plot-visual-design`。

## 视觉结果

- [改造前](before.png) / [改造后](after.png)：相同 seed=42，12×10 英寸，120 dpi，六面板输入数组逐项相等。
- [选中提示框](selected.png)、[放大面板](maximized.png)、[单面板](single.png)：已打开检查，当前示例文字无重叠，圆形金色焦点与数据清晰可辨。
- tooltip 保留原有偏移与拖动机制；靠边或峰值处可能跨出面板，可拖至空白位置。本次没有增加自动避让算法。

## 自动化检查

| 检查 | 本轮结果 |
| --- | --- |
| `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` | 通过，61 项，退出码 0 |
| `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` | 通过，退出码 0；每系列 1,000/10,000 点均完成，无性能阈值，不宣称性能指标达标 |
| `openspec validate --changes` | 通过，1 项，退出码 0 |
| `git diff --check` | 通过，退出码 0；不等同 Lint |
| 类型检查 | 覆盖缺口：有 mypy 配置，无已采用命令/安装工具 |
| Lint/格式 | 覆盖缺口：有 Ruff 配置，无已采用命令/安装工具 |
| 构建 | 覆盖缺口：无 build-system 或已采用构建命令 |
| E2E | 覆盖缺口：无独立套件；自动化交互使用 Agg |
| 安全扫描 | 覆盖缺口：无 secret scan、SAST、依赖漏洞扫描命令 |

新增检查覆盖显式样式保留、数据缺失断线、图例颜色、字体缺失回退、动态创建 tooltip、全局 rcParams 隔离、150 dpi 命中和键盘移动、标题/图例边界、放大恢复。原有 57 项测试全部保留。首轮发现左侧标题导致 `get_title()` 为空，已通过保留原标题对象修复，最终完整检查通过。

## macOS QtAgg 实际窗口

运行命令：`venv/bin/python interactive_plot.py`。
沙箱内首次启动因无法连接 macOS 窗口服务退出 134；沙箱外重试成功，完成下列操作后关闭，进程退出 0。使用实际 CUA 鼠标键盘操作及窗口截图观察：

| 场景 | 结果 |
| --- | --- |
| 启动、六面板显示、窗口缩窄 | 通过，标题和刻度可读 |
| 普通点击数据点 | 通过，出现圆形金边和 Frame/Value |
| Right、Left、Home、End | 通过，观察到 Frame 41、99、0 等变化 |
| tooltip 拖动 | 通过，文字框位置与连接箭头更新 |
| 整块图例拖动 | 通过，从右上拖至右下 |
| 双击背景、Esc 恢复 | 通过，放大单面板后恢复六面板，保留选中及拖动位置 |
| 工具栏 pan/zoom | 通过，坐标范围随拖动/矩形选区变化 |
| pan 模式下 Home | 通过，不重置平移后的视图 |
| 关闭窗口 | 通过，脚本退出 0 |
| 独立悬停、Shift+点击钉选、Delete/Backspace、未放大时 Esc 清除钉选 | GUI 未执行：当前 CUA 接口未提供独立鼠标移动或按住修饰键点击操作；对应 Agg 自动化检查通过，但不等同真实 GUI 验收 |

CUA 的 AX 复选框动作可能只改变 Qt 工具栏按钮勾选外观，验证工具栏实际行为使用坐标点击。双击使用连续两次实际点击确认，未将无效果的 clickCount 调用记为通过。

## Windows

未在 Windows 实机执行。实现不引入新依赖、平台专属字体路径或窗口 API；README 提供启动方式及中文字体、100%/150%/200% 显示缩放验收清单。macOS/Agg 结果不能证明 Windows 实机通过。

## 评审范围与收尾状态

基线提交：`1089e2aa867a6d35bb04a030684318f4b5ca6d02`。待审提交在独立评审记录中固定，并使用与该基线的 merge-base。本轮初始工作区仅存在上一轮创建的 OpenSpec 未跟踪方案，无其他用户代码修改。

代码和自动化验证已就绪；剩余真实 GUI 场景未全部完成前，不宣布 OpenSpec change 全部验收通过或允许归档。本次不自动归档。

## 独立评审与修复

初审范围：`1089e2aa867a6d35bb04a030684318f4b5ca6d02..2042eacb5d3de518a418967804321353e83189d9`，独立 Reviewer 未参与实现，读取全部规格并重跑 60 项测试、benchmark、OpenSpec，均退出 0。

- Critical：无。
- Important 代码问题：tooltip 新增 zorder=10 高于图例默认 5，但事件仍优先命中图例，重叠拖动目标与可见层级不一致。实现 Agent 独立复现双方同时命中且只开始拖图例，确认成立。
- 修复：tooltip 改为 zorder=4，位于曲线/散点之上、图例之下，保留既有事件优先级。新增重叠回归先在旧代码失败（10 不小于 5），修复后通过。重新运行完整 61 项测试、benchmark、OpenSpec 及 diff 检查，全部退出 0。
- Minor：无。
- Important 未完成验收：2.3 中的部分真实 GUI 场景未执行，属于验证缺口，不能以 Agg 代替，也未视作解决。任务 3.3 因该门槛仍未完成。
- 本机额外中文渲染检查通过：DejaVu Sans + Arial Unicode MS，中文标题及负数渲染无缺字警告；不等同 Windows 实测。

修复后独立复查的固定提交和结论见后续记录。
