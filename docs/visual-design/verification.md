# 视觉改造验证记录

日期：2026-09-05。变更：`refine-plot-visual-design`。

## 视觉结果

- [改造前](before.png) / [改造后](after.png)：相同 seed=42，12×10 英寸，120 dpi，六面板输入数组逐项相等。
- [选中提示框](selected.png)、[放大面板](maximized.png)、[单面板](single.png)：已打开检查，当前示例文字无重叠，圆形金色焦点与数据清晰可辨。
- tooltip 保留原有偏移与拖动机制；靠边或峰值处可能跨出面板，可拖至空白位置。本次没有增加自动避让算法。

## 自动化检查

| 检查 | 本轮结果 |
| --- | --- |
| `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` | 通过（首轮 61 项；后续轮次见下文各节，当前为 63 项），退出码 0 |
| `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` | 通过，退出码 0；每系列 1,000/10,000 点均完成，无性能阈值，不宣称性能指标达标 |
| `openspec validate --changes` | 通过，1 项，退出码 0 |
| `git diff --check` | 通过，退出码 0；不等同 Lint |
| 类型检查 | 覆盖缺口：有 mypy 配置，无已采用命令/安装工具 |
| Lint/格式 | 覆盖缺口：有 Ruff 配置，无已采用命令/安装工具 |
| 构建 | 覆盖缺口：无 build-system 或已采用构建命令 |
| E2E | 覆盖缺口：无独立套件；自动化交互使用 Agg |
| 安全扫描 | 覆盖缺口：无 secret scan、SAST、依赖漏洞扫描命令 |

新增检查覆盖显式样式保留、数据缺失断线、图例颜色、字体缺失回退、动态创建 tooltip、全局 rcParams 隔离、150 dpi 命中和键盘移动、标题/图例边界、放大恢复。原有 57 项测试全部保留。首轮发现左侧标题导致 `get_title()` 为空，已通过保留原标题对象修复，最终完整检查通过。

## macOS QtAgg 实际窗口

运行命令：`venv/bin/python interactive_plot.py`。
沙箱内首次启动因无法连接 macOS 窗口服务退出 134；沙箱外重试成功，完成下列操作后关闭，进程退出 0。使用实际 CUA 鼠标键盘操作及窗口截图观察：

| 场景 | 结果 |
| --- | --- |
| 启动、六面板显示、窗口缩窄 | 通过，标题和刻度可读 |
| 普通点击数据点 | 通过，出现圆形金边和 Frame/Value |
| Right、Left、Home、End | 通过，观察到 Frame 41、99、0 等变化 |
| tooltip 拖动 | 通过，文字框位置与连接箭头更新 |
| 整块图例拖动 | 通过，从右上拖至右下 |
| 双击背景、Esc 恢复 | 通过，放大单面板后恢复六面板，保留选中及拖动位置 |
| 工具栏 pan/zoom | 通过，坐标范围随拖动/矩形选区变化 |
| pan 模式下 Home | 通过，不重置平移后的视图 |
| 关闭窗口 | 通过，脚本退出 0 |
| 独立悬停、Shift+点击钉选、Delete/Backspace、未放大时 Esc 清除钉选 | GUI 未执行：当前 CUA 接口未提供独立鼠标移动或按住修饰键点击操作；对应 Agg 自动化检查通过，但不等同真实 GUI 验收 |

CUA 的 AX 复选框动作可能只改变 Qt 工具栏按钮勾选外观，验证工具栏实际行为使用坐标点击。双击使用连续两次实际点击确认，未将无效果的 clickCount 调用记为通过。

## Windows

未在 Windows 实机执行。实现不引入新依赖、平台专属字体路径或窗口 API；README 提供启动方式及中文字体、100%/150%/200% 显示缩放验收清单。macOS/Agg 结果不能证明 Windows 实机通过。

## 评审范围与收尾状态

基线提交：`1089e2aa867a6d35bb04a030684318f4b5ca6d02`。待审提交在独立评审记录中固定，并使用与该基线的 merge-base。本轮初始工作区仅存在上一轮创建的 OpenSpec 未跟踪方案，无其他用户代码修改。

