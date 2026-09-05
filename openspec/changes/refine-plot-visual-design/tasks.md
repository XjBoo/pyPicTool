## 1. 视觉实现

- [x] 1.1 保存 seed=42 的现状图并记录基线提交；验证图像可打开且六面板数据可重复生成。
- [x] 1.2 实现局部样式和字体回退，统一画布、坐标轴、标题、网格与边框；验证缺失首选字体不阻止渲染，创建/关闭会话不污染全局视觉配置。
- [x] 1.3 实现未指定 line_color 时与散点同色，调整演示配色和标签；以自动化检查验证显式颜色/透明度保留、缺失点断线与数据值未改变。
- [x] 1.4 优化图例、tooltip 和面板留白，统一初始布局入口；查看固定数据六面板、单面板及有选中点的渲染图，确认文字无重叠且焦点清晰。

## 2. 回归与兼容性

- [x] 2.1 执行 `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`，确认已有鼠标键盘、拖动、放大恢复与新增视觉契约检查通过，记录实际结果。
- [x] 2.2 执行 `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` 与 `openspec validate --changes`；记录退出码，不把性能冒烟解释为性能指标达标。
- [ ] 2.3 运行 `venv/bin/python interactive_plot.py`，真实检查悬停、普通点击、Shift 钉选、方向键/Home/End、Delete/Backspace、图例与 tooltip 拖动、双击/Esc、工具栏 pan/zoom、缩放与关闭窗口；按场景记录结果，无法执行的场景列为未执行。
- [x] 2.4 更新 README 的视觉说明、Windows 启动命令 `venv\Scripts\python.exe interactive_plot.py` 及中文字体、高 DPI 检查清单；明确 Windows 实机验证的执行状态，不将本机 Agg 结果等同 Windows 通过。

## 3. 评审与交付

- [x] 3.1 交付相同种子的前后对比图与验证报告；逐项列出测试、性能冒烟、OpenSpec、GUI 状态，以及类型检查、Lint/格式、构建、E2E、安全扫描的覆盖缺口。
- [x] 3.2 按 AGENTS.md 固定基线、待审提交和 merge-base，列明未纳入的未提交修改；交由未参与实现的独立 Reviewer 读取规格并审查，形成含证据与 Critical/Important/Minor 分级的稳定清单，评审回合不改代码。
- [ ] 3.3 逐项核实意见、记录误报理由并修复成立的问题，修复后执行相关及完整适用检查，必要时重新独立评审；仅在必需验证完成且阻断问题已解决或按规则接受后报告实现完成，不自动归档。

## 4. 用户试用后的布局微调

- [x] 4.1 缩小标题并移除演示标题序号，收紧标题、轴标签和面板间距；以相同 seed、窗口尺寸渲染，测量数据绘图区面积增大并检查文字不重叠。
- [x] 4.2 重新运行完整测试、Hover 冒烟及 OpenSpec 校验，更新效果图和验证记录；保留尚未完成的真实 GUI 验收状态。

- [x] 4.3 按二次反馈将标题和间距调整至前两版之间，查看更新图片并重新执行完整测试、Hover 冒烟和 OpenSpec 校验。
