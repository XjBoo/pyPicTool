# 图例配置实现验证与独立评审

日期：2026-09-12。实现提供每子图 `legend_loc="best_corner"` 和 `legend_frame_alpha`，保留默认右上角及 0.95 背景不透明度。本报告不表示已执行归档。

## 固定范围

- 基线及 merge-base：`8ce047c600c7955bb156bc51be3798793b39562b`。
- 首轮待审提交：`72912fa6f6fd0d68e117d6267c4ccaf8bc81aafa`。
- 测试修正后待审提交：`b4df9f7357663b19fb3b52514bc5689d9fb37a1c`。
- 首轮范围覆盖全部 12 个变更文件，审查时工作区干净；后续增量仅补强测试。最终报告及任务勾选属于后续文档更新，不包含额外实现修改。
- 独立 Reviewer 为未参与实现、未继承实现会话历史的 `legend_review` 上下文。读取磁盘 proposal、design、delta spec、tasks 和 AGENTS.md 后只读审查；未修改代码或索引。

## 问题验证与处理

首轮 Critical：0，Important：0，Minor：1。

Minor：原 `tests/test_legend_configuration.py:143` 的视图失效测试只验证缓存键非空，不能证明每次视图变化会重新评分；单面板也未实际覆盖多面板放大恢复。依据“视图变化与普通悬停”规格场景及任务 2.3，判定意见成立。

修正在 `b4df9f7`：使用两面板并添加真实右轴数据，分别验证左右轴范围、窗口大小、DPI、放大和恢复之后评分被调用且缓存键更新；新增改变纵轴范围后图例必须从右下移到右上的可观察行为测试。保留普通悬停零重算与完整/局部渲染一致性断言。未发现需要修改实现的缺陷。

## 最终自动化验证

以下命令从仓库根目录执行，测试补强后重新执行最终检查。全部退出码为 0。

| 检查 | 命令 | 结果 |
|---|---|---|
| 图例定向回归 | `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -p test_legend_configuration.py -v` | 10 项通过 |
| 全量单元/交互 | `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v` | 110 项通过，11.301 秒 |
| Hover 冒烟 | `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` | 完整运行无异常；没有机器无关阈值，不声称性能指标达标 |
| OpenSpec | `openspec validate --changes` | 1 项通过，0 失败 |
| 补丁空白检查 | `git diff --check` | 通过，不替代 Lint |

另执行 `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.plot_features --save /tmp/legend-features.png`，退出码 0，验证公开规格入口及示例导出。初轮全量为 109 项通过；最终结论依据补强后的 110 项结果。定向测试中曾有测试夹具错误（非法 NaN 横坐标、没有右轴数据却要求右轴范围改变触发评分），均已修正，最终无失败。

## QtAgg 人工检查

首次在沙箱内执行 `venv/bin/python interactive_plot.py` 因 macOS 窗口服务不可访问而退出 134，未计为通过。获得沙箱外执行权限后，运行 `MPLCONFIGDIR=.mplconfig venv/bin/python interactive_plot.py` 成功打开窗口，并通过 CUA 操作验证默认六子图双击放大与 Esc 恢复；关闭窗口后进程退出 0。

执行 `MPLCONFIGDIR=.mplconfig venv/bin/python -m examples.plot_features`，通过真实窗口鼠标/键盘操作观察：

- 初始双轴图自动图例位于左上，背景不透明度 0.3；下方面板固定右下且背景完全透明。
- 工具栏框选缩放改变坐标范围，自动图例移至左下；平移后移回左上，始终保持角锚定。
- 半透明图例拖到数据上方，仍能看见框后的线段；完全透明图例同样可拖动。
- 双击放大、Esc 恢复及拖动窗口边缘调整大小后，手动图例保持轴相对位置。
- L 进入选线模式，点击半透明图例条目成功高亮整线；Backspace 删除后，图例减少条目，保留手动位置和背景透明度。
- 点击完全透明图例条目同样可以选线；删除最后一条命名曲线后图例消失，Esc 可退出选线模式。
- 上述过程未观察到旧图例残影；Agg 栅格对比另验证普通悬停与完整绘制一致。

