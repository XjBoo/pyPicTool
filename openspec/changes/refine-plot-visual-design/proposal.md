## Why

当前六面板绘图使用高饱和红蓝点、密集虚线网格和较重边框，视觉层级不足；部分系列的连线与散点颜色不一致。需要提升长时间查看与多图对比的可读性，同时保留已有交互并支持后续 Windows 使用。

## What Changes

- 采用浅灰画布、白色绘图区、轻量网格与边框，统一标题、坐标轴、图例和 tooltip 的文字层级及留白。
- 演示数据采用协调的蓝橙色，曲线、散点和图例对应一致；保留调用者显式指定的颜色与透明度。
- 优化六面板及单面板布局，保留图例拖动、tooltip 拖动和双击放大后的布局恢复。
- 使用 Matplotlib 自带字体及 Windows 中文字体回退，不引入平台专属路径、新 GUI 框架或外部字体下载。
- 固定随机种子生成前后对比图，执行已有交互回归并记录 QtAgg 与 Windows 验证边界。

## Capabilities

### New Capabilities

- `plot-visual-presentation`: 统一绘图视觉、数据颜色对应、布局和跨平台字体策略。

### Modified Capabilities

无。现有三个 cursor 规格保持原有行为契约。

## Impact

涉及 `interactive_plotting/core.py` 的 artist 样式与布局、`interactive_plotting/demo.py` 的演示配色、可能新增内部样式模块、测试与 README。保持公开 API、数据语义、事件路由、6 px 命中半径及 QtAgg/PySide6 技术栈不变。不增加主题切换、数据处理、平滑或重采样功能。验证以 AGENTS.md 和实际项目 unittest 为准；配置上下文中的 silx/pytest 已与现状不符。
