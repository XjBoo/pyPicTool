# 实施验证记录

基线：76307de57d998f9319ed652ddb05355ce1f11e7d。实施前仅有本 change 的未跟踪规划文档，无已有代码修改。
Qt：PySide6 6.11.2。其余环境及物理/逻辑画布尺寸见 baseline-render.json 的 environment。

基线命令（均退出码 0）：
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py --events 60 --repeats 3 --include-render`
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py --events 60 --repeats 3`

对应 baseline-render.json、baseline-events.json。事件 p95 来自各事件处理时长，批次总时间另列；此处 Agg 不测真实 Qt 显示延迟。

## 首次实现自动化结果（修复前）

- `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`：98 tests，退出码 0（12.396 秒）。包括新增 8 项距离与画面回归，以及原有点击、键盘、钉选、双轴、删除和窗口生命周期测试。
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py`：退出码 0，结果见 benchmark-smoke.json；只代表无渲染事件处理冒烟。
- `openspec validate --changes`：1 passed，退出码 0。
- `git diff --check`：退出码 0。
- 类型检查：覆盖缺口（mypy 未安装，无已采用命令）。
- Lint/格式：覆盖缺口（Ruff 未安装，无已采用命令）。
- 构建：覆盖缺口（无 build-system/已采用命令）。
- E2E：覆盖缺口（无独立 E2E 套件；真实 Qt 操作为人工/桌面操作验证）。
- 安全扫描：覆盖缺口（无已配置扫描命令）。

## 首次实现的同机包含绘制对比（修复前，历史记录）

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

## 最终代码验证（642a114）

- 单元与交互检查：100 tests，11.307 秒，退出码 0。新增真实 Qt offscreen 排队刷新取消/合并测试以及 Figure 前景内容回归。
- 默认 hover benchmark：退出码 0，最新结果覆盖写入 benchmark-smoke.json。
- OpenSpec 结构校验：1 passed，退出码 0；git diff --check 退出码 0。
- 独立复审：10 项定向测试通过，退出码 0；两个 Important 均关闭，无新增 Critical/Important/确定 Minor。详见 review.md。
- 类型、Lint/格式、构建、独立 E2E、安全扫描仍为上文列明的覆盖缺口，没有变为通过。

性能对比最终单独运行，避免与测试进程竞争：`PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py --events 60 --repeats 3 --include-render`，退出码 0。

| 每系列点数 | 最终单事件中位数 | 最终 p95 | 每轮完整 draw |
| --- | --- | --- | --- |
| 1,000 | 8.020 ms | 8.591 ms | [0, 0, 0] |
| 10,000 | 7.971 ms | 8.302 ms | [0, 0, 0] |

## 最终 Qt 记录

- qt-dual-final.json：实际倍率 2，物理尺寸 1200×1420、逻辑尺寸 600×710。已观察左轴活动点与右轴悬停共存、跨面板清除旧预览、右轴键盘定位、双轴放大及恢复。
- qt-dual-post-fix.json：在审查修复后的代码上复查左轴选中、右轴悬停、双轴放大/恢复、跨面板预览、窗口尺寸变化、正常关闭，进程退出码 0；倍率 2，最终物理尺寸 1288×1464、逻辑尺寸 644×732。
- 原始 Qt 数值是输入到下一次 paint 的代理，可能混入其他 UI 操作；此处不据其计算纯悬停耗时。用户的“明显改善”与独立 Agg 前后对比共同支持体验改善结论。
- 真实倍率 1 和跨屏切换没有可用验证环境，明确列为硬件覆盖缺口；倍率 1/2 和运行时倍率切换已用自动化测试验证。
- 用户对真实窗口中 Shift＋点击多个点后钉选点及提示框是否正常、无残影的确认是：“表现正常的”。该人工确认补齐任务 4.2；结合已完成的独立复审与修复后检查，任务 5.2 同时完成。
- qt-pin-check.json 已解析验证：实际设备倍率 2，逻辑尺寸 600×710、物理尺寸 1200×1420，233 个鼠标移动事件。原始时序仅为辅助观测，钉选验收依据为用户明确反馈。

## 验收结论

14/14 项任务完成，无未解决 Critical 或 Important。最终实现代码仍为独立复审覆盖的 642a114；后续仅追加证据和任务状态，没有修改代码，因此本次不重复运行已通过的 100 项测试与性能检查。上述硬件和工具覆盖缺口保持如实记录。本 change 尚未归档。
