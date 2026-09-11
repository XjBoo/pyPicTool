# 实施验证记录

基线：76307de57d998f9319ed652ddb05355ce1f11e7d。实施前仅有本 change 的未跟踪规划文档，无已有代码修改。
Qt：PySide6 6.11.2。其余环境及物理/逻辑画布尺寸见 baseline-render.json 的 environment。

基线命令（均退出码 0）：
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py --events 60 --repeats 3 --include-render`
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py --events 60 --repeats 3`

对应 baseline-render.json、baseline-events.json。事件 p95 来自各事件处理时长，批次总时间另列；此处 Agg 不测真实 Qt 显示延迟。

## 当前自动化结果

- `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`：98 tests，退出码 0（12.396 秒）。包括新增 8 项距离与画面回归，以及原有点击、键盘、钉选、双轴、删除和窗口生命周期测试。
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py`：退出码 0，结果见 benchmark-smoke.json；只代表无渲染事件处理冒烟。
- `openspec validate --changes`：1 passed，退出码 0。
- `git diff --check`：退出码 0。
- 类型检查：覆盖缺口（mypy 未安装，无已采用命令）。
- Lint/格式：覆盖缺口（Ruff 未安装，无已采用命令）。
- 构建：覆盖缺口（无 build-system/已采用命令）。
- E2E：覆盖缺口（无独立 E2E 套件；真实 Qt 操作为人工/桌面操作验证）。
- 安全扫描：覆盖缺口（无已配置扫描命令）。

## 同机包含绘制的对比

相同 benchmark 输入，60 事件 × 3 次，6 面板。after-render.json 与 baseline-render.json 对比：

| 每系列点数 | 基线单事件中位数 / p95 | 优化后中位数 / p95 | 每次完整 draw 次数 |
| --- | --- | --- | --- |
| 1,000 | 50.984 / 58.833 ms | 8.050 / 8.378 ms | 48 → 0 |
| 10,000 | 69.873 / 71.250 ms | 8.181 / 8.923 ms | 55 → 0 |

不同命中半径改变了偏移事件是否命中，因此同时报告实际绘制次数；这不是纯绘制内核微基准。最新悬停反馈包含的渲染工作明显减少，但不能推导成通用帧率保证或物理显示延迟。

## 真实 Qt 操作记录

直接执行 `venv/bin/python interactive_plot.py` 在沙箱内因系统 GUI 服务不可用退出 134；随后在获准的 GUI 环境运行 `MPLCONFIGDIR=.mplconfig venv/bin/python interactive_plot.py`，窗口成功打开并正常关闭（退出码 0）。

另运行 `PYTHONPATH=. MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/observe_hover_qt.py`，用真实鼠标操作收集时序，不注入模拟事件。用户对慢速靠近、快速沿线/跨点移动的反馈为“明显改善”。

桌面操作已观察到：点击点出现 tooltip；框选缩放改变范围，Home 恢复；平移后恢复；连续双击空白处放大子图，Escape 恢复；窗口拖动边界后尺寸改变且布局正确；整线模式选中蓝色曲线后 Backspace 删除，旧曲线消失且图例更新；Escape 退出；tooltip 与图例拖动后位置正确、无旧位置残影；保存图像包含当前 tooltip、图例及剩余曲线（qt-export.png，已查看）；关闭后重新打开双轴窗口。

qt-observation.json 为首轮原始采集：2,347 个鼠标移动事件，710 条与后续 paint 关联。该版本 environment 记录的是显示前默认倍率/尺寸，不能用于证明实际屏幕倍率；paint 可能由后续其他 UI 操作触发，因此不将其中的中位数作为纯悬停延迟结论。观察脚本已改为记录每次事件倍率及窗口关闭时的真实尺寸，双轴采集待补。

多屏倍率切换仅有自动化模拟覆盖，当前没有进行真实跨屏验证；作为硬件覆盖缺口报告，不冒充通过。
