## Why

现有绘图核心已能按系列所在面板推导布局，但轴标签、点形状等仍写死，面板标题还耦合在线数据上。外部调用者需要用少量接近 Matlab figure/subplot/plot 的操作描述任意基础多图、多子图及多曲线绘图，并复用现有交互。

## What Changes

- 提供显式对象式 `figure → subplot → plot` 接口，支持多张独立整图、矩形子图布局和每个子图任意数量曲线。
- 分离整图配置、子图文字和系列样式，开放总标题、左上角子图标题、横纵轴文字、颜色、点形状及基础线型。
- 将绘图描述一次性构建为现有交互会话；显示由调用者控制。
- 保留 `SeriesData`、`create_interactive_plot` 及六子图演示的兼容入口与交互行为。
- 增加调用示例、参数校验、非默认布局与交互回归验证。

## Capabilities

### New Capabilities
- `flexible-plotting-interface`: 图形、子图与曲线的可组合公开接口、配置规则及生命周期。

### Modified Capabilities
无。现有视觉与光标交互契约保留；自定义数据点形状不改变圆形交互焦点。

## Impact

影响 `interactive_plotting/model.py`、`core.py`、包导出、演示、README 和测试；新增公开构建模块。继续使用 Matplotlib 与 PySide6，无新增运行时依赖。确认方案后从当前主线创建 `codex/flexible-plotting-interface` 实现分支；已有未提交的 `AGENTS.md` 改动不纳入实现提交。

## Non-goals

不完整复刻 Matlab，不引入全局“当前图/当前轴”、实时数据更新、渲染后追加曲线、任意跨格布局、双 Y 轴或新绘图类型。本轮聚焦基础折线与点图，外部业务数据格式仍由调用方适配。
