# cursor-keyboard-navigation Specification

## Purpose

定义选中游标的键盘导航契约：方向键与 Home/End 移动当前选中的游标（不区分锁定状态）、tooltip 对键盘移动的跟随行为、锁定语义与键盘的关系，以及与 matplotlib 默认视图导航键位的隔离。

## Requirements

### Requirement: 键盘移动最近点击选中的点

以下鼠标和键盘交互 SHALL 在普通点选择模式且未被导航或拖动占用时生效；整线选择模式暂停这些点操作，退出后恢复。

系统 SHALL 仅对最近被鼠标左键点击选中的点（普通活动选中、Shift+左键新增的钉选点，或左键点击其 tooltip）响应 Left/Right/Home/End：方向键移动到本系列的上一/下一有效数据点，Home/End 跳转到第一个/最后一个有效数据点。仅经悬停预览的点 SHALL NOT 响应这些按键；悬停变化预览点 SHALL NOT 改变键盘移动目标。未发生任何左键点击时，这些按键 SHALL NOT 移动任何点。

#### Scenario: 普通选中点可被方向键移动

- **WHEN** 在普通点选择模式下，用户普通左键点击数据点后按 Right
- **THEN** 活动选中移动到本系列下一个有效数据点

#### Scenario: 钉选点可被方向键移动

- **WHEN** 在普通点选择模式下，用户经 Shift+左键新增钉选点后按 Right
- **THEN** 该钉选点及其 tooltip 移动到本系列下一个有效数据点

#### Scenario: 悬停预览不启用键盘移动

- **WHEN** 在普通点选择模式下，用户仅悬停预览某点，未发生左键点击，随后按 Left/Right/Home/End
- **THEN** 所有活动选中和钉选点保持原位

#### Scenario: 键盘目标不随悬停切换

- **WHEN** 在普通点选择模式下，用户左键点击点 A 后悬停预览点 B，再按方向键
- **THEN** 点 A 移动，点 B 不作为键盘移动目标

#### Scenario: 未发生点击时按键不移动

- **WHEN** 在普通点选择模式下，尚无任何左键点击发生时按 Left/Right/Home/End
- **THEN** 所有标记保持原位

### Requirement: tooltip 跟随键盘移动

当前键盘目标被移动时，其 tooltip SHALL 跟随移动到新的数据点，其内容 SHALL 按新位置刷新：默认使用所属轴格式化的 Frame/Value，配置回调时使用该序列的回调结果。其他活动或钉选 tooltip SHALL 保持在原位。鼠标悬停 SHALL NOT 移动任何 tooltip 的锚点。

#### Scenario: 方向键移动后 tooltip 显示新位置

- **WHEN** 用户点击数据点出现 tooltip 后按 Right
- **THEN** 键盘目标的 tooltip 锚定到新数据点并显示新点的默认 Frame/Value 或回调内容，其他 tooltip 保持不变

#### Scenario: 悬停不拖动 tooltip

- **WHEN** 图上存在活动选中或钉选 tooltip 时鼠标在图内悬停移动
- **THEN** 所有 tooltip 的锚点保持在各自的点击或键盘移动位置

### Requirement: 键盘导航与默认视图键位隔离

交互绘图会话存在期间，Left/Right/Home/Backspace 按键 SHALL 不触发 matplotlib 工具栏的视图后退/前进/重置导航，L SHALL 不触发 Y 轴线性／对数比例切换；最后一个会话结束后系统 SHALL 不残留对这些默认键位的修改。

#### Scenario: 视图历史存在时按方向键不跳动坐标系

- **WHEN** 用户 pan/zoom 产生视图历史后按 Left/Right/Home
- **THEN** 仅游标移动，坐标轴范围保持当前视图不变

#### Scenario: 会话关闭后默认键位恢复

- **WHEN** 最后一个交互绘图会话断开或关闭
- **THEN** matplotlib 默认键位绑定恢复原状，后续新建的普通 figure 行为不受影响

#### Scenario: 鼠标位于绘图区时切换选线
- **WHEN** 鼠标停在绘图区并按 L 进入或退出整线模式
- **THEN** 仅切换选择模式，Y 轴比例和坐标范围保持原状

### Requirement: 持久选中不阻塞悬停预览

以下鼠标和键盘交互 SHALL 在普通点选择模式且未被导航或拖动占用时生效；整线选择模式暂停这些点操作，退出后恢复。

活动选中或钉选点存在时，鼠标悬停 SHALL 仍能预览任意系列的其他数据点。悬停预览 SHALL NOT 移动、隐藏或改变已有活动选中或钉选点的 tooltip。

#### Scenario: 同系列已选中后仍可悬停其他点

- **WHEN** 在普通点选择模式下，某系列已有活动选中或钉选点，鼠标移到该系列的另一数据点
- **THEN** 另一数据点显示悬停预览高亮，已选中或钉选点保持原位和可见
