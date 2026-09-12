# 独立审查与修复记录

首次固定范围：76307de57d998f9319ed652ddb05355ce1f11e7d..61b2cfa2d4e08d01eb2511905466da7e023ffa5c，merge-base 等于基线。Reviewer 使用未参与实现的独立上下文，只读审查了仓库契约及本 change 全部规划、代码与测试。未跟踪的 Qt 双轴观测 JSON 不在首次范围。

## 稳定问题清单

Critical：无。Important：2 项。Minor：无其他确定发现。

1. Important：core.py（首次待审版本）138、168 行，在交互层 draw 内捕获的背景缺少较高 zorder 的 Figure Artist。添加 zorder=20 的 figure.text 后，首次悬停使文字消失。Reviewer 的优化/完整帧相差 10,714 颜色通道；实施方另行复现相差 3,022 通道（文字内容不同）。违反“悬停刷新保持画面一致”。确认成立。
2. Important：core.py（首次待审版本）161、176 行，draw_idle 排队后 disconnect 未取消 Qt 回调。Reviewer 在真实 Qt offscreen 事件循环中复现断开后 canvas.draw 执行 1 次。违反“关闭或断开时仍有刷新待处理”。确认成立。

Review 回合未修改代码。稳定清单形成后进入修复回合，没有接受风险或拒绝问题。

## 修复与相关验证

- I1：检查 Figure 的实际 zorder 顺序，交互层后存在可见 Artist 时回退完整绘制；覆盖相同 zorder 后插入文字及更高 zorder，删除文字后恢复 blit。像素级回归通过。
- I2：交互层使用自身拥有的零间隔、单次 GUI 定时器，合并刷新并直接在回调中 draw；完整绘制和 disconnect 停止定时器。非交互后端保留同步 draw_idle 回退。退出整线模式时不再从 disconnect 排队额外绘制；布局恢复所需绘制在断开返回前同步完成。
- 新增真实 Qt offscreen 子进程测试：排队后 disconnect/close 不执行绘制；同一事件循环前 A/B/C 多次命中只完整绘制一次且显示 C。使用短时 QEventLoop 等待真实定时器，未合成用户桌面输入。定向测试退出码 0。

## 独立执行记录及覆盖缺口

首次 Reviewer 自行执行 98 tests（12.696 秒）、默认 hover benchmark、openspec validate --changes，均退出码 0。类型检查、Lint/格式、构建、独立 E2E、安全扫描均是仓库现有覆盖缺口，不计通过。人工 Qt 由主代理执行，Reviewer 未代称人工验证。

## 最终复审

固定修复范围：61b2cfa2d4e08d01eb2511905466da7e023ffa5c..642a11430f01cd842731814e66031372e784d343；总范围仍以 76307de57d998f9319ed652ddb05355ce1f11e7d 为 merge-base。

原独立 Reviewer 对修复进行只读复审，确认 I1/I2 均可关闭，未发现新增 Critical、Important 或确定的 Minor。独立执行 `MPLBACKEND=Agg MPLCONFIGDIR=.mplconfig venv/bin/python -m unittest tests.test_hover_rendering tests.test_hover_qt_lifecycle -v`，10 项通过，退出码 0。

主代理修复后完整运行 100 tests、默认 benchmark 和 OpenSpec 校验，均通过；Reviewer 未重复全套。证据文档与 Qt 观测数据的最终追加不在该代码审查范围内，不构成新增实现代码。代码审查阻断已解除，最终 GUI 确认见 verification.md。

最终人工验收已收到用户“表现正常的”确认，详情见 verification.md；两项审查问题均关闭，必需验收已完成，14/14 项任务完成。未执行归档或合并。
