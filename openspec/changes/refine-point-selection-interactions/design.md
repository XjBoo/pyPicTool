## Context

现有 `DataCursor` 为每个系列保留一个默认游标，同一对 highlight/tooltip 同时承担悬停预览、普通点击选中和锁定。`locked` 既决定方形外观，又禁止悬停移动；图级事件分发又在每次点击后隐藏其他 tooltip。这使三类行为无法同时满足。

现有 Shift+左键已能创建额外游标，Delete/Backspace 可删除当前额外游标，Escape 可清除额外游标。设计将保留这些操作入口，但重新定义其状态语义。

## Goals / Non-Goals

**Goals:**

- 使 hover preview、active selection 和 pinned selection 能同时存在。
- 让标记和 tooltip 的可见性由单一、可推导的状态决定。
- 保持屏幕像素命中阈值、tooltip 拖动、键盘导航和多面板分发能力。

**Non-Goals:**

- 不改变数据系列输入模型或命中距离算法。
- 不新增钉选点序列化、导出或会话间持久化。
- 不改变双击最大化、图例拖动和工具栏交互。

## Decisions

### 1. 将悬停预览与持久点对象分离

每个面板保留一个独立的 hover preview artist，它只包含标记、不包含 tooltip，可在任意系列和点之间移动。活动选中和每个钉选点各自拥有独立的 marker/tooltip 对。

不采用“继续复用每系列默认游标”，因为一个 artist 无法在保留已选中点的同时预览同系列的另一点。

### 2. 使用显式角色，不再使用 `locked` 布尔值表达多重含义

控制器明确管理：

- `hover_preview`：瞬态，没有 tooltip。
- `active_selection`：全图最多一个，普通点击不同点时替换，再次点击同一点时清除。
- `pinned_selections`：可有多个，Shift+点击时追加。
- `keyboard_target`：指向最近被点击的 active 或 pinned selection，不随 hover 变化。

这比在现有游标上继续增加 `locked`/`default`/`selected` 组合条件更易于维护和测试。

### 3. 标记只使用圆形，焦点通过尺寸和描边表达

所有点标记固定为 `o`。当前交互焦点沿用现有的增大、金色描边和加粗效果；非焦点的 pinned selection 保留系列颜色的圆形标记。这避免将形状同时解释为“已点击”和“不响应 hover”。

### 4. 图级管理器负责全局唯一活动选中，面板控制器负责本地点

普通点击由命中面板创建或更新 active selection，图级管理器同时清理之前位于任何面板的 active selection。Shift+点击只向命中面板追加 pinned selection，不运行全局 tooltip 隐藏逻辑。

不保留“每个系列一个可见默认选中”，因为它会使普通点击的全图唯一替换规则变得含糊。

### 5. 事件处理顺序保持可预测

鼠标按下按以下顺序分派：

1. 工具栏模式或已在拖动时停止点交互。
2. 图例命中优先于数据点命中。
3. tooltip 命中优先于数据点命中，用于选中键盘目标和启动拖动。
4. 双击恢复单击前快照，再切换面板最大化。
5. Shift+左键命中新增 pinned selection。
6. 普通左键命中数据点后，先按系列与数据索引查找同位置的 pinned selection；命中时移除该钉选点并结束事件。
7. 没有命中钉选点时，若命中点与 active selection 相同，清除 active selection 及 keyboard target；否则替换 active selection。

鼠标移动按以下顺序分派：

1. tooltip 拖动中只更新 tooltip 文本偏移。
2. 鼠标不在可交互面板或没有命中点时隐藏 hover preview。
3. 命中数据点时移动 hover preview；若命中点已有 active/pinned marker，隐藏 preview artist 并仅对已有 marker 应用焦点样式。

### 6. 快照恢复覆盖全部新状态

用于双击判定的状态快照必须包含 hover preview、active selection、所有 pinned selections、键盘目标以及每个 tooltip 的锚点、偏移和文本。这避免第一次单击在双击最大化后留下标记或 tooltip。

### 7. 取消操作依据精确数据点身份，不依赖 artist 命中

左键点击通过现有屏幕距离命中算法先解析为 `(series_idx, data_index)`，再与 active/pinned selection 的身份比较。这使点击加粗 marker 内的任意位置都能稳定取消，也避免将 annotation 箭头或重叠 artist 误认为取消目标。

当同一数据点同时存在 active 和 pinned selection 时，普通左键优先取消 pinned selection；再次点击才取消 active selection。tooltip 的点击优先级仍高于数据点命中，因此拖动或选择 tooltip 不会意外删除点。

## Risks / Trade-offs

- [每个钉选点增加 marker 和 annotation artist，大量钉选可能增加绘制成本] → 只在事件导致可见状态变化时调用 `draw_idle`，并在 hover benchmark 中覆盖存在钉选点的情况。
- [active/pinned 点与 hover 点重合时可能双重绘制] → 按系列和数据索引判定重合，重合时复用已有标记的焦点样式。
- [现有测试大量依赖方形和 `locked` 语义] → 先增加新状态机的行为测试，再逐类替换旧断言，保留无关的命中、双击和拖动回归覆盖。
- [多 tooltip 可能相互遮挡] → 保留每个 tooltip 独立拖动能力；本次不引入自动避让排版。

## Migration Plan

1. 用新角色状态和回归测试替换 `locked` 切换行为。
2. 将图级唯一 tooltip 清理改为只替换 active selection，保留 pinned tooltips。
3. 更新双击快照、删除、清理和会话关闭路径。
4. 运行自动化测试、hover 冒烟 benchmark 和 OpenSpec 校验，再对 QtAgg 真实鼠标交互执行手工验证。

如需回退，可整体回退该 change 的实现提交；本变更不涉及持久化数据迁移。
