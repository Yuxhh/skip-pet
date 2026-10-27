# 宿傩桌宠 · skip-pet

一个运行在 Windows 桌面上的宿傩角色桌宠。点一下，头颈与眼睛随动作推进；拖到屏幕边缘，它会贴边陪伴。当前开发版还支持宿傩 AI 对话、DeepSeek Harness 任务联动和任务状态气泡。

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
| 默认分支 `main` | 0.2.1 历史基线，包含角色动作、点击回弹、持续跳动、透明命中和贴边 |
| [当前开发分支](https://github.com/xyd-0811/skip-pet/tree/codex/dsh-reference-bridge) | 0.4.0 开发代码，增加 AI 对话、桌宠设置及 DeepSeek Harness 接入 |
| 本机交付 | 0.4.0 已完成作者安装版试聊验收，实际安装版还包含后续菜单和托盘更新；交付文件在本机 `dist/accepted-0.4.0/release/`，不随仓库提供 |

上方功能清单概括当前项目能力，并非全部已合入 `main`。开发分支代码、本机安装包和验收结果的对应关系见 [0.4.0 交付任务 #53](https://github.com/xyd-0811/skip-pet/issues/53)、[菜单更新 #54](https://github.com/xyd-0811/skip-pet/issues/54)和[托盘更新 #55](https://github.com/xyd-0811/skip-pet/issues/55)。

目前未创建 GitHub Release，仓库不提供安装包下载入口。乙骨忧太角色切换与左右交替跳仍在[规划中 #56](https://github.com/xyd-0811/skip-pet/issues/56)。

## 安装与使用

适用于 Windows 10 1809 及更新版本、Windows 11 x64。已有交付安装包的使用者可运行 `Setup.exe`，安装后从开始菜单启动“宿傩桌宠”；安装后无需另装 Python。详细操作见[当前开发版使用说明](https://github.com/xyd-0811/skip-pet/blob/codex/dsh-reference-bridge/docs/user-guide.md)。其中“候选/待试聊”文字是构建阶段记录，后续作者验收结论以 #53 为准。

首次无设置启动时角色静止。单击互动，按住拖动，右键打开菜单；模式和大小会自动保存。角色动作可离线使用，AI 对话和宿主任务接入按需配置。

AI 对话固定使用 `deepseek-flash`，关闭思考。API Key 由使用者提供，优先保存到 Windows 当前用户凭据管理器；连接测试、发送与重试可能产生 API 费用。会话记录保存在本机。

任务联动需要启用 DeepSeek Harness 接入，并具备相应 Node.js / pnpm 工具环境；当前适配验证基于 DeepSeek Harness 0.2.1-rc.2。AI 对话和任务联动是独立功能，桌宠自己的聊天不会触发任务联动跳动。

## 从源码运行

源码要求 Windows x64、Python 3.12+。若要体验 AI 对话与任务联动，请检出开发分支；`main` 仍是 0.2.1 基线。

```powershell
git clone --branch codex/dsh-reference-bridge https://github.com/xyd-0811/skip-pet.git
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

固定构建环境为 x64 CPython 3.14.4，其他 Python 版本的打包未验证。依赖、构建及安装验收步骤见[开发分支构建说明](https://github.com/xyd-0811/skip-pet/blob/codex/dsh-reference-bridge/docs/build.md)。

## 文档与验证范围

- [使用说明](https://github.com/xyd-0811/skip-pet/blob/codex/dsh-reference-bridge/docs/user-guide.md)：聊天、设置、接入及故障恢复。
- [任务状态决策 #33](https://github.com/xyd-0811/skip-pet/issues/33)与[气泡决策 #36](https://github.com/xyd-0811/skip-pet/issues/36)：任务状态与气泡交互的确认记录。
- [0.4.0 验证记录](https://github.com/xyd-0811/skip-pet/blob/codex/dsh-reference-bridge/docs/verification/issue-53/README.md)：自动化、安装版验证与作者试聊流程。
- [GitHub Issues](https://github.com/xyd-0811/skip-pet/issues)：功能规划、规格与验收记录。

真实多屏、负坐标屏、混合 DPI、屏幕插拔及干净无 Python Windows 环境仍有待硬件补验；自动化测试和本机试聊通过不代表这些环境均已实测。

## 素材与参考

素材来源见 [provenance.json](src/sukuna_pet/assets/provenance.json)。桌宠接入与维护参考 [dsh-pet-indesktop](https://github.com/MerZlin/dsh-pet-indesktop)；安装包保留第三方许可，复用范围与许可说明见随包文件。
