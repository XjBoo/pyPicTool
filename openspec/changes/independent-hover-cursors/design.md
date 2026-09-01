## Context

悬停路径现状（见 proposal.md - Why）：`DataCursor.on_hover` 调 `_nearest_point_from_px` 做无阈值 argmin，随后把所有未锁定游标同步到目标帧（`_nearest_index_for_frame`）；点击命中半径是独立的 `_CLICK_HIT_RADIUS_PIXELS = 10.0`。游标标记（`highlight`）自创建起永远可见。同步表在 `__init__` 构建（`_sync_frames_list` / `_sync_indices_list`，`np.minimum.at` 处理重复帧取最小原索引）。

## Goals / Non-Goals

- Goals：阈值化悬停、系列独立、瞬态可见性、删除同步机制、保持既有键盘/点击/tooltip/双击还原行为不变。
- Non-Goals：不引入悬停节流或性能优化（现有 `_ensure_disp_cache` 缓存机制不动）；不改公共 API；不做"临时同步"模式（用户已确认接受同步对比损失）；不处理多面板间的交互（面板隔离已由 dispatcher 的 `inaxes` 路由保证）。

## Decisions

### D1：悬停与点击共用一个命中阈值常量

`_CLICK_HIT_RADIUS_PIXELS = 10.0` 重命名为 `_HIT_RADIUS_PIXELS = 6.0`，悬停与点击同一判定：`distance_squared <= _HIT_RADIUS_PIXELS**2`。理由：两个阈值不一致会出现"点得中却没高亮"或"高亮了却点不中"的割裂；6px 约等于鼠标光标热点与标记半径之和的一半，满足"几乎重合"的观感。备选：悬停 6px + 点击 10px（宽容操作）——被否决，因为割裂感比操作精度损失更影响体验；用户明确选择按推荐共用。

### D2：悬停只作用于命中系列的游标

`on_hover` 保留 `_nearest_point_from_px` 的跨系列 argmin（用于在多系列都命中时取屏幕距离最近者），但判定加阈值；命中时只调用 `_select_cursor(命中系列游标)` 并在未锁定时 `_update_cursor_visuals(该游标, 命中点)`，删除同步循环。未命中（超阈值或不在本 axes）时调用 `_hide_transient_highlights()`：隐藏所有未锁定游标的 `highlight`（锁定游标不动）。金色高亮跟随命中系列切换，`_selected` 语义不变。

### D3：瞬态可见性的状态规则

游标标记可见当且仅当：`cursor.locked` 为真（点击锚定/Shift+左键新增持久可见），或该游标正被悬停命中（未锁定，当前高亮）。实现为三处赋值：`Cursor.__init__` 创建后 `set_visible(False)`；`on_hover` 命中且未锁定时 `set_visible(True)`；`_hide_transient_highlights()` 中对未锁定游标 `set_visible(False)`。`CursorState` 增加 `marker_visible` 字段，`capture_state`/`restore_state` 保存与恢复可见性，保证双击还原、`clear_extra_cursors` 等快照路径不破坏瞬态规则（恢复后重新按 locked 规则计算亦可，但显式快照更直接且与既有快照字段风格一致）。

### D4：删除同步机制

`__init__` 中 `valid_frames`/`sync_indices` 构建块、`_sync_frames_list`/`_sync_indices_list` 字段、`_nearest_index_for_frame` 方法整体删除；`on_key` 的同步循环替换为只移动 `_click_selected` 游标。`_valid_indices_list` 保留（键盘按有效点步进仍需要）。删除后 `on_hover` 与 `on_key` 都是 O(1) 游标操作，唯一剩余的 O(N) 是 `_nearest_point_from_px` 本身（有 disp 缓存）。

### D5：测试基线的重写策略

`test_hover_synchronizes_each_series_by_nearest_frame_value` 反转为独立性断言（其他系列游标不动且不可见）；`test_keyboard_keeps_targeting_the_clicked_cursor_while_hovering` 中蓝线跟随断言改为保持原位；`test_unsigned_frame_distance_does_not_overflow` 的同步断言改为仅红线命中（该用例的 uint64 溢出回归点在 argmin 距离计算，不受同步删除影响）。既有用例中所有 `send_mouse_event(..., 数据点坐标)` 都精确落在数据点上（距离 0 < 6px），阈值化后依旧命中；唯一风险点是用例若依赖"悬停任意位置即吸附"将被暴露为失败，届时逐例核对语义后再改。

## Risks / Trade-offs

- 6px 阈值较紧，密集数据点上不易瞄准——用户明确选择"几乎重合"的观感，接受此代价；常量单一，后续可一行调整。
- 可发现性下降：新用户可能不知道要贴近点才有高亮。缓解：tooltip/点击行为不变，锁定游标持久可见作为操作痕迹。
- 大量既有测试依赖"永远可见的游标"，本变更会集中暴露；按 D5 逐例核对，避免为凑通过而弱化新契约。
