## Why

左键点击数据点会翻转默认游标的 locked 状态，而锁定游标忽略一切键盘移动（`core.py` 的 `DataCursor.on_key` 直接 return），导致"点击锚定一个点之后按方向键逐帧移动"这一核心查看流程不可用。交互模型中不存在"钉在原地且可键盘微调"的状态；此外 matplotlib 默认键位把 Left/Right/Home/Backspace 绑定到视图导航，pan/zoom 之后按这些键还会连带跳动或重置坐标系。

## What Changes

- Left/Right/Home/End 改为移动"当前选中"的游标，**无论其是否锁定**；锁定语义收窄为"忽略鼠标 hover 跟随"，不再吞掉键盘。
- 被键盘移动的选中游标若持有图上唯一 tooltip，tooltip 跟随游标移动并刷新 Frame/Value 文本（取代现契约"键盘移动不把 tooltip 拖离点击点"中针对该游标的部分；hover 仍不得拖动 tooltip）。
- 创建交互绘图时清理 matplotlib 默认键位冲突：从 `keymap.back` 移除 `left`/`backspace`，从 `keymap.forward` 移除 `right`，从 `keymap.home` 移除 `home`，避免 toolbar 视图导航与游标导航叠加触发。
- 同步更新 README 交互契约与自动化测试。

## Capabilities

### New Capabilities

- `cursor-keyboard-navigation`: 选中游标的键盘移动（方向键/Home/End）、锁定语义与键盘的关系、tooltip 对键盘移动的跟随行为、与 matplotlib 默认键位的隔离。

### Modified Capabilities

（`openspec/specs/` 目前为空，无既有 capability 需要修改。）

## Impact

- `interactive_plotting/core.py`：`DataCursor.on_key` 的锁定守卫、`_update_cursor_visuals` 的 tooltip 刷新路径、`create_interactive_plot`（键位清理的安装/恢复位置）。
- `README.md`：Interaction 一节的锁定与键盘移动契约。
- `tests/test_public_api.py`：键盘移动相关用例需覆盖"点击锁定后方向键可移动"与"tooltip 跟随"；既有 `test_double_click_preserves_the_selected_controller_for_keyboard_input` 必须保持通过。
- 运行时影响：键位清理写入 `plt.rcParams` 属进程级全局状态，多 figure 场景下的行为需在 design.md 明确。
