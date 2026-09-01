## 1. 悬停阈值与系列独立

- [ ] 1.1 将 `_CLICK_HIT_RADIUS_PIXELS` 重命名为 `_HIT_RADIUS_PIXELS = 6.0`；`on_hover` 在 `_nearest_point_from_px` 返回后判定 `distance_squared <= _HIT_RADIUS_PIXELS**2`，超阈值直接走"无命中"分支；点击命中判定同步使用新常量（D1）。验证：新增用例"鼠标距最近点约 8px 时无高亮、无游标移动"与"距数据点 0px 时命中"通过；既有点击用例全部通过
- [ ] 1.2 `on_hover` 命中时仅 `_select_cursor(命中系列游标)` 并在该游标未锁定时移动到命中点，删除同步循环（D2）。验证：`test_hover_synchronizes_each_series_by_nearest_frame_value` 重写为独立性断言（其他系列游标不动且不可见）后通过；新增"多系列近点取屏幕最近者"用例通过

## 2. 瞬态可见性

- [ ] 2.1 `Cursor.__init__` 创建标记后 `set_visible(False)`；`on_hover` 命中且未锁定时显示该游标；新增 `_hide_transient_highlights()`（隐藏所有未锁定游标），在悬停无命中与 `inaxes` 不匹配时调用（D2/D3）。验证：新增用例"初始状态无任何游标可见""鼠标移开后未锁定游标隐藏""锁定游标不受移开影响"通过
- [ ] 2.2 `CursorState` 增加 `marker_visible` 字段，`capture_state`/`restore_state` 保存与恢复标记可见性（D3）。验证：既有双击还原用例（`test_double_click_maximizes_without_applying_the_first_single_click`、`test_double_click_restores_the_previous_figure_tooltip`、`test_double_click_preserves_the_selected_controller_for_keyboard_input`）全部通过

## 3. 删除同步机制

- [ ] 3.1 删除 `__init__` 的同步表构建块、`_sync_frames_list`/`_sync_indices_list` 字段与 `_nearest_index_for_frame` 方法；`on_key` 同步循环替换为仅移动 `_click_selected` 游标（D4）。验证：`test_keyboard_keeps_targeting_the_clicked_cursor_while_hovering` 中蓝线断言改为保持原位后通过；新增"键盘移动不移动其他系列游标"用例通过
- [ ] 3.2 核对既有测试对旧契约的依赖（D5）：`test_locked_selected_cursor_freezes...` 系（现为 `test_keyboard_moves_the_selected_cursor_regardless_of_lock`）、`test_ordinary_clicks_keep_default_cursor_owners_fixed`、`test_unsigned_frame_distance_does_not_overflow`、`test_series_validation_and_missing_values_are_publicly_enforced` 等逐例核对语义后更新断言。验证：`MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` 全部通过，无跳过或弱化的新契约断言

## 4. 文档与整体验证

- [ ] 4.1 改写 README Interaction 一节：悬停契约改为"贴近数据点（共享命中阈值）才触发单系列高亮、移开即隐藏、初始全部隐藏"，删除同步描述（Data and synchronization rules 一节的同步规则同步删除）。验证：通读 README 与两份 spec（cursor-hover-highlight、cursor-keyboard-navigation）无矛盾表述
- [ ] 4.2 全量自动化检查无回归。验证：`MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` 全部通过；`PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` 可运行且无异常；`openspec validate --changes` 通过
- [ ] 4.3 手动验证 QtAgg 路径（不进自动测试）：`venv/bin/python interactive_plot.py` 打开后初始无高亮；鼠标在空白处移动无高亮；贴近某条线的点时仅该线出现高亮，另一条线无反应；点击锚定后锁定游标持续显示；方向键只移动点击锚定的线。验证：窗口行为逐条符合 spec 场景
