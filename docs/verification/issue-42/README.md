# 正式安装版与实机验收：0.3.0 候选

## 用户验收收口

2026-10-26，用户在安装并试用本版后明确确认：“我觉得可以关闭了，这个版本已经符合我的要求了”。据此按当前交付和已验证能力验收 #42，关闭为 completed。这一范围确认取代本文此前“整票仍未完成”“#42 保持开放”的阶段性结论；原始目标及实测边界继续作为历史记录保留。

本次接受 0.3.0 安装版、日常宿主问题等待/回答/完成、原生鼠标操作、升级维护/共享卸载/重装及已通过的自动化结果。多屏、混合 DPI、完整安装版状态与气泡矩阵、干净机器等未验场景以及 #41 已接受的状态覆盖限制，未改记为全部实现或实测通过，后续按实际需要处理，不再阻止本票关闭。

本次仅同步用户验收和任务状态，运行代码未变。已交付的 Setup、源码 ZIP、构建报告及哈希清单保持原样，以下记录及包内验收说明反映构建当时的候选状态；本节是后续有效的用户验收结论。

关闭依据已同步至 [GitHub 用户验收结论](https://github.com/xyd-0811/skip-pet/issues/42#issuecomment-6417632173)。

## 构建与实测记录（验收前）

2026-10-26（Asia/Shanghai）。对应 [正式安装版与实机验收 #42](https://github.com/xyd-0811/skip-pet/issues/42)。本轮已构建并在本机升级、卸载、重装 0.3.0，真实日常宿主的问题等待链路通过；整票仍未完成，不宣称全部发布门槛通过。

## 交付与实现

- 新候选在 `dist/issue-42/release/`：`Setup.exe`、`sukuna-pet-0.3.0-source.zip`、`build-report.json`、`SHA256SUMS.txt`；目录包在 `dist/issue-42/app/SukunaPet/`。旧 `dist/release/Setup.exe` 未覆盖，其 SHA-256 仍为 `35b37f84dfd86df7f020b3fe2de6238f1d6d30eef14e30a1f4b83370953d9ba9`。
- Setup 版本 **0.3.0**，随包桥 **0.3.2**，协议 schema **1**；目标实测宿主 **DeepSeek Harness 0.2.1-rc.2**。Setup SHA-256 为 `cff4416faacd412447723b476827fdc8255afb7fad4d6a370f6b6c7705485107`，最终源码与报告哈希以交付目录清单为准。
- 复用 #39/#40 和用户已接受关闭的 #41；未重做联动和气泡。既有工作区中已确认的气泡缩放、圆角改动一并进入本次构建，不将其冒称为本票新开发。
- 构建命令增加 `--output-root`，候选与旧发行隔离。资源明确从本次 `src` 收集，避开旧构建环境的 editable 安装；编译 Setup 前逐文件校验插件清单及许可与源码一致，报告保留桥版本及六个文件哈希。
- [冻结代码核对](frozen-code.json)：PyInstaller 内 **12 个应用模块**的代码对象均与本次源码编译结果相等，包括气泡、监测和维护；[核对脚本](verify_frozen_code.py)可复跑。构建环境中旧应用的 distribution metadata 不作为本次应用版本来源，版本取自 pyproject.toml。
- 对应源码 ZIP 是工作区文件快照，包含既有未提交相关改动；报告的 `source_base_commit` 是基点，不宣称 ZIP 等于该提交。开发者原有其他改动未混入本票 Git 提交。
- 使用、外部 Node/pnpm 前置、诊断、配置备份和共享卸载恢复说明随安装提供；Qt、Python 等许可和桥插件 MIT 许可均在包内。Setup 未签名。

## 自动化与本机安装证据

用户已确认测试边界为发行构建命令/产物清单，以及安装后启动/插件维护公开入口。新增测试先失败后通过，验证错误编译器不写候选或触碰旧包、缺失宿主适配文件的 bundle 拒绝发行。

| 检查 | 实际结果 | 证据类别 |
| --- | --- | --- |
| 最终完整回归 | **267 passed，184.30 秒**；[pytest.txt](pytest.txt) | Qt offscreen、真实测试文件及独立 profile；不是实机交互证明 |
| 类型检查 | src 与构建脚本共 **14 文件通过**；[mypy.txt](mypy.txt) | 静态 |
| Node 两套 harness | 文件、健康、问题、并发工具、结束、隐私、身份、轮转及重载验证通过 | 真实插件，宿主事件替身 |
| 打包 | CPython 3.14.4、锁定依赖及素材检查、pip check、PyInstaller 和 Inno Setup 6.7.3 编译成功 | 本机发行工具链 |
| 0.2.1 → 0.3.0 升级 | 实际用户安装目录，退出码 0；原 `click/188px` 偏好保持不变 | 真实安装器、注册表、文件系统 |
| 独立启动 | 从 System32 启动；PYTHONHOME/PYTHONPATH 指向不存在路径，窗口正常；Python/Qt DLL 均在安装目录 | 真实冻结进程；原源码目录仍在磁盘，不能代替物理不可用/干净机器验收 |
| 实际 profile 接入 | GUI 预检/确认，备份配置，插件链接转到安装目录，启用仅在成功后持久化 | 真实 `~/.dsh/profiles/desktop`，本机 Node 与既有 pnpm |
| 路径刷新与双实例 | 第二个独立副本启动后自动刷新到新路径；两实例共用同一 profile | 真实冻结进程与维护 |
| 共享卸载 | 主安装实例退出，第二实例仍占用；实际 uninstaller 退出 0，程序文件移除，插件迁到独立数据目录 | 真实 Inno 卸载与存活占用 |
| 最后占用清理、重装 | 第二实例退出后，冻结程序正式清理入口移除本项目依赖及 bundle；Setup 重装退出 0，保留合法模式/大小；重新确认后启用成功 | 真实维护与安装 |
| 安装文件一致性 | 重装目录 **174 个文件**与构建目录哈希相等 | 本机文件系统 |

安装分阶段事实见 [installation.json](installation.json)。其他插件配置在共享迁移前后及最终恢复后完全一致；最后移除时 pnpm 暂时省略空的 `dependencies` 对象，重新启用后恢复原结构，无其他字段差异。未删除其他插件或整份恢复旧配置。

首次原生 Qt 全量运行在 test_edges 遇到 `0x8001010d` COM 异常而中止；不能记为通过。隔离为 offscreen 后曾有 266 项通过、1 项新增测试因 UTF-8 子进程/GBK 父进程解码失败；测试改为检查原始字节后，最终完整 267 项通过。原始记录在本机 `.scratch/issue42/`，最终结果如上。

## 本次真实宿主与原生桌面

用户正常重开原日常桌面实例，PID **108940**，宿主 0.2.1-rc.2、插件 0.3.2、同一 boot `8fce8d93-7e29-48cc-bed7-3b846b25aed0`。已安装桌宠 PID **40396**，任务联动模式，188px；未用另一宿主或 CLI 替代。用户先确认“正在等待”，后确认回答并“已完成”。

| 本地时间 | 真实文件桥事实 |
| --- | --- |
| 21:17:53.856 | 额外只读消费者首次为未知，不显示文字、不跳动 |
| 21:17:54.373 | 健康增长后 waiting=1、questions=1、running=0、jump=false |
| 21:19:42.239 | 回答后当前事实 running=1、waiting=0、jump=true |
| 21:19:43.539 | 本轮 completed=1，运行/等待归零 |
| 21:19:51.412 | 结束提示归零，文字为空；首次完成采样至隐藏采样约 **7.873 秒** |

[live-installed.json](live-installed.json) 只保存版本、代际、健康、计数和固定台词，不保存正文、问题、答案、命令或凭据。上表的时序来自额外只读 BridgeReader，不是向安装进程注入诊断；首次采样间隔不能当作精确 GUI 显示时长。

安装版的原生可访问树与截图另存于 [waiting-ui.json](installed/waiting-ui.json)、[等待气泡](installed/waiting-1.png)：显示“话说清楚，小鬼。等你回答。”；任务结束后原生气泡隐藏。运行与完成期间没有逐帧捕获安装进程气泡，不能把额外消费者台词冒称该进程各帧截图。完整时长、并发和异常分支还需补验。

实际鼠标验收：单击后推进并停留；[原生拖动](installed/drag.json)使窗口 y=811→696；通过菜单切换持续跳动和任务联动，并从原有 188px 切换 [271px](installed/size-271.png)、[320px](installed/size-320.png) 后恢复 [188px/任务联动](installed/final-188-task.png)，持久化结果与菜单一致。重装后 GUI [接入预检](installed/re-enable-plan.json)确认 profile/工具/随包路径，实际鼠标确认安装成功。当前保留安装版、启用接入、任务联动和 188px。

## 尚未通过，#42 保持开放

| 门槛 | 本次边界与后续操作 |
| --- | --- |
| 多屏、负坐标、混合 DPI、连接变化 | 当前缺对应硬件；需在真实多屏上双向拖动、播放/缩放、各屏贴边、拔插及工作区变化，逐项记录。未通过 |
| 安装版完整宿主状态矩阵 | 本轮仅真实问题等待/回答/完成；普通审批拒绝、失败、中断、真实子代理并发及断线/重载的完整安装版矩阵未通过。#41 源码历史证据继续保留，不移花接木 |
| 气泡完整桌面矩阵 | 等待气泡原生显示已确认；短→长→短尺寸、角外透明的像素核对、实际输入穿透、四边/四角避让与快速连点残影的安装版矩阵仍未完成。既有 Qt/源码及 0.2.1 记录不能代替 |
| 独立机器与路径不可用 | 本机独立冻结运行已通过；无 Python 的干净 Windows 10/11、原源码目录物理不可用仍未通过 |
| 全部维护故障分支 | 正常升级/刷新/共享卸载/重装通过；缺 Node/pnpm、依赖失败、部分 profile 成功及坏权限等安装版故障分支未全部现场覆盖，自动化结果单独列明 |

#41 已按用户接受的日常能力收口；嵌套外层执行、跨轮多个 continued、其他 provider 归属等保留限制，不重新加入上游回复前置，也不将其改记为全部实现。没有新增延期的接入能力说明或扩展本次发布范围。

## 复现入口

在锁定构建环境执行（源码 ZIP 解压后同样可用）：

```powershell
python tools/build_release.py --iscc 'C:\path\to\ISCC.exe' --output-root dist/issue-42
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:QT_QPA_PLATFORM = 'offscreen'
python -m pytest -q --basetemp=.scratch/issue42-qa
python -m mypy src tools/build_release.py
node tests/bridge_harness.mjs .scratch/issue42-node-core
node tests/bridge_transport_harness.mjs .scratch/issue42-node-transport
python docs/verification/issue-42/verify_frozen_code.py dist/issue-42/app/SukunaPet --output frozen-code.json
```

真实安装和卸载需使用 Setup/Windows 安装入口，分别记录注册版本、进程路径、偏好、profile 自有条目及无关配置比较。宿主事实由用户在日常桌面入口触发；纯模拟测试不得替代上述未完成项。

## 早先前置检查

## 实际硬件

通过既有 `tools/verify_screens_native.py --output .scratch/issue42-preflight/screens` 只读枚举，Qt 平台为真实 `windows`。环境详情见 [environment.json](environment.json)。当前仅连接 G24H1 一台屏幕，1920×1080、工作区 1920×1032、DPR 1.0、逻辑 DPI 96。

当前环境不能提供真实多屏、负坐标屏、混合 DPI 和屏幕连接变化的完整验收证据。这些场景保持未通过；单屏枚举不接受任何交互场景，也不等于气泡或正式安装版验证。

## 构建环境

日常 `.venv` 缺少构建依赖 altgraph，随后复用此前发行的独立锁定环境 `.scratch/i28e`，未改动日常环境。该环境运行当前 `tools.build_release.check_inputs()` 成功，CPython 3.14.4、全部锁定依赖和冻结素材哈希均通过；`pip check` 无损坏依赖。Inno Setup 6.7.3 的 ISCC.exe 签名 Valid，发布者 Pyrsys B.V.。

依赖文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| requirements.txt | e3d0fc3556cbae7c96df3a22627a9f8f26c0f93fe3048ed8c720880cc344d03e |
| requirements-dev.txt | 931821290bf9d86046e441dbbc1ac1eb1f3f4b064d593fad0cd7665165cf3ea7 |
| requirements-build.txt | 752f27cdf6ba316735c31787f37a183f53525ff39d2e17f1c48a66179b1f7353 |

## 前置检查后的变化

#39/#40/#41 已关闭；本轮已生成新版候选并完成上文列明的实际操作。早先“缺接口契约、没有新 Setup”的描述已过时，不再作为本票实施前置。硬件及完整矩阵仍以本记录未通过项为准。
