## Context

动机见 proposal.md。当前 `create_interactive_plot` 同时负责推导网格、创建 artist、写入固定文字及安装交互。`PlotSession` 已集中管理资源，`DataCursor` 与 `FigureDispatcher` 已支持多个子图，因此无需重写交互引擎。当前工作区 `AGENTS.md` 有用户修改。

## Goals / Non-Goals

**Goals:** 小型公开接口隐藏样式、布局和交互初始化；明确多个整图之间的所有权；将子图配置从系列数据移出；保留旧入口。

**Non-Goals:** 不提供隐式全局当前轴；本轮只支持构建前依次添加数据，不支持显示后修改数据或结构。

## Decisions

### 1. 显式对象式接口

拟定调用方式：

```python
from interactive_plotting import figure
import matplotlib.pyplot as plt

fig = figure(rows=2, cols=1, title="实验结果", figsize=(10, 8))
top = fig.subplot(1, title="温度变化", xlabel="时间 / s", ylabel="温度 / °C")
top.plot([0, 1, 2], [20, 22, 21], label="传感器 A", color="blue", marker="o")
top.plot([0, 1, 2], [19, 21, 23], label="传感器 B", color="orange", marker="s")
bottom = fig.subplot(2, title="压力变化", xlabel="时间 / s", ylabel="压力 / kPa")
bottom.plot([0, 1, 2], [100, 102, 101], label="压力", marker="^", linestyle="--")
session = fig.build()
plt.show()
session.close()
```

每次 `figure()` 创建独立描述对象。默认布局 1×1；`subplot(index)` 从 1 开始按行编号，布局在 figure 创建时固定。重复取得同一编号返回同一子图；显式传入的文字更新该子图，省略的文字保持原值。新接口轴标签与标题默认空字符串，调用方决定物理量。用户明确创建的空子图可见，未使用的格子隐藏。`plot` 始终追加，返回该子图对象，可连续调用；label 可省略，无 label 的曲线不进入图例。默认按子图独立循环配色，默认实线与圆点；`marker=None` 隐藏数据点，`linestyle="None"` 隐藏连线，至少一者可见。开放 linewidth、markersize，markersize 使用点大小语义，由绘制层转换成 scatter 面积。

相比复制 Matlab 全局状态，显式持有图与子图更适合外部库调用，也避免多个调用方将曲线画到错误窗口。相比仅增加配置字典，逐条 plot 更接近用户预期，并将线数量直接表达为调用次数。

### 2. 一次性构建与会话所有权

描述阶段不创建窗口、不注册回调。`build()` 完整验证后创建并返回 `PlotSession`，不调用 show；成功后冻结描述，重复 build 返回原会话。构建后尝试改结构、样式或追加曲线报 RuntimeError；已关闭的会话不自动重新打开。构建失败释放中间资源，描述仍可修改重试。不额外增加隐含构建的 show 方法，避免拥有两个不同的窗口生命周期接口。多图可分别 build，再由调用方一次 `plt.show()` 显示。

这一取舍降低本轮交互状态迁移复杂度，但与可随时追加数据的 Matlab 不完全一致；此限制是方案确认时需明确展示的产品边界。

### 3. 分离描述、渲染与交互

新增 `api.py` 管理公开 figure/subplot/plot 描述及冻结规则；`model.py` 保存规范化的整图、子图和系列配置；核心内部构建函数只接收完整描述。新入口与旧 `create_interactive_plot` 都通过同一个内部构建路径创建 artist 和交互会话。内部类不全部导出为公共契约。

保留 SeriesData 已有字段的顺序与默认值，新增样式字段只能以默认值扩展。兼容入口仍自动推导网格、使用 Frame Number/Value、保留原面板标题选择与默认颜色。旧示例与旧测试不得被迫迁移。演示逐步改为使用新入口，但 make_demo_series 的输出与旧入口继续可用。

整图总标题在布局计算前设置；图例仅在存在非空 label 时创建。子图标题继续左对齐。所有样式局限于本图，不修改全局视觉配置。颜色、形状、线型和尺寸在创建图前校验；数据校验复用现有 SeriesData 规则。

### 4. 保留交互事件顺序

复用原 dispatcher：工具栏导航模式优先隔离光标操作，图例和 tooltip 手势优先于子图背景双击，数据点击及 Shift 钉选按现有契约处理；悬停不改变键盘目标。Esc 在最大化时恢复布局，否则清除钉选。数据点 marker 可配置，交互焦点仍为圆形金边；tooltip 保持 Frame/Value 与现有轴格式器语义。布局捕获在全部标题、图例和布局计算完成后执行。任意网格、空子图及多个窗口均需验证关闭与事件隔离。

## Risks / Trade-offs

- [一次性构建不同于 Matlab 即时绘图] → 文档和示例明确先描述、后 build；不承诺显示后追加曲线。
- [新旧入口默认行为不一致] → 在兼容转换处明确默认值，保留既有测试，并增加两个入口输出一致性的测试。
- [总标题或长标签影响布局] → 使用非默认网格、长文字及总标题作渲染检查，并验证放大恢复。
- [对象多持有一次数据副本] → 尽量复用只读规范化数组，不额外建立平行数据模型或第二套交互控制器。

## Migration Plan

方案确认后创建 `codex/flexible-plotting-interface`，记录基线；将本 change 文档随实现纳入分支。先统一内部构建路径，再增加新入口、迁移演示和文档，保留旧入口。以公开接口回归测试证明兼容性。完成后按仓库契约固定提交范围、独立审查及修复验证；本次不自动归档。回退时可撤销本 change 的实现提交，旧入口与演示保持可恢复。
