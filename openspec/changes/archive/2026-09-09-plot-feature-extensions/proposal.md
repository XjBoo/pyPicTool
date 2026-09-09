## Why

pyPicTool 的既有接口缺少同面板双 Y 轴、业务 tooltip、可选主题、公开规格构建、整线删除和状态枚举，调用方难以完整描述实验数据。本次将用户七项 TODO 纳入可追踪的行为规格，便于后续维护和验收。

本 change 为**实现后补录**：七项功能已在工作树实现并按临时验收约定验证，随后用户要求纳入 OpenSpec。原始 TODO、用户明确确认的共享 X／独立左右 Y、数值→文字枚举、专门选线后快捷键删除为需求来源；现有代码仅用于核对落实方式，不是需求正确性的唯一依据。既有测试与审查属于历史证据，不视为本 change 的正式收尾批准。

## What Changes

- 支持共享 X 轴、左右独立 Y 轴的面板，合并图例并保留两侧完整交互。
- 支持每序列 tooltip 内容回调，提供原始索引、数值及轴格式化文字；未指定时保持 Frame/Value。
- 保留默认主题，新增可选 MATLAB 风格主题；样式局限于当前图。
- 公开 FigureSpec、PanelSpec、build_figure 和 builder.to_spec；提供创建窗口前的参数校验。
- 支持独立窗口标题、图例初始位置和多行总标题样式。
- 支持独立整线选择模式、快捷键删除及程序化删除；删除后清理曲线相关交互并重算所属面板范围。
- 支持左右 Y 轴数值到枚举文字映射，刻度与默认 tooltip 一致。
- 将现有规格中无条件的 tooltip／键盘描述补充为默认行为或按交互模式区分，保留普通点选择语义。

## Capabilities

### New Capabilities

- `curve-selection-deletion`: 整线选择模式、稳定曲线句柄、删除及范围自动适配。

### Modified Capabilities

- `flexible-plotting-interface`: 双轴、公开 FigureSpec API、每序列回调、枚举、窗口标题和图例／总标题配置。
- `plot-visual-presentation`: 可选主题，默认 tooltip 与自定义内容的边界，以及双轴交互图层顺序。
- `cursor-keyboard-navigation`: 按普通点模式与整线模式区分键位职责，隔离 L 默认缩放快捷键。
- `cursor-point-pinning`: 明确普通点模式下的点击与钉选契约，整线模式暂停点操作。
- `cursor-hover-highlight`: 明确普通点模式触发点悬停，整线模式暂停瞬态预览。

## Impact

影响 `interactive_plotting/{model,api,core,style,qt_toolbar,__init__}.py`、README、示例、测试和 `docs/plot-features/`。保留 `interactive_plotting` 包名和旧 SeriesData/create_interactive_plot 调用，不新增运行依赖；后端仍为 QtAgg/PySide6，自动化逻辑测试仍采用 Agg。

基线为 `91c1b4bf49ae1880ca47cd1bc7a2e2670e2dd971`。此时实现尚未提交；后续在 `codex/plot-feature-extensions` 固定待审提交，并按 merge-base 到该提交重新建立正式审查范围。本轮只补规划，不同步主规格或归档。
