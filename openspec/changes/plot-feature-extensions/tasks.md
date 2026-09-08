## 1. 补录后逐项核对既有实现

以下是本 change 的待核对清单，不代表代码尚未编写。既有实现和历史 84 项测试记录见 `docs/plot-features/verification.md`；apply 时先检查已有实现，只修补实际差异，逐项确认后勾选。本轮规划不提前替后续验证勾选。

- [x] 1.1 核对公开 FigureSpec/PanelSpec/build_figure/to_spec 的入口、输入校验和生命周期，以 `tests/test_plot_extensions.py` 的规格校验及快照测试、`tests/test_figure_interface.py` 的冻结/失败清理测试证明符合对应规格。
- [x] 1.2 核对共享 X、独立 Y、主轴与右轴访问及屏幕命中，用双轴点击/悬停/键盘和布局恢复测试确认两侧交互与面板整体恢复；发现缺失时补实现及针对性测试。
- [x] 1.3 核对每序列 tooltip 回调的原始索引、轴格式化值、异常回退及枚举，用原始索引/缺失值/枚举/回调异常测试确认，补足尚未覆盖的输入或刷新场景。
- [x] 1.4 核对 default/matlab 主题、独立窗口标题、图例位置及多行总标题，用主题隔离及总标题布局测试和 examples/plot_features.py 的导出图片确认外观与参数行为。
- [x] 1.5 核对整线选择模式的按钮/L/点击命中/空白清除/Esc、普通点模式保留及导航优先级，用线段和 NaN 缺口测试、带鼠标位置的 L 键测试与 Qt 按钮探针确认。
- [x] 1.6 核对稳定句柄删除、重复/跨会话/断开行为、游标与图例清理、散点和双轴范围适配及其他面板保留，以删除测试及必要的边界用例确认。
- [x] 1.7 核对交互层对两侧数据的绘制优先级，以及图元删除、状态恢复、隐藏和导出生命周期，用实际 draw 顺序与恢复清理测试确认，补足差异。
- [x] 1.8 核对 README、示例和历史验收文档与本 change 一致，形成需求→代码→测试或桌面证据对应清单，并明确未覆盖场景。

## 2. 固定范围与真实验证

- [ ] 2.1 在功能分支固定实现及规格提交，记录基线 `91c1b4bf49ae1880ca47cd1bc7a2e2670e2dd971`、待审 SHA、merge-base 和未提交修改；用 Git 状态及 diff 清单确认正式范围包含实现、测试、规格和文档。
- [ ] 2.2 对待审版本执行 `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`、`PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py`、`openspec validate --changes`，记录各命令退出码及结果；无性能阈值不声称指标达标。
- [ ] 2.3 按 AGENTS.md 执行 `venv/bin/python interactive_plot.py` 并结合扩展示例核验 Qt 窗口生命周期、左右轴 tooltip、整线按钮/快捷键、删除缩放、图例/tooltip 拖动及布局恢复；记录实际场景、结果和无法执行项，不把此前未完成的右轴桌面复查算作通过。
- [ ] 2.4 形成该 change 的正式验证报告，逐项列出类型、Lint、构建、独立 E2E、安全扫描及平台覆盖缺口，区分通过、失败、未执行和缺少能力，验收所需能力未满足则保持待完成。

## 3. 独立审查与修复闭环

- [ ] 3.1 将本 change 全部规格、设计、任务、固定 Git 范围和验证报告交给未参与实现的 Reviewer，只读形成 Critical/Important/Minor 稳定清单，逐项附定位与触发依据。
- [ ] 3.2 独立审查完成后逐项依据规格、代码和测试确认意见，记录成立、误报理由或待澄清；对成立问题修复并执行相关检查，以结果及问题处置记录证明解决。
- [ ] 3.3 若发生修复，重新执行适用完整检查并按需独立复审修复范围；若无修复或新问题，保留本阶段已执行的有效验证，不作无理由重复运行。
- [ ] 3.4 汇总正式收尾结论：无未解决 Critical、无未接受风险的 Important、必需验证完成；仅达标后进入同步/归档阶段，以独立报告和真实检查为依据，不以规划 artifact 状态或历史实现总结替代。
