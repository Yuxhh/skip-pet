# 系统托盘与任务栏验证

日期：2026-10-27（Asia/Shanghai）。对应任务：[让桌宠常驻系统托盘并隐藏角色任务栏按钮](https://github.com/xyd-0811/skip-pet/issues/55)。

## 改动

角色窗口使用 `Qt.Tool`，沿用透明、置顶、点击和拖动行为。显式恢复 `WA_QuitOnClose`：Qt 工具窗口默认关闭不结束应用，若忽略这一点会留下没有角色的后台进程。

增加一个以现有角色画面为图标的 `QSystemTrayIcon`，保活托盘对象和菜单。托盘提供显示桌宠、AI 对话、桌宠设置、退出；双击恢复显示。设置和聊天复用已有窗口；AI 对话保持普通窗口。退出继续走现有聊天保存与取消关闭、凭据释放、任务桥清理，真正关闭后移除托盘。

对照本地 dsh-pet 固定提交 `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e` 的 `pet/window.py:179`、`pet/overlay_shell.py:4268` 与 `pet/overlay_shell.py:4434`。采用相同的工具窗口和 Qt 托盘机制；本项目退出继续使用自己的关闭流程。参考工作树干净。

## 自动化和原生证据

- `tests/test_tray.py` 与聊天会话关闭测试：14 passed。
- 托盘、会话保存、设置、AI 对话、模式、V5 桌面、指针、尺寸、贴边、任务桌面、桥接桌面、发布相关回归：124 passed，133.40 秒。记录：`.scratch/tray/regression.xml`、`regression.log`。
- `mypy src`：23 个源文件通过；本次修改文件 `git diff --check` 通过。
- 新测试读取原生 `WS_EX_TOOLWINDOW`/`WS_EX_APPWINDOW`，验证角色跳过任务栏而聊天不是工具窗口；独立进程实际运行 `main()` 事件循环，验证关闭聊天、设置后桌宠继续运行，从托盘退出后事件循环正常结束。
- 聊天写入失败时从托盘发起退出，取消后角色、聊天、凭据和托盘继续可用；保存后再次从托盘退出会移除角色及图标。
- Windows Shell 可用，原生托盘图标已注册，返回矩形 `(1567, 1032, 32, 48)`。隐藏面板与常显区域之间的收纳遵循 Windows 用户设置。

Windows Qt 测试记录仍包含环境中既有的 COM `0x8001010d` 诊断；测试进程返回 0，全部 124 项通过。该诊断不计作程序崩溃或测试失败。

## 构建与当前用户安装

使用锁定的 `.scratch/i28e` CPython 3.14.4 构建环境和 Inno Setup 6.7.3，新产物位于 `dist/issue-55/release/`，没有覆盖既有验收目录。构建脚本校验冻结模块与当前源码一致，保留安装包、源码 ZIP、报告和 SHA-256 清单。本轮基于已有未提交功能和菜单顺序改动继续修改；源码 ZIP 是构建时快照，报告 Git SHA 仅为基点。

通过旧桌宠自己的退出菜单正常关闭，再运行新版 Setup 更新 `C:\Users\xing\AppData\Local\Programs\SukunaPet`，安装器返回 0。安装后的 186 个文件均与 `build-report.json` 一致，无缺失或哈希不符。

安装目录实际执行 `--verify-installation` 返回 0：冻结运行时、合成凭据跨进程读取和清理、会话恢复、未完成标记、偏好兼容、窗口生命周期及 Windows TLS CA 检查通过。结果在 `.scratch/tray/installed-check/result.json`；不访问产品凭据、个人会话或真实计费接口。

已重新启动安装版。原生只读检查确认该安装路径有且仅有一个可见宿傩角色窗口，`WS_EX_TOOLWINDOW=true`、`WS_EX_APPWINDOW=false`，记录在 `.scratch/tray/installed-native.json`。computer-use 的窗口选择器过滤工具窗口，不能据其无法列出窗口推断桌宠未启动；本次用原生样式与可见性核实。未宣称完成托盘隐藏面板的截图验收。

本记录在构建完成后追加，不改变已生成 Setup 和源码 ZIP 的哈希。它不替代原有作者试聊、多屏、混合 DPI 和干净 Windows 验收。
