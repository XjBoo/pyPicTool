## 1. 交互状态模型

- [x] 1.1 为 hover preview、全图唯一 active selection、多个 pinned selections 和 keyboard target 建立显式状态，并通过初始状态与状态转换单元测试验证它们相互独立
- [x] 1.2 更新双击快照和恢复逻辑以覆盖新状态，并验证双击最大化不会保留第一次单击的标记、tooltip 或键盘目标

## 2. 悬停与普通选中

- [x] 2.1 实现独立的 hover preview artist 和重合点去重样式，并测试已有 active/pinned 点时同系列和跨系列的其他点仍可悬停高亮
- [x] 2.2 将普通左键点击改为全图唯一 active selection 替换，并测试跨系列、跨面板点击时旧 marker 和 tooltip 同时消失、新 marker 和 tooltip 同时出现
- [x] 2.3 将 hover、active 和 pinned 标记统一为圆形并用尺寸/描边表示焦点，并用 artist 属性测试确认点击后不再出现方形

## 3. 多点钉选与标签

- [x] 3.1 实现 Shift+左键追加 pinned selection 且不隐藏已有 pinned tooltips，并测试同系列、跨系列和跨面板多个点及标签可同时保持可见
- [x] 3.2 使普通点击只替换 active selection 而不清除 pinned selections，并通过普通点击前后的 pinned marker/tooltip 状态断言验证
- [x] 3.3 适配 tooltip 点击、拖动、Delete/Backspace 单点删除和 Escape 批量清除，并测试这些操作只影响目标 pinned selection，不影响 active selection 或其他 pinned selections
- [x] 3.4 实现普通左键再次点击同一 active selection 时取消选中，并测试 marker、tooltip 和 keyboard target 同时清除且 pinned selections 不受影响
- [x] 3.5 实现普通左键点击 pinned selection 时只移除该钉选点，并测试不在同位置创建 active selection、其他 pinned selections 与已有 active selection 保持不变，tooltip 点击仍可选择和拖动

## 4. 键盘、生命周期与回归

- [x] 4.1 使 Left/Right/Home/End 仅移动最近点击的 active 或 pinned selection 及其 tooltip，并测试 hover 不会改变键盘目标或移动其他标记
- [x] 4.2 更新断开、关闭、面板布局恢复与绘制缓存失效路径，并通过现有幂等性、最大化和 transform cache 回归测试
- [x] 4.3 从仓库根目录运行 `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`，并确认全部单元与交互逻辑测试退出码为 0
- [x] 4.4 从仓库根目录运行 `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py`，确认 hover 冒烟检查完整运行且无异常，不将其结果表述为达到机器无关性能阈值
- [x] 4.5 从仓库根目录运行 `openspec validate --changes`，并确认全部 change 结构校验退出码为 0
- [x] 4.6 使用 `venv/bin/python interactive_plot.py` 在 QtAgg 后端手工验证圆形点击样式、蓝红系列切换、同线选中后 hover、多点钉选、tooltip 拖动和键盘导航，并记录各场景结果
- [x] 4.7 在收尾报告中逐项记录类型检查、Lint/格式、构建、E2E 和安全扫描的通过、失败、未执行或覆盖缺口状态，并验证没有将未配置的检查误报为通过