代码和自动化验证已就绪；剩余真实 GUI 场景未全部完成前，不宣布 OpenSpec change 全部验收通过或允许归档。本次不自动归档。

## 独立评审与修复

初审范围：`1089e2aa867a6d35bb04a030684318f4b5ca6d02..2042eacb5d3de518a418967804321353e83189d9`，独立 Reviewer 未参与实现，读取全部规格并重跑 60 项测试、benchmark、OpenSpec，均退出 0。

- Critical：无。
- Important 代码问题：tooltip 新增 zorder=10 高于图例默认 5，但事件仍优先命中图例，重叠拖动目标与可见层级不一致。实现 Agent 独立复现双方同时命中且只开始拖图例，确认成立。
- 修复：tooltip 改为 zorder=4，位于曲线/散点之上、图例之下，保留既有事件优先级。新增重叠回归先在旧代码失败（10 不小于 5），修复后通过。重新运行完整 61 项测试、benchmark、OpenSpec 及 diff 检查，全部退出 0。
- Minor：无。
- Important 未完成验收：2.3 中的部分真实 GUI 场景未执行，属于验证缺口，不能以 Agg 代替，也未视作解决。任务 3.3 因该门槛仍未完成。
- 本机额外中文渲染检查通过：DejaVu Sans + Arial Unicode MS，中文标题及负数渲染无缺字警告；不等同 Windows 实测。

修复后独立复查的固定提交和结论见后续记录。

### 复查发现的测试隔离问题

复查范围 `2042eacb5d3de518a418967804321353e83189d9..d80f9a5c0a5d7bd3a6317fbf268c73fdb807dd90`。Reviewer 确认层级修复及重叠回归通过，但单独运行 `tests.test_visual_presentation` 时发现字体测试清空整个字体表，依赖先前测试填充的字体缓存；其复查最终报告因使用额度中断，不能视为完整批准。

实现 Agent 单独运行复现失败后修正测试：仅保留自带 DejaVu Sans，模拟可选系统字体缺失；同时将 rcParams 基线改为深拷贝，避免键位列表被原地修改污染预期值。后一个问题在修正字体夹具后单模块运行直接暴露。两项均属测试隔离缺陷，不是绘图运行时修改。修正后独立进程运行该模块 4 项通过（退出码 0）；完整检查重新执行并记录最终结果。

### 最终独立复查结论

最终复查固定范围：`2042eacb5d3de518a418967804321353e83189d9..387a7040416521804b10241790472eb202da0eeb`，整体原始基线仍为 `1089e2aa867a6d35bb04a030684318f4b5ca6d02`。复查时工作区干净。

独立 Reviewer 确认 tooltip 层级问题和测试隔离问题均已解决；未发现新增 Critical、Important 或 Minor 代码问题。其本轮实际执行：视觉模块 4 项、完整 61 项、benchmark、OpenSpec 1 项及固定范围 diff 检查，全部退出 0。类型/Lint/构建/E2E/安全扫描仍按上表列为覆盖缺口。

代码可作为已实现版本交付。剩余真实 GUI 场景未验收，任务 2.3、3.3 保持未完成，OpenSpec 进度 9/11；Windows 实机验证仍未执行，不允许归档。本节为复查后追加的记录文档，不属于上述已审代码范围，未再次改动运行代码或测试。

### 用户试用后的紧凑布局调整

用户反馈整体满意，要求扩大数据绘图区并移除标题序号。本次在相同 seed=42、12×10 英寸下，标题由 12 pt/13 pt 间距改为 10 pt/6 pt 间距；收紧外边距、面板间距及轴标签/刻度间距。默认演示标题改为 Signal comparison，调用者自定义标题不做字符串删除。

单面板归一化面积从 0.08570625 增至 0.11387468，约增加 32.9%；六面板总绘图区占画布由 51.4% 增至 68.3%。已查看默认、选中与单面板图，更新 after/selected/maximized/single 图片。标题和实际范围内的刻度/轴标签边界检查通过；初次诊断误把轴范围外不参与绘制的 -20/120 刻度纳入，修正检查范围后通过，未改变刻度逻辑。

