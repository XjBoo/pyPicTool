# cursor-keyboard-navigation Specification

## Purpose

定义选中游标的键盘导航契约：方向键与 Home/End 移动当前选中的游标（不区分锁定状态）、tooltip 对键盘移动的跟随行为、锁定语义与键盘的关系，以及与 matplotlib 默认视图导航键位的隔离。

## Requirements

### Requirement: 键盘移动点击选中的游标

系统 SHALL 仅对最近被鼠标左键点击选中的游标（数据点左键点击、Shift+左键新增、或左键点击其 tooltip）响应 Left/Right/Home/End：方向键移动到本系列的上一/下一有效数据点，Home/End 跳转到第一个/最后一个有效数据点。该移动 SHALL 不受游标锁定状态限制。仅经悬停选中的游标 SHALL 不响应这些按键；悬停改变当前选中（金色高亮）游标 SHALL 不改变键盘移动的目标。未发生任何左键点击时，这些按键 SHALL 不产生游标移动。键盘移动 SHALL 不移动其他系列的任何游标。

#### Scenario: 点击锁定后的游标可被方向键移动

- **WHEN** 用户左键点击数据点使该游标进入锁定状态后按 Right
- **THEN** 选中的游标移动到本系列下一个有效数据点

#### Scenario: 悬停选中不足以启用键盘移动

- **WHEN** 用户仅悬停选中某游标（未发生任何左键点击）后按 Left/Right/Home/End
- **THEN** 所有游标保持原位

#### Scenario: 键盘目标不随悬停切换

- **WHEN** 用户左键点击游标 A 后悬停使金色高亮落到游标 B，再按方向键
- **THEN** 游标 A 移动，其他游标保持原位，游标 B 不作为键盘移动的目标

#### Scenario: 未发生点击时按键不移动

- **WHEN** 尚无任何左键点击发生时按 Left/Right/Home/End
- **THEN** 所有游标保持原位

### Requirement: tooltip 跟随键盘移动

当前持有图上唯一可见 tooltip 的选中游标被键盘移动时，tooltip SHALL 跟随移动到新的数据点，其 Frame/Value 文本 SHALL 刷新为新位置的数值。鼠标悬停 SHALL 不移动任何 tooltip 的锚点。

#### Scenario: 方向键移动后 tooltip 显示新位置

- **WHEN** 用户点击数据点出现 tooltip 后按 Right
- **THEN** tooltip 锚定到新数据点，文本显示新点的 Frame/Value

#### Scenario: 悬停不拖动 tooltip

- **WHEN** tooltip 可见时鼠标在图内悬停移动
- **THEN** tooltip 锚点保持在其点击时的数据点（锁定游标）或既有非锁定游标行为不变

### Requirement: 键盘导航与默认视图键位隔离

交互绘图会话存在期间，Left/Right/Home/Backspace 按键 SHALL 不触发 matplotlib 工具栏的视图后退/前进/重置导航；会话结束后系统 SHALL 不残留对这些默认键位的修改。

#### Scenario: 视图历史存在时按方向键不跳动坐标系

- **WHEN** 用户 pan/zoom 产生视图历史后按 Left/Right/Home
- **THEN** 仅游标移动，坐标轴范围保持当前视图不变

#### Scenario: 会话关闭后默认键位恢复

- **WHEN** 交互绘图会话断开或关闭
- **THEN** matplotlib 默认键位绑定恢复原状，后续新建的普通 figure 行为不受影响

### Requirement: 锁定游标忽略悬停跟随

鼠标悬停 SHALL 不移动任何锁定游标；锁定游标仅可被键盘（选中时）或点击解锁后移动。

#### Scenario: 悬停不拖动锁定游标

- **WHEN** 某游标处于锁定状态且鼠标贴近其所属系列的数据点悬停
- **THEN** 该游标保持原位，仅选中高亮可随悬停变化
