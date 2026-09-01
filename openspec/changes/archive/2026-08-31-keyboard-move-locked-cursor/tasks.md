## 1. 键盘移动选中游标（含锁定）

- [x] 1.1 在 `DataCursor.on_key` 中移除 `if cursor.locked: return` 守卫；对选中游标且其 tooltip 可见时以 `show_tooltip=True` 刷新，使 tooltip 跟随键盘移动（D1/D2）。验证：`MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest tests.test_public_api -v`，新增用例"左键点击锁定后按 Right，游标移至下一有效点且 tooltip 锚点与 Frame/Value 文本刷新"通过
- [x] 1.2 补充跨系列同步用例：键盘移动选中游标时，未锁定游标按帧同步、其他锁定游标保持原位、未选中游标时按键不移动。验证：同一测试命令，对应 spec 场景逐条通过
- [x] 1.3 确认既有交互不回归：`test_double_click_preserves_the_selected_controller_for_keyboard_input`、悬停不拖动 tooltip、hover 不移动锁定游标等现有用例全部通过

## 2. 键盘导航与默认视图键位隔离

- [x] 2.1 在 `core.py` 实现会话级引用计数的键位清理（D3）：首个 session 创建时快照 `keymap.back`/`keymap.forward`/`keymap.home` 并移除 `left`/`backspace`/`right`/`home`（成员检查保证幂等），活跃计数归零时按快照整体赋值还原；接入 `create_interactive_plot` 与 `PlotSession.disconnect`。验证：新增 rcParams 快照断言用例（清理生效、还原精确、连续创建/断开、乱序断开、键已缺失时幂等）通过
- [x] 2.2 手动验证 QtAgg 路径（不进自动测试）：`venv/bin/python interactive_plot.py` 中 pan/zoom 产生视图历史后按 Left/Right/Home，仅游标移动、坐标系不跳动。验证：用户在 QtAgg 窗口确认点击后方向键可逐帧移动、tooltip 跟随，且 pan/zoom 后按键坐标系不跳动

## 3. 文档契约同步

- [x] 3.1 改写 README Interaction 一节：锁定游标契约改为"忽略鼠标悬停跟随，选中时可被键盘移动"；键盘移动条目去掉 unlocked 限定，新增 tooltip 跟随与键位隔离说明。验证：通读 README 与 specs/cursor-keyboard-navigation 无矛盾表述

## 4. 整体验证

- [x] 4.1 全量自动化检查无回归。验证：`MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` 全部通过；`PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` 可运行且无异常

## 5. 键盘目标限定为点击选中的游标（用户在手动验证后追加的需求）

- [x] 5.1 在 `DataCursor` 中新增 `_click_selected`（仅左键点击路径赋值），`on_key` 移动目标从 `_selected` 改为 `_click_selected`；删除/清空/断开路径清理该引用，`StateSnapshot` 增加 `click_selected` 字段使双击还原撤销单击锚定。验证：新增用例"悬停选中不启用键盘""键盘目标不随悬停切换"通过，全量测试通过
- [x] 5.2 同步 spec/design/README 契约表述。验证：README 与 spec 中键盘移动均限定为"左键点击选中的游标"，无矛盾表述