本轮实际完整 unittest 61 项、Hover benchmark、OpenSpec 结构校验及 git diff --check 均退出 0。没有新增交互处理、字体依赖或平台调用；本轮未重跑 Qt GUI/Windows 实机检查，既有覆盖缺口不变。前述独立复查仅覆盖其固定提交，不包含本次布局微调。OpenSpec 追加任务 4.1/4.2 已完成，整体 11/13，2.3/3.3 保持未完成，不归档。

### 二次反馈：适度恢复留白

按用户反馈，标题改为 11 pt、标题间距 9 pt，tight_layout 外边距 1.4、行列间距 1.7，刻度间距 4 pt、轴标签间距 5 pt；保留无序号标题。固定 seed=42、12×10 英寸的单面板面积为 0.10103719，比初版增加约 17.9%，介于前两版之间。已查看更新后的六面板渲染，更新全部当前效果图。

本轮完整 unittest 61 项、Hover benchmark、OpenSpec 校验均退出 0。仅调整静态样式参数，未变更交互逻辑；GUI/Windows 未在本轮重新执行，既有缺口仍保留，前述独立评审范围不覆盖本轮微调。本次追加任务 4.3 完成，整体 12/14，未归档。

### 工具栏默认隐藏

本轮加入 Qt 原生右上角“工具栏”按钮：默认隐藏原生导航栏，点击展开/收起，收起时解除 pan/zoom。按钮由画布拥有，随 resize 定位，不绘入导出图片；Agg 不加载此 Qt 控件。README 和 OpenSpec 规格、设计已同步。

本轮完整 unittest 62 项通过（退出 0，含独立子进程的 Qt offscreen probe）；Hover benchmark、OpenSpec 校验及 diff 检查通过。Qt probe 验证初始隐藏、展开/收起、pan/zoom 退出、widgetlock 释放、视图和选中保留、键盘移动、放大恢复、resize、导出及重复 close。类型/Lint/构建/独立E2E/安全扫描仍为既有覆盖缺口。

实际运行 `venv/bin/python interactive_plot.py` 启动了新窗口；CUA 按应用名及路径定位时返回另一个已存在的旧 Python 绘图进程（无新按钮），未对旧窗口执行操作。因此本轮真实鼠标展开/收起未验收，Qt offscreen 结果不冒充实机通过；Windows 亦未实测。任务 5.2 保留未完成，既有 2.3/3.3 状态不变，不归档。

工具栏独立评审范围：`3672c6f6a17f56127214f213f233006d1bed493a..333700849204b48a52b6c510bb77c1942f0cfdc0`，评审时工作区干净。Reviewer 未发现 Critical/Important 代码缺陷；其完整 62 项测试、独立 Qt probe、额外 Agg 未加载 Qt 检查、benchmark 和 OpenSpec 均通过。Minor 指出直接注入 Matplotlib 键盘事件不能证明 Qt 焦点，已核实成立并在收起后的 Qt probe 增加 `canvas.hasFocus()` 断言；相关检查及完整 62 项、benchmark、OpenSpec、diff 检查再次通过。该后续改动仅为测试断言与记录，不修改运行代码。已另外查看 offscreen 原生窗口在收起/展开时的渲染，按钮位于右上角；此渲染不替代真实桌面验收，5.2 的 GUI 部分仍保留未完成。

### 主线收尾评审（main...pic-opt）

本轮以 `main`（merge-base `1089e2aa867a6d35bb04a030684318f4b5ca6d02`）到 `eedb50fff2a1c2d2db542b50fe7a6fd0ded7c947` 的完整分支范围为固定范围执行收尾评审；评审时工作树干净。本轮实际执行：完整 62 项 unittest、Hover 冒烟、OpenSpec 校验，均退出 0；类型/Lint/构建/E2E/安全扫描仍为既有覆盖缺口。

