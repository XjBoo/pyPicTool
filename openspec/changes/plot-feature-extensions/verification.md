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

待固定提交后填写。本报告当前不作完成/归档结论。

## 覆盖缺口

类型检查：未执行，mypy 未安装且无已采用命令。Lint/格式：未执行，Ruff 未安装且无已采用命令。构建：缺少 build-system 和构建命令。独立 E2E：缺少套件，Agg 与 Qt offscreen 不等于完整 E2E。安全扫描：无 secret scan、SAST、依赖漏洞扫描配置。Windows/多 DPI：尚未实际验证。上述缺口不计为通过。