GUI 中初次使用 AX 复选框点击只改变按钮状态，未实际执行导航；随后通过屏幕坐标点击工具栏按钮，观察到坐标范围和图例位置变化，才计入缩放/平移通过。

## 覆盖缺口

| 类别 | 状态与限制 |
|---|---|
| 类型检查 | 未执行：mypy 未安装，仓库无已采用命令 |
| Lint/格式检查 | 未执行：Ruff 未安装，仓库无已采用命令 |
| 构建 | 无检查能力：未声明 build-system，无已采用构建命令 |
| 独立 E2E | 无独立套件；自动化交互使用 Agg，本次另做 QtAgg 人工检查 |
| 安全扫描 | 未执行：未配置 secret scan、SAST 或依赖漏洞扫描命令 |

上述缺口不计为通过；本 change 未新增这些工具作为必需验收条件。已知产品限制为四角遮挡数量启发式并不保证视觉遮挡面积全局最优，超大图例不保证完全容纳。

## 最终结论

独立 Reviewer 已复审 `72912fa..b4df9f7`，确认原 Minor 已解决、未发现新增问题：Critical 0、Important 0、Minor 0。最终适用自动化检查及 QtAgg 人工验收完成，12/12 任务完成，满足收尾条件。规格尚未同步到主规格，change 尚未归档。

## Finish run：codex/finish-legend-placement-opacity

- 本轮基线及 merge-base：`8ce047c600c7955bb156bc51be3798793b39562b`。
- 首个固定候选：`137314a55ddcd23770c159507186840e769f9dc6`。
- 分支：`codex/finish-legend-placement-opacity`。
- 首轮工作区及索引干净，无排除的实现修改。正式独立审查覆盖 `8ce047c...137314a`，进入 finding 处置循环 1。

### Finding 处置

| ID | 级别 | 摘要 | 验证 | 处置 |
|---|---|---|---|---|
| F1 | Minor | 第二面板没有实际图例，多面板透明度隔离缺少渲染断言 | Confirmed：规格场景要求两面板经公开构建各自保留透明度，原测试只断言快照值 | Fixed：第二面板增加命名曲线，并断言两个实际 Legend frame 的 alpha |
| F2 | Minor | 自动模式删除后重新评分缺少回归测试 | Confirmed：原删除测试只覆盖固定或手动位置 | Fixed：新增确定性自动角场景，断言重建、自动状态、评分完成及右下到右上的换角 |
| V1 | Important | 自动模式删除曲线后缓存键访问已移除 artist 的空 axes 并崩溃 | Confirmed：公开 `remove_series` 回归先稳定触发 `AttributeError` | Fixed：缓存键遇到 removed record 时记录删除状态后跳过其 artist；原失败测试转为通过 |

F1、F2 均按用户授权自动采用推荐方案；不改变 OpenSpec 行为，不需修改 proposal、design、spec 或 tasks。V1 是修复 F2 测试时发现的规范阻断，实现修复保持既有设计：删除记录不参与候选几何和评分。

### 修复后验证

| 检查 | 结果 | 证据或缺口 |
|---|---|---|
| 单元与 Agg 交互测试 | Pass | `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest discover -s tests -v`，111 项通过，11.676 秒 |
| Hover benchmark | Pass | `PYTHONPATH=. MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python benchmarks/benchmark_hover.py` 完整运行；无机器无关性能阈值 |
| OpenSpec 结构 | Pass | `openspec validate --changes`，1 passed、0 failed |
| OpenSpec 实现核验 | Pass | 12/12 tasks、3 requirements、12 scenarios 均映射到实现与测试，未发现规格或设计分歧 |
| QtAgg 人工检查 | Pass | 本轮执行 `MPLCONFIGDIR=.mplconfig venv/bin/python interactive_plot.py`；验证子图放大/恢复、图例拖动、L 选线、关闭清理，进程退出 0 |
| 类型检查 | Gap | mypy 未安装，仓库无已采用命令 |
| Lint/格式 | Gap | Ruff 未安装，仓库无已采用命令；`git diff --check` 通过但不替代 Lint |
| 构建 | Gap | 无 build-system 或已采用构建命令 |
| 独立 E2E | Gap | 无独立套件；现有自动交互为 Agg，并补充 QtAgg 人工检查 |
| 安全扫描 | Gap | 未配置 secret scan、SAST 或依赖漏洞扫描 |

