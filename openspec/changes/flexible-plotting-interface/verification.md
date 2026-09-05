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

初次在沙箱中启动 `MPLCONFIGDIR=.mplconfig venv/bin/python interactive_plot.py` 因 macOS 窗口服务连接失败退出 134；改用授权的桌面运行环境继续验证。实际交互结果待补充，不以 offscreen 结果代替真实桌面检查。

## 覆盖缺口

- 类型检查：未执行，mypy 未安装，没有已采用命令。
- Lint/格式检查：未执行，Ruff 未安装，没有已采用命令；diff 空白检查不代替 Lint。
- 构建：未执行，无 build-system 和已采用构建命令。
- 独立 E2E 套件：缺少；现有自动化交互主要采用 Agg，Qt 探针为 offscreen。
- 安全扫描：未执行，无已配置 secret scan、SAST、依赖漏洞扫描命令。
- Windows 实机及不同 DPI：未执行，本机 macOS 结果不代表 Windows 验收。

## 独立审查

待固定提交后由未参与实现的 Reviewer 检查规格、兼容性和改动范围。尚不宣布 change 完成，不归档。
