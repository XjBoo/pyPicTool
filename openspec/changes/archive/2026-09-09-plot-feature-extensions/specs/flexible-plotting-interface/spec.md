## ADDED Requirements

### Requirement: 共享横轴的左右双纵轴面板

接口 SHALL 允许每条曲线选择左或右 Y 轴，同面板共享 X 轴，两侧具有独立的 Y 范围、标签及格式器。两侧命名曲线 SHALL 合并到可拖动图例；悬停及点选 SHALL 按屏幕距离选择对应轴的数据点，tooltip SHALL 使用该轴坐标。面板放大和恢复 SHALL 同时作用于两侧轴。既有主轴访问顺序 SHALL 保留，新增右轴 SHALL 可按面板编号访问。

#### Scenario: 两种量纲同图交互
- **WHEN** 同一面板绘制左侧温度和右侧压力，并在普通点模式分别点击两侧点及按方向键
- **THEN** 两侧使用各自 Y 范围、共享 X 范围，选中及 tooltip 对应正确曲线和坐标，图例包含两条曲线

#### Scenario: 双轴布局恢复
- **WHEN** 用户放大双轴面板后恢复
- **THEN** 两侧轴一起放大并回到原布局，其他面板恢复原可见性，选中状态保留

### Requirement: 每序列提示内容回调

接口 SHALL 支持每条序列配置返回字符串的 tooltip 回调，输入包含序列、原始数组零起始索引、原始 x/y 和所属轴格式化文字。点击、钉选及键盘移动 SHALL 刷新内容，悬停 SHALL 不调用回调。未指定回调 SHALL 使用默认 Frame/Value；回调异常或返回非字符串 SHALL 发出运行时警告并回退为默认内容，不破坏选择和后续交互。

#### Scenario: 缺失点不改变业务索引
- **WHEN** 含缺失值的序列通过键盘跳到后续有效点
- **THEN** 回调得到该点在原数组中的索引及格式化文字，而不是过滤缺失值后的索引

#### Scenario: 回调失败后继续交互
- **WHEN** 自定义回调抛出异常或返回非字符串
- **THEN** tooltip 使用默认 Frame/Value，产生警告，后续选择仍可进行

### Requirement: 公开规格描述和构建入口

调用方 SHALL 可公开导入 FigureSpec、PanelSpec 并使用 build_figure(spec) 构建，也 SHALL 可使用 builder.to_spec() 获取不创建窗口的当前描述快照。规格面板坐标 SHALL 为零起始行列，序列坐标 SHALL 与所属面板一致。公开构建 SHALL 在分配窗口前校验布局、重复或越界面板、文字、数据、轴归属与样式，非法输入 SHALL 抛 ValueError。直接规格构建每次 SHALL 返回独立会话、不调用 show；builder 原有冻结及幂等构建契约 SHALL 保留。

#### Scenario: 同一快照创建独立会话
- **WHEN** 调用方对同一合法规格调用两次公开构建
- **THEN** 得到相互独立的会话，关闭其中一张图不影响另一张

#### Scenario: 无效规格不分配窗口
- **WHEN** 规格包含重复或越界面板、曲线面板不匹配、非法样式或轴归属
- **THEN** 构建在窗口创建前抛 ValueError，不留下部分会话

### Requirement: 窗口标题与总标题及图例初始位置

接口 SHALL 分别支持窗口标题和图内总标题；多行总标题 SHALL 支持字号、字重、行距及左中右对齐，并由布局预留空间。面板 SHALL 支持图例命名初始位置，构建后仍可拖动；不指定参数 SHALL 保留既有默认行为。

#### Scenario: 多行总标题及图例配置
- **WHEN** 调用方指定独立窗口标题、三行总标题样式及左下角图例
- **THEN** 窗口标题与图内文字各自生效，总标题不覆盖绘图区，图例位于指定初始位置且可拖动

### Requirement: 左右纵轴枚举文字

左右 Y 轴 SHALL 可独立配置有限数值到字符串的映射，刻度与默认 tooltip SHALL 使用映射文字；未映射值的 tooltip SHALL 显示数值。数据仍 SHALL 采用数值数组。builder 接收映射时 SHALL 复制保存；空映射 SHALL 清除枚举配置，非法键或非字符串标签 SHALL 抛 ValueError。

#### Scenario: 设备状态文字
- **WHEN** Y 轴配置 0 对应关闭、1 对应运行，并选中值为 1 的点
- **THEN** 刻度显示对应文字，默认 tooltip 的 Value 显示运行

#### Scenario: 映射输入隔离
- **WHEN** 调用方配置映射后修改原字典
- **THEN** 已有绘图描述不受原字典后续修改影响

## MODIFIED Requirements

### Requirement: 兼容旧调用和既有交互

原 SeriesData 和 create_interactive_plot 调用 SHALL 继续保留现有参数默认值、推导布局、轴文字及缺失值处理。新接口 SHALL 复用悬停、点击、钉选、键盘移动、拖动、工具栏隔离及放大恢复契约；非默认布局的恢复 SHALL 回到原布局。未指定内容回调时，tooltip SHALL 保留 Frame/Value 及轴格式器语义；指定回调时 SHALL 使用对应序列的自定义内容。普通点模式保持既有点交互，整线模式遵循独立曲线选择与删除契约。

#### Scenario: 旧六子图调用
- **WHEN** 旧调用方将 make_demo_series 的输出传给 create_interactive_plot
- **THEN** 仍得到六子图的原有视觉与交互，无需修改调用代码

#### Scenario: 自定义图交互
- **WHEN** 用户在含方形数据点的 2×2 图上悬停、点击、Shift 钉选、按方向键并双击放大后按 Esc
- **THEN** 各交互保持原有语义，圆形选择焦点可辨，恢复原布局和选择状态