### 第二轮独立复审

- 修复检查点：`2df83678ff6e19b85f816fa73b03c6833997de99`。
- Review batch：`legend-rereview-2df8367`，完整审查 `8ce047c...2df8367`。
- Reviewer 在 `/private/tmp` 隔离副本撤掉 removed-record 跳过逻辑，F2 测试稳定以 `AttributeError` 失败；当前检查点同一测试通过，确认 V1 回归测试具备 mutation sensitivity。
- Reviewer 独立复跑 111 项测试、hover benchmark、OpenSpec 校验和 `git diff --check`，退出码均为 0。
- 最终批次：Critical 0、Important 0、Minor 0；F1、F2、V1 均为 `Fixed`，没有 Deferred、Accepted risk 或 Unresolved blocker。

## OpenSpec Review Report: configure-legend-placement-opacity

- Base / merge-base：`8ce047c600c7955bb156bc51be3798793b39562b`
- 最终实现检查点：`2df83678ff6e19b85f816fa73b03c6833997de99`
- Review loops：2
- Outcome：Findings dispositioned；最新独立批次 No findings

### Validation

| Check | Result | Evidence or gap |
|---|---|---|
| 单元与交互逻辑 | Pass | 111 tests；主流程 11.676 秒、独立 Reviewer 11.717 秒 |
| Hover 冒烟 | Pass | 两次完整运行无异常；无性能阈值结论 |
| OpenSpec 结构 | Pass | 1 passed、0 failed |
| OpenSpec 实现核验 | Pass | 12/12 tasks、3/3 requirements、12/12 scenarios |
| QtAgg 手工 | Pass | 放大/恢复、图例拖动、L 选线、关闭，进程退出 0 |
| 类型检查 | Gap | mypy 未安装，无采用命令 |
| Lint/格式 | Gap | Ruff 未安装，无采用命令 |
| 构建 | Gap | 无 build-system 或采用命令 |
| 独立 E2E | Gap | 无独立套件；Agg 自动交互 + QtAgg 手工 |
| 安全扫描 | Gap | 未配置扫描命令 |

### Findings and disposition

| ID | Severity | Summary | Validation | Disposition |
|---|---|---|---|---|
| F1 | Minor | 多面板透明度缺少实际图例断言 | Confirmed | Fixed |
| F2 | Minor | 自动图例删除重评分缺少回归 | Confirmed | Fixed |
| V1 | Important | 自动图例删除后访问空 axes 崩溃 | Confirmed，mutation probe | Fixed |

### Changes made

- Code：自动定位缓存跳过已删除记录的 artist，同时把删除状态保留在缓存键中。
- Tests：增加双面板实际图例透明度断言；增加自动图例删除后重建、重评分和换角回归。
- OpenSpec artifacts：规范行为未改变；更新本审查记录。

### Remaining risk

- 保留上述类型检查、Lint、构建、独立 E2E 和安全扫描覆盖缺口。
- best_corner 使用四角遮挡数量启发式，不保证视觉遮挡面积全局最优；超大图例不保证完全容纳。这是已记录的产品边界，不是未解决 finding。

### Archive gate

Completed。主规格已同步，change 已归档至 `openspec/changes/archive/2026-09-12-configure-legend-placement-opacity/`。
