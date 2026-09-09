## ADDED Requirements

### Requirement: 可选择且局部生效的主题

图表 SHALL 保留默认浅色主题并提供可选 MATLAB 风格主题，后者采用七色序列循环、浅灰画布、白色绘图区及盒式边框。主题 SHALL 只作用于当前图；显式曲线颜色 SHALL 优先于默认循环，既有旧调用颜色 SHALL 保留。未知主题 SHALL 在创建图前被拒绝。

#### Scenario: 主题图与普通图共存
- **WHEN** 调用方创建 MATLAB 风格图后创建默认图及普通绘图
- **THEN** 各图保留各自样式，全局视觉默认值未被主题修改

### Requirement: 双轴交互图元的可辨性

两侧 tooltip、点焦点及整线选择描边 SHALL 绘制在两侧数据曲线之上，图例 SHALL 保持高于交互提示的绘制及手势优先级。隐藏面板 SHALL 不残留可见交互图元；恢复布局和删除曲线 SHALL 同步恢复或清理对应提示。

#### Scenario: 右轴曲线穿过左侧提示
- **WHEN** 右轴曲线经过左轴 tooltip 或点焦点所在的屏幕位置
- **THEN** 提示和焦点仍清晰可见，不被右轴曲线遮住

## MODIFIED Requirements

### Requirement: 视觉调整保留交互契约

普通点选择模式下，新样式 SHALL 保留现有悬停、点击、Shift 钉选、删除、键盘移动、图例及 tooltip 拖动、工具栏导航隔离、双击放大和 Esc 语义。焦点 SHALL 继续使用圆形标记及金色加粗边缘；未指定回调时 tooltip SHALL 继续仅显示按所属轴格式器格式化的 Frame 和 Value；指定回调时 SHALL 显示该序列的自定义文本。单面板放大后恢复 SHALL 还原放大前的布局和选中状态。

#### Scenario: 选中并移动数据点

- **WHEN** 在普通点选择模式下，用户点击数据点后按 Right，再悬停另一个点
- **THEN** 仅键盘目标移动且刷新 tooltip，悬停预览独立，圆形焦点仍清晰可辨

#### Scenario: 放大后恢复

- **WHEN** 在普通点选择模式下，用户拖动图例、钉选数据点后双击面板背景放大，再按 Esc
- **THEN** 原布局与钉选状态恢复，图例与 tooltip 仍可拖动
