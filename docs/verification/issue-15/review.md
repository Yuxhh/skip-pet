# #15 双轴审查

审查基点：用户确认的 `e4df517a0650ce6a2c71405ed7339a08adb9b9b3`。实现快照：`8c622f4 Support native character dragging and transparent input (#15)`。固定命令：`git diff e4df517...HEAD`；`git log e4df517..HEAD --oneline` 在审查时仅包含该实现提交。随后仅补充本审查记录，不改变程序行为。

按 code-review 技能，Standards 与 Spec 由两个独立并行子代理只读审查。标准来源：AGENTS.md、docs/agents/domain.md、docs/agents/issue-tracker.md、GLOSSARY.md、README.md、pyproject.toml；无相关 ADR。既有未提交规划资料不纳入 diff。

## Standards

0 项发现。未发现违反仓库文档规则或值得提出的基线代码异味。输入判断收拢到已确认的应用入口，Qt 保留坐标、平台阈值、原生命中和窗口移动职责；测试通过公开状态验证行为，未依赖 Qt 私有成员。

## Spec

0 项发现。#15 的五项验收要求均有对应实现与证据：拖动/释放不推进阶段，普通点击仍走统一入口；原生轮廓掩码让透明处穿透；真实记事本菜单响应证明跨进程输入，且角色仍置顶；阈值使用 Qt 平台距离和逻辑坐标；应用级自动测试与 Windows 操作记录齐备。未发现范围扩张或错误实现。真实混合 DPI/多屏尚未验证，记录已明确说明，属于 #16。

Standards 0 项，Spec 0 项；两轴均无待修正问题。

## 最终检查

- `python -m mypy src`：6 个源码文件通过。
- `python -m pytest tests/test_pointer.py -q`：8 passed。
- `python -m pytest -q --basetemp=.scratch/issue15-verification/pytest-temp`：40 passed。首次全量运行因缺少临时目录的父目录导致 7 项 fixture 初始化错误；创建 `.scratch/issue15-verification` 后重跑，全量通过，程序代码无需修改。
- `python -m pip check`：No broken requirements found。
- `git diff --check`：本次源码、测试、工具及文档无空白错误。
- `tools/verify_pointer_native.py` + `@oai/sky` 系统鼠标：真实记事本透明角点击/右键、前置后的置顶、角色点击、拖动及释放、角色右键菜单和菜单退出通过；观察进程返回 0。
- `tools/verify_modes_native.py`：三次独立 Windows/Qt 菜单与重启验证返回 0。辅助工具重生成的 #14 图片已恢复，避免修改历史证据。

原生验证详情和图片见 [README.md](README.md)。本次提交只含 #15 实现、测试及文档，保留用户已有未提交修改；未推送。
