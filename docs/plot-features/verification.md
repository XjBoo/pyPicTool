# 绘图扩展验证记录

日期：2026-09-08（初始实现验证）。

后续补录说明：本记录早于 [plot-feature-extensions](../../openspec/changes/plot-feature-extensions/proposal.md) 的创建，保留历史测试和工作树审查事实；不能作为该 change 已按固定提交范围完成正式验证或允许归档的证明。原记录中的“本次不创建 change”仅描述初始实现阶段。
基线及当前 HEAD：`91c1b4bf49ae1880ca47cd1bc7a2e2670e2dd971`。

本次代码尚未提交。审查范围为该 HEAD 到工作树的变更，以及新增扩展测试、示例和验收文档；没有把空的提交范围声称为覆盖全部实现。本次不创建、完成或归档 OpenSpec change。

## 验收结果

[验收约定](requirements.md) 的七项功能已实现；[使用示例](../../examples/plot_features.py) 展示双轴、主题、回调、枚举、窗口标题、多行总标题、图例位置和公开规格构建。

- 双轴共享 X、独立 Y，合并图例；点选、悬停、键盘和整体布局经过自动化验证。
- 回调支持原始数据索引与格式化文字；异常回退有测试。
- MATLAB 风格主题与三行总标题布局、局部样式不污染 rcParams 有测试。
- 公开规格的无窗口校验及独立构建有测试。
- 整线模式点击线段、数据点或图例后 Delete/Backspace 删除；NaN 缺口不命中。
- 删除后散点也参与范围计算；双轴共享 X 重算，空轴 0..1，其他线的钉选保留、索引修正。
- 左右枚举刻度和默认 tooltip 的文字映射有测试。

## 实际自动化检查

以下为最后修复后的执行结果，退出码均为 0：

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 单元与交互 | `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` | 84 项通过，9.501 秒；包含 Qt offscreen 子进程验证原生选线按钮、焦点、删除、退出及断开禁用 |
| Hover 冒烟 | `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` | 完整运行无异常；1,000 / 10,000 点每序列、200 次事件，中位数约 0.00455 / 0.01107 秒，不含渲染；无机器无关阈值，不声称性能指标达标 |
| OpenSpec | `openspec validate --changes` | 返回 `No items found to validate.`；无活动 change，不代表进行了本次规格结构校验 |
| 示例导出 | `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.plot_features --save docs/plot-features/preview.png` | 成功导出并目视检查 |
| Diff 空白检查 | `git diff --check` | 通过；不替代 Lint |

## 独立审查与修复

未参与实现的 Reviewer 读取 AGENTS.md、验收约定、相关现有 OpenSpec 交互规格和代码后，只读审查工作树。初审：0 Critical、2 Important、0 Minor。

1. **成立并修复：L 与 Matplotlib 默认 Y 对数比例快捷键冲突。** 将 `keymap.yscale` 的 `l` 纳入会话占用与释放，增加带实际鼠标坐标的键盘回归测试，确认视图保持线性且最后关闭后恢复原键位。
2. **成立并修复：右轴数据可能覆盖左侧 tooltip/高亮。** 新增交互绘制层，在两侧数据之后画 tooltip、焦点及整线描边，图例保持更高优先级。覆盖实际绘制顺序、双击恢复重新挂载图元、删除清理和图例重建。

独立复审确认两个 Important 已解决，修复范围内无新增 Critical / Important。复审实际运行上述两项回归测试，退出码 0。随后主 Agent 重新执行了上述完整检查。

## 真实 Qt GUI 验证

- 执行 `venv/bin/python interactive_plot.py`。沙箱内首次启动因 macOS 窗口服务连接不可用退出 134；随后允许窗口服务访问的启动成功，正常关闭退出 0。
- 在原有六面板中点击原生“选线”，点击图例选中整条线，金色描边出现；Backspace 删除后图例同步移除，其他面板保留；Esc 退出模式。
- 修复后执行 `MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.plot_features`，通过真实桌面鼠标/键盘检查：
  - 窗口显示独立中文标题，MATLAB 风格、双行 suptitle、左右 Y 标签与枚举刻度正常。
  - 左轴点击和 Right 键刷新自定义 tooltip（时间 2 s、温度 23 °C）。
  - L 进入选线，原比例保持；点击高温曲线显示整线金色描边。
  - Backspace 删除高温曲线，左轴由约 20..50 收缩到约 20..27，右轴保留约 100..140，另一曲线 tooltip 保留。
  - 点击状态点，默认 tooltip 显示 `Value: 运行`。
  - 双击背景时左右轴一起放大，其他面板及其提示隐藏；Esc 恢复布局与提示。
  - 合并图例可通过实际鼠标拖动到新位置。
- 后续单独右轴 tooltip 的桌面复查因 Mac 自动锁屏而未继续；右轴点击和键盘路径已有 Agg 自动化覆盖，不能声称该独立桌面复查通过。

## 现有覆盖缺口

| 检查 | 状态 |
| --- | --- |
| 类型检查 | 未执行；仓库仅有 mypy 配置，未安装/采用检查命令 |
| Lint / 格式 | 未执行；仓库仅有 Ruff 配置，未安装/采用检查命令 |
| 构建 | 缺少能力；未声明 build-system 或构建命令 |
| 独立 E2E | 缺少独立套件；Agg 交互测试和 Qt offscreen 探针不等于完整 E2E |
| 安全扫描 | 缺少配置；无 secret scan、SAST 或依赖漏洞扫描命令 |
| Windows / 多种 DPI | 未在 Windows 或多种显示缩放设置下验证 |

这些覆盖缺口未计为通过。
