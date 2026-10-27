# 宿傩桌宠 · skip-pet 0.4.2

一个运行在 Windows 桌面上的宿傩角色桌宠。点一下，头颈与眼睛随动作推进；拖到屏幕边缘，它会贴边陪伴。支持宿傩 AI 对话、DeepSeek Harness 任务联动和任务状态气泡。0.4.2 修复菜单打开 AI 对话窗口的时序问题，并保留 0.4.1 的 DeepSeek 接入修复。

## 可以做什么

- **点击互动**：每次点击推进一个视线阶段，到位后停留，同时触发整体回弹；连续点击可接续循环。
- **三种跳动模式**：点击跳动、持续跳动、任务联动。任务联动时，已确认仍在执行的任务让角色持续跳动，只剩等待人工操作时停止自动跳动。
- **桌面陪伴**：透明置顶、透明区域点击穿透、拖动与贴边，支持 188 / 271 / 320px 三档大小。
- **宿傩 AI 对话**：使用自己的 DeepSeek API Key 聊天，支持流式回复、停止、重试，以及保存在本机的多会话记录。
- **任务状态气泡**：接入 DeepSeek Harness，显示已确认的运行、等待批准、等待回答及任务结束状态。
- **设置与托盘**：集中调整桌宠偏好和 AI 接入，通过系统托盘打开聊天、设置或恢复显示桌宠。

## 版本与获取

截至 2026-10-27：

| 位置 | 状态 |
| --- | --- |
| 默认分支 `main` | 0.4.2 正式源码，包含 AI 对话菜单修复、系统托盘、任务联动和接入修复 |
| [发布标签 v0.4.2](https://github.com/xyd-0811/skip-pet/tree/v0.4.2) | 与本次安装包对应的源码版本 |
| [GitHub Release 0.4.2](https://github.com/xyd-0811/skip-pet/releases/tag/v0.4.2) | Setup.exe、对应源码 ZIP、构建报告和 SHA256SUMS.txt |

本版保留此前已验收的功能，代码与本次安装包对应。历史验收记录见 [0.4.0 交付任务 #53](https://github.com/xyd-0811/skip-pet/issues/53)、[菜单更新 #54](https://github.com/xyd-0811/skip-pet/issues/54)和[托盘更新 #55](https://github.com/xyd-0811/skip-pet/issues/55)。

从 [Releases](https://github.com/xyd-0811/skip-pet/releases/tag/v0.4.2) 下载 Setup.exe，可直接升级并保留设置和聊天记录。本版将桌宠右键和托盘菜单中的 AI 对话改为在菜单关闭后打开并激活窗口，验证记录见[菜单修复 #62](docs/verification/issue-62/README.md)。[接入修复 #61](https://github.com/xyd-0811/skip-pet/issues/61)已通过真实任务验收；升级后正常重开 DeepSeek Harness，并选择任务联动。乙骨忧太角色切换与左右交替跳仍在[规划中 #56](https://github.com/xyd-0811/skip-pet/issues/56)。

## 安装与使用

适用于 Windows 10 1809 及更新版本、Windows 11 x64。运行发布页提供的 `Setup.exe`，安装后从开始菜单启动“宿傩桌宠”；安装后无需另装 Python。详细操作见[使用说明](docs/user-guide.md)，验证范围见[发布说明](docs/release-status.md)。

首次无设置启动时角色静止。单击互动，按住拖动，右键打开菜单；模式和大小会自动保存。角色动作可离线使用，AI 对话和宿主任务接入按需配置。

AI 对话固定使用 `deepseek-flash`，关闭思考。API Key 由使用者提供，优先保存到 Windows 当前用户凭据管理器；连接测试、发送与重试可能产生 API 费用。会话记录保存在本机。

任务联动需要启用 DeepSeek Harness 接入；0.4.1 会自动发现 DeepSeek 自带的 Node.js / pnpm 工具，无需依赖开发终端 PATH。当前适配验证基于 DeepSeek Harness 0.2.1-rc.2。AI 对话和任务联动是独立功能，桌宠自己的聊天不会触发任务联动跳动。

## 从源码运行

源码要求 Windows x64、Python 3.12+。默认分支已包含 0.4.2；重建本次发布时可检出标签 v0.4.2。

```powershell
git clone https://github.com/xyd-0811/skip-pet.git
cd skip-pet
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\pythonw.exe -m sukuna_pet
```

开发验证：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mypy src tools/build_release.py
.\.venv\Scripts\python.exe -m pytest -q
```

固定构建环境为 x64 CPython 3.14.4，其他 Python 版本的打包未验证。依赖、构建及安装验收步骤见[构建说明](docs/build.md)。

## 文档与验证范围

- [使用说明](docs/user-guide.md)：聊天、设置、接入及故障恢复。
- [任务状态决策 #33](https://github.com/xyd-0811/skip-pet/issues/33)与[气泡决策 #36](https://github.com/xyd-0811/skip-pet/issues/36)：任务状态与气泡交互的确认记录。
- [AI 对话验收](docs/verification/issue-53/README.md)与[接入修复验收](docs/verification/issue-61/README.md)：自动化、安装版验证与作者试聊流程。
- [GitHub Issues](https://github.com/xyd-0811/skip-pet/issues)：功能规划、规格与验收记录。

真实多屏、负坐标屏、混合 DPI、屏幕插拔及干净无 Python Windows 环境仍有待硬件补验；自动化测试和本机试聊通过不代表这些环境均已实测。

## 素材与参考

素材来源见 [provenance.json](src/sukuna_pet/assets/provenance.json)。桌宠接入与维护参考 [dsh-pet-indesktop](https://github.com/MerZlin/dsh-pet-indesktop)；安装包保留第三方许可，复用范围与许可说明见随包文件。
