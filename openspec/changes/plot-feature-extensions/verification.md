# plot-feature-extensions 正式验证记录

本报告属于补录后 apply 阶段；早期实现及工作树审查记录保留在 `docs/plot-features/verification.md`，不作为本轮正式批准依据。

## 需求与实现、验证对应

| 任务 / 规格 | 实现位置 | 本轮核对证据 |
| --- | --- | --- |
| 1.1 公开规格与生命周期 | api.py 的 build_figure、FigureBuilder；model.py 的公开规格 | test_public_spec_validation_before_window_allocation、test_theme_title_and_public_spec_round_trip、test_invalid_falsy_title_style_is_rejected；test_figure_interface 中冻结、独立窗口及失败清理测试 |
| 1.2 双轴 | core.py 的面板组、最近屏幕点分发、AxesLayoutManager | test_dual_axes_click_hover_keyboard_and_layout、test_dual_axis_removal_and_gap_selection |
| 1.3 回调及枚举 | api.py 的 _enum_values、core.py 的 _apply_enum 和 _update_cursor_visuals | 原始索引/枚举/非法返回回退测试；新增 test_enum_clear_unmapped_values_and_callback_exception 验证异常、无悬停调用及清空枚举 |
| 1.4 主题、标题、图例 | style.py；model.py 的 SuptitleStyle；core.py 构建 | 主题隔离/三行标题布局测试与 examples/plot_features.py；桌面验证见下文 |
| 1.5 整线模式 | PlotSession 与 FigureDispatcher；qt_toolbar.py | 整线/缺口命中、轴内 L 键比例保持测试；新增 test_mode_blank_click_and_escape_preserve_pins_and_layout；Qt 探针新增 pan/zoom→选线退出导航及焦点检查 |
| 1.6 删除与范围 | PlotSession.remove_series、DataCursor.remove_series | 删除散点/双轴/游标保留测试；新增 test_handles_other_panels_disconnect_and_foreign_session 验证跨会话拒绝、断开、同名身份与其他面板视图 |
| 1.7 图层及生命周期 | InteractionLayer、OverlayLegend、状态恢复 | 实际 draw 顺序和重新挂载/删除测试；新增 test_hidden_dual_tooltip_not_drawn_and_export_remains_valid |
| 1.8 文档 | README、examples/plot_features.py、docs/plot-features | 与本 change 的七项原始需求及模式行为核对；历史记录保留明确补录说明 |

本轮发现并修正 `suptitle_style` 的 falsey 非法输入被默认值掩盖：现在仅 None 表示默认，False/0/空字符串/空容器均拒绝。回归在修复前确认未在窗口分配前拒绝，修复后通过。

## 本轮针对性验证

`MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest tests.test_plot_extensions tests.test_figure_interface tests.test_visual_presentation tests.test_qt_toolbar -v`：退出码 0，32 项通过，4.118 秒。

## 待审范围与完整验证

基线与 merge-base：`91c1b4bf49ae1880ca47cd1bc7a2e2670e2dd971`。
待审实现：`f0b8e69bd44a38b0270a7b78b23ac1010658d0da`，分支 `codex/plot-feature-extensions`。
提交后工作树为空；后续仅更新本报告与任务勾选，运行时代码/测试无未提交修改。

- 完整 unittest 命令：退出码 0，89 项通过，10.983 秒。
- Hover benchmark 命令：退出码 0，1,000/10,000 点每序列，中位数 0.004777/0.011123 秒，无阈值，非性能指标验收。
- `openspec validate --changes`：退出码 0，1 passed / 0 failed。
- `openspec validate plot-feature-extensions --strict`：退出码 0，valid。
- 扩展示例 Agg 导出：退出码 0，输出 `/tmp/pypic-apply-preview.png`。

## 本轮真实桌面验证（2026-09-08 至 2026-09-09）

`venv/bin/python interactive_plot.py`：成功启动，工具栏展开、整线按钮、图例条目选线、Backspace 删除、Esc 退出已实际操作；关闭后进程退出码 0。
`MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.plot_features`：窗口标题及主题正常；实际点击压力点后 Right 键显示 Frame 2 / Value 110.00，右侧 tooltip 可拖动；左轴自定义提示显示时间 2 s / 温度 23 °C；L 选中高温线后 Backspace 删除，左轴收缩至约 20..27，右轴保留约 100..140，左侧提示保留。
2026-09-09 通过同一扩展示例的只读事件日志探针再次操作原生 Qt 窗口：背景双击成功放大整个双轴面板，日志明确记录 `double True / max True`；Esc 恢复两个面板，随后合并图例拖动成功。探针仅记录实际鼠标事件，没有合成事件。前一日双击未成功触发的现象本次未复现，原因未确定；不以自动化测试替代本次桌面证据。窗口已正常关闭。

## 覆盖缺口

类型检查：未执行，mypy 未安装且无已采用命令。Lint/格式：未执行，Ruff 未安装且无已采用命令。构建：缺少 build-system 和构建命令。独立 E2E：缺少套件，Agg 与 Qt offscreen 不等于完整 E2E。安全扫描：无 secret scan、SAST、依赖漏洞扫描配置。Windows/多 DPI：尚未实际验证。上述缺口不计为通过。


## 独立审查与处置（2026-09-09）

未参与实现的独立 Reviewer `resume_review` 只读审查上述固定范围，完整读取 proposal、design、六份增量规格、tasks 与验证背景，核对实现、测试、README 和示例。范围外仅本报告与任务勾选更新，未遗漏运行时代码或测试改动。

稳定清单：0 Critical、0 Important、0 Minor。没有待确认、拒绝或修复的问题，因而没有修复后的复审范围。

Reviewer 本轮实际执行以下命令，均退出码 0：

- `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`：89 项通过，11.174 秒。
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py`：完成冒烟；1,000/10,000 点中位数约 0.004667/0.011428 秒，无性能阈值，不代表性能指标达标。
- `openspec validate --changes`：1 passed。

Reviewer 未重复执行真实 GUI；该条件由主 Agent 上述原生操作证据补齐。类型、Lint、构建、独立 E2E、安全扫描及平台缺口与上文一致，均未计为通过。

## Apply 结论

16 项任务已核对完成，必需自动化与适用 Qt 手工场景已执行，无未解决 Critical 或 Important。本次 apply 完成；仅提交验证报告和任务状态作为收尾记录，未执行主规格同步、归档或合并。独立审查覆盖的实现提交保持为 `f0b8e69bd44a38b0270a7b78b23ac1010658d0da`，后续记录提交不改变运行时代码或测试。
