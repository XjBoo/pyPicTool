# 实施与验证记录

## 范围

- 已确认方案：figure/subplot/plot 描述后一次性 build，不支持构建后追加。
- 分支：`codex/flexible-plotting-interface`。
- 基线：`c69ad1ef5062917a22ab1bc737cc10b96fac7c78`。
- 用户既有 `AGENTS.md` 未提交修改保留，不纳入实现提交和固定代码审查范围；执行仍遵守其当前规则。

## 自动化验证（2026-09-06）

- `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`：退出 0，75 项通过，包含独立 Qt offscreen 工具栏探针。
- `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py`：退出 0，1000/10000 点每系列场景完整运行。仅验证无异常，未设置机器无关性能阈值。
- `openspec validate --changes`：退出 0，1 项通过。
- `git diff --check`：退出 0。
- `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.flexible_plot --save-dir /tmp/flexible-plot-example`：退出 0，生成两张图片并查看。中文总标题、子图标题、图例、轴文字、空/隐藏子图和自定义点形状可见且无重叠。

## 桌面检查

初次在沙箱中启动 `MPLCONFIGDIR=.mplconfig venv/bin/python interactive_plot.py` 因 macOS 窗口服务连接失败退出 134；在授权的桌面运行环境重试后正常启动，关闭后退出 0。

通过 CUA 在 macOS 的真实 QtAgg 窗口执行并观察以下场景：

- 六子图演示：正常打开，默认工具栏收起，双击子图放大，Esc 恢复六子图；鼠标启用 Pan 后收起再展开工具栏，Pan 状态从 1 回到 0；正常关闭。
- `MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.flexible_plot`：显示两个独立窗口。单图的纯折线和 x 形散点、总标题、轴文字与图例正确；点击折线点后出现圆形焦点和 tooltip，Right 将 Frame 1.50 / Value 0.997 移到 Frame 2.00 / Value 0.909；tooltip 和图例均可拖动。
- 关闭第二张图后，第一张图仍可见且响应工具栏展开操作；第一张图显示 2×2 稀疏布局、中文标题和自定义数据点。关闭全部窗口后进程退出 0。
- 上述窗口切换后，CUA 的坐标点击曾报告 `noWindowsAvailable`，但 AX 控件操作仍有响应。未把工具故障视为绘图库失败；使用单独进程打开 2×2 自定义布局补测。
- 单独的 2×2 自定义布局：方形数据点可点击并按 Right 移至下一点；双击含数据的子图放大，保留总标题、选择及 tooltip，Esc 恢复原稀疏布局。空子图同样可双击放大、Esc 恢复，原数据选择保留。正常关闭后退出 0。

桌面未逐项重测 Shift+点击、Delete/Backspace、Home/End、缩放模式及不同 DPI；对应键盘/钉选/工具栏语义由现有 Agg 测试与 Qt offscreen 探针覆盖其适用场景，不宣称全部人工验收或 Windows 验收通过。

## 覆盖缺口

- 类型检查：未执行，mypy 未安装，没有已采用命令。
- Lint/格式检查：未执行，Ruff 未安装，没有已采用命令；diff 空白检查不代替 Lint。
- 构建：未执行，无 build-system 和已采用构建命令。
- 独立 E2E 套件：缺少；现有自动化交互主要采用 Agg，Qt 探针为 offscreen。
- 安全扫描：未执行，无已配置 secret scan、SAST、依赖漏洞扫描命令。
- Windows 实机及不同 DPI：未执行，本机 macOS 结果不代表 Windows 验收。

## 独立审查

独立 Reviewer `/root/review_flexible_plot` 使用不包含实现对话的新上下文，只读审查了全部实现变更及相关交互代码，并重新读取 change 规格。

- 审查范围：merge-base `c69ad1ef5062917a22ab1bc737cc10b96fac7c78` 到 `adba1169b46ed672df1a608320425a6937ddda47`。
- Critical：0；Important：0；Minor：0。未发现有充分证据支持的问题，无需进入代码修复回合。
- Reviewer 独立执行规定测试：75 项通过，退出 0；性能冒烟两组完成，退出 0；OpenSpec 1 项通过，退出 0；固定范围 diff 空白检查退出 0。
- Reviewer 补充逐一构建、Agg 绘制并关闭全部文档支持的 marker，未出现构建失败或遗留 figure。
- 本记录后续提交仅更新任务勾选和验证记录，不改变已审查的代码；不以这些文档更新触发无理由的重复测试。

实现与规定自动化检查、适用桌面场景及独立审查已完成。上述能力缺口保留明确记录；本 change 未将这些缺失工具或 Windows 实机定义为必需验收条件。本次不归档、不合并或推送。

## 收尾审查与修复（2026-09-06，finish-openspec-change 流程）

- 固定范围：merge-base `c69ad1e` 到检查点 `945b99a`，审查时工作区干净，无排除修改。
- 收尾主代理实测：单测 75 项通过（退出 0）、Hover 冒烟完整运行（退出 0）、`openspec validate --changes` 1 项通过（退出 0）。
- 独立 Reviewer（未参与实现的新上下文，只读审查全部实现与规格产物）：Critical 0、Important 0、Minor 8。
- 逐项处置：
  - Minor 8（旧入口 panel_title 推导兼容性存疑）：拒绝。基线 `c69ad1e` core.py:1105-1106 与现实现的 `next((item.panel_title for item in ... if item.panel_title), "")` 表达式一致，无兼容偏差。
  - Minor 1/2/3/5/6/7：成立并修复。linestyle 错误消息列全别名；README 补记 `"none"`/`""`；`plot` 文档注明默认 √10 对应 10 pt² 面积；总标题断言改用公开 `figure.texts`；`_MARKERS` 改为分组字面量；测试补 linestyle 文字别名正测试、显式 `label=""` 未命名行为与图例 handle 线宽/点尺寸断言。
  - Minor 4（`FigureBuilder`/`Subplot` 包级导出以便类型注解）：成立但延后。design.md 明确保持最小公开接口，示例与文档不需要类名；待作为独立库发布或调用方需要类型标注时再评估。
- 修复后全量重跑：单测 75 项通过（退出 0）、Hover 冒烟退出 0、OpenSpec 校验 1 项通过（退出 0）、`git diff --check` 退出 0。
- 覆盖缺口沿用上文记录（mypy/Ruff/构建/E2E/安全扫描/Windows 实机均未配置或未执行），未新增缺口。
- 修复检查点 `27e4f84` 提交后，第二位全新独立 Reviewer 只读复审了完整范围 `c69ad1e...27e4f84`：确认 8 项处置全部闭环（6 项修复逐项找到证据且未引入新问题、1 项延后有 design.md:44 依据、1 项拒绝有表达式与新旧入口等价性测试支撑），未发现新的 Critical/Important/Minor，结论 Ready to archive。复审环境无终端未复跑验证命令，以收尾主代理实测记录印证。
