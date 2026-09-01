## Why

当前悬停逻辑对每条线做无阈值 argmin，鼠标无论在图内何处（包括空白角落）都必然吸附出一个"最近点"，且所有未锁定游标被强制同步到同一帧——结果是每条线永远各有一个高亮点、多条线常常同步跳动，视觉噪音大。用户需要的是：只有鼠标几乎贴到某个点上时才出现高亮，且各条线完全独立，选中一条线的点不影响其他线。

## What Changes

- 悬停与点击共用一个像素命中阈值（约 6px，视觉上鼠标光标与数据点几乎重合）：鼠标与最近数据点的屏幕距离超过阈值时不产生任何高亮或游标移动。
- 悬停只影响鼠标所贴近的那条线的游标：该线游标（未锁定时）出现并吸附到该点、获得金色高亮；其他线的游标完全不动、不显示。
- 高亮变为瞬态：初始状态（打开图、无任何交互）所有游标隐藏；鼠标移开后未锁定的游标隐藏；仅锁定（含点击锚定、Shift+左键新增）的游标持久可见。
- 键盘移动的跨系列同步**移除**：方向键/Home/End 只移动点击锚定的那条线的游标，其他线不再跟随。
- 删除同步机制代码（`_sync_frames_list`、`_sync_indices_list`、`_nearest_index_for_frame` 等），README 交互契约与自动化测试同步改写。
- 用户已确认接受同步对比能力的损失（原本用于跨系列同帧对比，现在不需要）。

## Capabilities

### New Capabilities

- `cursor-hover-highlight`: 悬停高亮的触发阈值、各系列间的独立性、游标标记的瞬态可见性规则。

### Modified Capabilities

- `cursor-keyboard-navigation`: 移除"键盘移动的跨系列同步"需求；修改提及悬停同步的既有需求场景表述（键盘移动不再同步其他游标）。

## Impact

- `interactive_plotting/core.py`：`DataCursor.on_hover`（阈值判断、仅移动命中系列）、`on_key`（去同步循环）、`__init__`（初始隐藏、删除同步表构建）、`CursorState`/`StateSnapshot`（需记录游标标记可见性以支持双击还原）、点击命中半径常量与悬停阈值合并。
- `README.md`：Interaction 一节的悬停契约整体改写（无阈值吸附与同步描述删除）。
- `tests/test_public_api.py`：`test_hover_synchronizes_each_series_by_nearest_frame_value` 等同步类用例按独立性语义重写；新增阈值边界、初始隐藏、移开隐藏、键盘不同步用例。
- 无公共 API 变更；`PlotSession` 对外方法不变。
