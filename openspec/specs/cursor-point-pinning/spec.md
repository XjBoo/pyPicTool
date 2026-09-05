# cursor-point-pinning Specification

## Purpose

定义数据点的普通选中与多点钉选行为，使用户既能查看单个当前点，也能在同一图中保留多个对比点及其标签。

## Requirements

### Requirement: 普通点击建立唯一活动选中

系统 SHALL 在左键点击命中未钉选数据点时将该点设为全图唯一的活动选中，显示该点的圆形加粗标记和 tooltip。左键点击不同的未钉选点 SHALL 同时移除旧活动选中的标记和 tooltip，但 SHALL NOT 移除其他钉选点。左键再次点击当前活动选中所在的同一数据点 SHALL 取消活动选中，同时隐藏其标记和 tooltip 并清空键盘目标。

#### Scenario: 跨系列普通点击替换选中

- **WHEN** 用户先普通点击蓝色系列的点，再普通点击红色系列的点
- **THEN** 仅红色点保持活动选中标记和 tooltip，蓝色点的活动选中标记和 tooltip 同时消失

#### Scenario: 普通点击不清除钉选

- **WHEN** 图上已有一个或多个钉选点，用户普通点击另一数据点
- **THEN** 新点成为唯一活动选中，所有已有钉选点及其 tooltip 保持不变

#### Scenario: 再次点击活动点取消选中

- **WHEN** 用户左键点击某未钉选数据点使其成为活动选中，随后再次左键点击同一点
- **THEN** 该点的活动选中标记和 tooltip 消失，键盘目标被清空，已有钉选点保持不变

### Requirement: Shift 点击支持多点钉选

系统 SHALL 在 Shift+左键点击命中数据点时新增一个钉选点，并持续显示其圆形标记和 tooltip。后续的悬停、普通点击或 Shift+点击 SHALL NOT 自动隐藏已有钉选点的标记或 tooltip。

#### Scenario: 同面板钉住多个点

- **WHEN** 用户对同一面板中的多个数据点依次执行 Shift+左键点击
- **THEN** 每个被点击的点都同时保留圆形标记和 tooltip

#### Scenario: 跨面板钉住多个点

- **WHEN** 用户在不同面板中依次执行 Shift+左键点击
- **THEN** 各面板的钉选点和 tooltip 同时保持可见

### Requirement: 选中标记使用统一圆形视觉

系统 SHALL 对悬停预览、活动选中和钉选点使用圆形标记，并使用尺寸或边缘加粗表示当前焦点。系统 SHALL NOT 使用方形区分持久状态。

#### Scenario: 点击后仍为圆形

- **WHEN** 用户普通点击或 Shift+左键点击一个数据点
- **THEN** 该点显示为圆形标记，视觉效果与悬停时的加粗点一致

### Requirement: 钉选点可被单独删除或批量清除

系统 SHALL 允许通过普通左键点击钉选点或删除当前选中的钉选点，并 SHALL 允许一次清除全图所有钉选点。删除 SHALL 同时移除该钉选点的标记和 tooltip，如果该点是键盘目标则 SHALL 清空键盘目标，且 SHALL NOT 移除普通活动选中或其他钉选点。左键点击钉选点 SHALL NOT 在同一位置创建新的活动选中。左键点击 tooltip 仍 SHALL 用于选择键盘目标或开始拖动，不触发取消。

#### Scenario: 左键点击钉选点取消钉选

- **WHEN** 用户普通左键点击一个钉选点
- **THEN** 仅该钉选点的标记和 tooltip 被移除，不在该位置建立活动选中

#### Scenario: 删除当前钉选点

- **WHEN** 用户选中一个钉选点并触发单点删除
- **THEN** 仅该钉选点的标记和 tooltip 被移除

#### Scenario: 清除全部钉选点

- **WHEN** 用户触发全部钉选点清除
- **THEN** 全图所有钉选点及其 tooltip 被移除，普通活动选中保持不变
