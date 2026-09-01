## Context

`interactive_plotting/core.py` 中 `DataCursor.on_key` 以 `if cursor.locked: return` 吞掉所有键盘移动，锁定游标同时忽略 hover；左键点击又必然翻转出 locked 状态，因此"点击后键盘微调"不可达。matplotlib 3.10.8 的 `FigureManagerBase` 在每个 canvas 上注册 `key_press_handler`（默认键位），与 `FigureDispatcher.on_key` 并行触发且无消费机制：`left`/`backspace`→`toolbar.back()`、`right`→`toolbar.forward()`、`home`→`toolbar.home()`（无条件重置视图）。仓库 `matplotlibrc` 仅钉了 backend。已确认 pytest 事件路径（`callbacks.process` 直接分发）不经过默认 handler，键盘行为可在 Agg 测试中稳定验证。

## Goals / Non-Goals

**Goals:**

- 方向键/Home/End 对选中游标生效，锁定与否不再影响键盘路径。
- 键盘移动选中游标时其可见 tooltip 跟随并刷新数值。
- 键盘导航键与 toolbar 视图导航在会话内隔离，会话结束后默认键位还原。

**Non-Goals:**

- 不改 hover 跟随、点击锁定翻转、额外游标、双击最大化等既有交互。
- 不引入新的键盘手势或"键盘模式"状态机。
- 不处理鼠标事件与视图导航的冲突（pan/zoom 时游标逻辑本就暂停）。

## Decisions

### D1：键盘目标 = 点击选中，锁定不设限

`DataCursor.on_key` 删除 `if cursor.locked: return`，移动目标从"当前选中"（`_selected`，悬停也会改变）收窄为 `_click_selected`——仅在左键点击路径（数据点点击、Shift+左键新增、点击 tooltip 拖拽）赋值，悬停只改 `_selected`（金色高亮）不改键盘目标。删除/清空/断开路径在目标游标被移除时清空 `_click_selected`；`StateSnapshot` 增加 `click_selected` 字段使双击还原能精确撤销单击的键盘锚定。Delete/Backspace 仍作用于 `_selected`（额外游标本就只能经点击选中，行为等价不变）。备选方案（点击不翻转锁定、引入键盘微调模式）在探索阶段已否决：本方案改动最小且语义自洽——键盘只服务用户显式点击锚定的点。同步循环中 `if candidate.locked: continue` 保持不变，非选中的锁定游标依旧静止。

### D2：tooltip 跟随条件为"选中游标且其 tooltip 可见"

`on_key` 对选中游标调用 `_update_cursor_visuals(..., show_tooltip=True)`，条件是 `cursor.tooltip.get_visible()` 为真（未点击过则 tooltip 隐藏，保持隐藏；点击后 tooltip 是图上唯一可见的，随选中游标移动）。`_update_cursor_visuals` 已有的锚点/文本刷新逻辑复用，`restore_state` 的 tooltip 快照字段无需改动。假设：探索阶段提议"tooltip 跟随并刷新"已随"按方案 A 来"被接受。

### D3：键位清理采用会话级引用计数

新增模块级辅助（`core.py` 内）：首个 `PlotSession` 创建时快照 `rcParams["keymap.back"/"keymap.forward"/"keymap.home"]` 并移除冲突键（`left`/`backspace`、`right`、`home`），活跃 session 计数归零时按快照还原（整体赋值拷贝，不原地改共享 list）。移除前检查成员，兼容用户自定义 rcParams 已删键的情况。备选：模块导入时一次性清理（不可恢复，违反"会话结束不残留"）、每 session 独立快照恢复（乱序断开时后建 session 的还原值已被先断者污染）。计数方案下乱序断开安全：任一活跃 session 存在即保持清理态。

### D4：事件处理顺序

键盘：Qt `keyPressEvent` → `FigureCanvasBase.key_press_event` → callbacks 按注册顺序执行——`FigureManagerBase` 的 `key_press_handler` 先（figure 创建时注册），`FigureDispatcher.on_key` 后（`create_interactive_plot` 尾部注册）。默认 handler 每次按键实时读 rcParams，故会话内任意时刻清理均有效，注册顺序无需调整；清理后对这些键 `key_press_handler` 退化为 no-op。

鼠标（tooltip 边界）：`motion_notify_event` → `on_hover` 永不修改 tooltip（锚点/文本/可见性）；`button_press_event` → `on_press` 命中 tooltip 则进入拖拽，否则 `on_click` 显示唯一 tooltip；`key_press_event` → `on_key` 移动选中游标并按 D2 刷新其 tooltip。此顺序本 change 不改动，仅作为行为边界固化进测试。

### D5：README 与测试同步

README Interaction 一节改写两处契约：锁定游标"忽略鼠标与键盘移动"改为"忽略鼠标悬停跟随，选中时可被键盘移动"；键盘移动条目去掉"unlocked"限定并新增 tooltip 跟随描述。测试沿用 Agg + `callbacks.process` 路径新增用例；键位清理用 rcParams 快照断言（事件路径测不到默认 handler）。

## Risks / Trade-offs

- [rcParams 是进程级全局，会话存续期间同进程其他 figure（含非交互图）也失去这些默认键] → 记录为已知代价；清理范围仅 3 个 keymap 列表中的 4 个键，最后一个 session 断开即还原。
- [用户自定义 matplotlibrc 已移除待清理键] → remove 前做成员检查，幂等。
- [把锁定理解为"完全冻结"的既有用户被键盘移动意外] → 明确契约变更（见 proposal），gold 边 + 方形标记的选中态视觉提示保留；键盘移动需先选中再按键，非误触路径。
- [keyboard 移动与 drag/toolbar 守卫的交互] → `on_key` 既有守卫（dragging、toolbar active）保持，不新增路径。

## Migration Plan

库内行为变更，无部署步骤；回滚等价于 revert 对应提交。提交按 tasks.md 小步拆分（行为、键位清理、文档）。

## Open Questions

无。