独立 Reviewer（未参与实现，只读）重读全部规格工件与运行代码，核实 `toolbar.mode` 枚举用法、Qt 对象保活链、Agg 不加载 Qt、close 幂等、figsize、zorder 优先级与字体回退等关键点。结论：无 Critical、无 Important；确认 7 项 Minor（M1 ToolbarToggle 保活注释/显式引用、M2 probe 缺直接收起路径与钉选断言、M3 Agg 不加载 Qt 缺持久回归、M4 标题断言仅查非空、M5 probe 子进程未固定 MPLCONFIGDIR 且 timeout 偏紧、M6 qt_toolbar 无类型注解、M7 按钮/图例遮挡并入 5.2 清单）。逐项核实均成立，无误报；用户选择全部修复。

修复 M1–M6：qt_toolbar.py 显式持有 `canvas._toolbar_toggle` 引用并注明保活链、补全类型注解（M1/M6，行为等价）；probe 增加 Shift 钉选保留断言与“展开后未启用 pan/zoom 直接收起”路径（M2）；test_visual_presentation.py 新增 Agg 会话不加载 `matplotlib.backends.qt_compat` 的持久回归并将标题断言改为逐字相等（M3/M4）；test_qt_toolbar.py 子进程固定仓库 MPLCONFIGDIR、timeout 放宽至 120 s（M5）；M7 写入任务 5.2 验收清单。修复后完整 63 项测试（含扩展 probe 子进程）、Hover 冒烟及 OpenSpec 校验重跑均退出 0。任务 2.3/3.3/5.2 的真实 GUI 与 Windows 实机缺口保持未完成，不归档；修复提交后由新的独立 Reviewer 复审完整范围。

### 复审闭环与第二轮 Minor

复审（固定范围 `1089e2a..47ff35b`）确认 M1–M7 七项全部闭环，无新增 Critical/Important，另确认 2 项 Minor：N1 保活注释表述问题、N2 install 幂等防护缺失。两轮 Reviewer 对 PySide6 信号连接保活语义表述相反，本轮以实验裁决：PySide6 中连接到信号后 `del` 接收者并 `gc.collect()`，weakref 显示对象已被回收——信号连接不保活 Python 接收者，N1 成立（第一轮对 M1 机制的"信号连接保活"解释证伪，显式引用修复因此必要），N2 成立（防御性）。用户授权修复：qt_toolbar.py 改写保活注释为经实验验证的准确表述，并增加 `getattr(canvas, "_toolbar_toggle", None) is not None` 幂等短路；运行行为不变。修复后完整 63 项测试、Hover 冒烟、OpenSpec 校验及 `git diff --check` 重跑均退出 0。任务 2.3/3.3/5.2 的真实 GUI 与 Windows 实机缺口保持未完成，不归档。

第三轮复审确认 N1/N2 闭环，无新增 Critical/Important；其指出的记录措辞问题（机制名 hasattr→getattr、顶部表格轮次标注）已照其修复方向订正，无代码改动。剩余可选后续事项：为幂等短路路径增加 probe 回归断言（Minor-2，可选加固，不影响闭环判定）。

### 用户验收与归档决定（2026-09-05）

- 真实 GUI 人工验收：用户在真实桌面环境完成 `venv/bin/python interactive_plot.py` 的人工验收，声明通过，覆盖任务 2.3 与 5.2 的 GUI 部分（含工具栏展开/收起与图例遮挡检查）。本记录按用户声明登记，此前 CUA 记录中未覆盖的场景以用户本次验收为准。
- Windows 实机验收：用户决定延后统一执行，本轮明确不作为归档前置条件。design.md 已声明真实 Windows 检查不是本地实现完成的必需门槛；README 与本记录保留"未实测、不得声称 Windows 通过"的边界声明。
- 归档决定：用户确认归档 `refine-plot-visual-design`，delta specs（新增 plot-visual-presentation capability）按默认流程同步至主 specs。最终 checkpoint：`7336dadd70d0e74e7d0aba729103adca977e617a`。
