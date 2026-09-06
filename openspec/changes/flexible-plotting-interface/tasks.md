## 1. 分支和统一构建模型

- [x] 1.1 确认方案后创建 codex/flexible-plotting-interface 分支并记录基线提交，核对 git status，保留且不提交用户既有 AGENTS.md 修改。
- [x] 1.2 分离整图、子图和系列配置并统一内部构建路径；通过旧公开入口回归测试证明默认布局、颜色、轴文字和缺失值语义不变。

## 2. 公开接口和自定义呈现

- [x] 2.1 实现并导出 figure/subplot/plot 对象式接口及参数校验；通过公开接口测试验证 1×1、2×2、多图、重复子图、空子图、稀疏布局和非法输入。
- [x] 2.2 实现总标题、左上角子图标题、轴文字、多曲线样式和按子图循环配色；通过 artist 属性及图例测试核对独立颜色、marker、线型、线宽、点大小和无 label 行为。
- [x] 2.3 实现 build 的非阻塞创建、冻结、重复调用、异常清理和关闭规则；通过窗口计数及事件绑定测试证明无泄漏且图间隔离。
- [x] 2.4 将新配置接入现有交互，补充非默认布局、不同 marker、多窗口的事件测试；验证点击、钉选、键盘移动和放大恢复不改变既有行为。

## 3. 文档和整体验证

- [x] 3.1 更新 README 和演示，提供单图、多图、多子图、多曲线示例，说明 1 起始编号、先描述后 build 和兼容入口；运行示例的 Agg 构建与保存验证并检查输出图片。
- [x] 3.2 运行 MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v，记录退出码及测试结果。
- [x] 3.3 运行 PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py，记录成功运行情况，不将冒烟结果解释为达到性能阈值。
- [x] 3.4 运行 openspec validate --changes，记录结构校验结果。
- [x] 3.5 运行 venv/bin/python interactive_plot.py 并对自定义布局执行真实桌面检查，记录标题、图例、工具栏、光标交互、多窗口关闭及放大恢复场景；未能执行的场景明确标记未验证。

## 4. 独立审查和修复

- [x] 4.1 固定 merge-base 到待审提交的范围，由未参与实现的独立 Reviewer 依据本 change 规格审查，报告 Critical/Important/Minor 及证据，明确未提交修改是否排除。
- [x] 4.2 逐项验证审查问题后独立进入修复回合，记录成立、误报及需澄清项；修复后运行相关检查和适用完整检查，并对必要的新增改动重新审查。
- [x] 4.3 输出收尾记录，逐项报告测试、性能冒烟、OpenSpec、GUI 及类型检查、Lint、构建、E2E、安全扫描的结果或覆盖缺口；存在阻断问题或必需检查未完成时不宣布完成，不自动归档。
