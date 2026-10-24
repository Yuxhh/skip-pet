# 保持现有桌面启动方式的双宿主接入调查

2026-10-24（Asia/Shanghai）。任务：[保持现有桌面启动方式时，双宿主一次性接入采用什么具体方案](https://github.com/xyd-0811/skip-pet/issues/10)。本文是只读研究报告，不是已经通过联动验收的实现方案。

## 决策结论

**目前不能选定满足全部要求的双宿主接入方案。可以把 DeepSeek 的桌面 profile 内插件选作条件性首选方向；Codex 必须先通过“能否观察现有桌面 runtime”的门槛，不能直接进入双宿主联动实现。**

这次补足了具体入口和可证伪结果，而不是重复“可能搭桥”：

- DeepSeek 实际发行代码明确提供 `DSH_HOME/profiles/desktop` 外部插件 profile；本机默认目录存在。普通 Electron 启动把这个 profile 交给它自己的 Host。因而插件可以在现有桌面 Host 内运行，不需要替换用户的日常启动方式，也不必从外部窃取桌面认证 cookie。但插件是否能完整重建等待状态，仍没有通过运行验收。
- Codex 本机 CLI **0.163.0-alpha.11.2** 有此前未核查的 `app-server proxy --sock`，它代理到已运行的控制 socket，不同于另起 `app-server`。然而只读 `app-server daemon version` 尝试默认控制 socket 后失败；默认 socket 的元数据查询也未找到。该入口当前未能证明可连接在用桌面 runtime。不能据此判定所有入口绝对不存在。
- Hooks 可作为补充事件来源，不能独自解决首次连接、崩溃遗漏、等待恢复和存活判断。普通 MCP 工具也不是宿主自动广播任务状态的接口。

保留既定要求：一次配置后照常打开两个桌面宿主；按任务分别记账；等待审批/用户回答不计运行；任一任务运行则播放；10 秒从确认断线开始；重连用最新状态。本文没有替用户接受 CLI 限定、特殊启动器或缩小覆盖。

## 证据范围与版本

沿用[前轮本机报告](https://github.com/xyd-0811/skip-pet/blob/b54846f70e0404cab4f31339f15bf98bd1aa3ccb/.scratch/sukuna-pet/research/local-host-state-findings-2026-10-24.md)的身份与状态代码证据，不重复进程扫描：Codex Store 包 26.1016.8622.0；DeepSeek Harness Electron 0.2.1-rc.2。

本轮新增证据：

| 编号 | 类型 | 位置及结果 |
| --- | --- | --- |
| C1 | 实际程序自述帮助/版本；未启动服务 | `C:/Users/xing/AppData/Local/OpenAI/Codex/bin/37f54d68e5533a51/codex.exe --version` 返回 `codex-cli 0.163.0-alpha.11.2`。`app-server --help` 列出 daemon、proxy、generate-ts、generate-json-schema；proxy 帮助描述连接运行中的控制 socket，`--sock` 参数明确为 Unix domain socket 路径。 |
| C2 | 实际只读诊断；未创建任务 | 同一程序 `app-server daemon version`，帮助描述“Print local CLI and running app-server versions as JSON”。实际退出 1：`failed to connect to C:\Users\xing\.codex\app-server-control\app-server-control.sock`，`os error 10050`（套接字操作遇到已死网络）。没有执行 bootstrap/start/restart/proxy。 |
| C3 | 元数据，未读取配置/会话 | 默认控制 socket 路径的 `Get-Item` 未找到；`C:/Users/xing/.dsh/profiles/desktop` 目录存在。C2/C3 只否定本次默认端点可达性，不能证明不存在自定义端点，也不能将诊断失败解释成 Codex 桌面故障。 |
| D1 | 既有发行成员的定点复核 | `D:/deepseek harness/resources/app.asar` 中 `/lib/main.js` 的既有原样复制件；SHA-256 `6f3d1ddd1106371452c2204be6dfb2e5460a8e8259cdd05cdccb5387b3f9a85a`。本轮重新核对哈希及行号，没有重新解包、执行发行代码或声称获得 REA 图。 |
| D2 | 远端第一方源码/文档，版本可能不同 | 本轮公开 master HEAD `22ddee3792402c3e70ec5f86a63c3e3e895a2f60`；源码通过 gh 获取。发行物自报提交 `332895e0f7c9d4dbfb29729f5eb367fa263ff986` 的 tree API 返回 422，不能把公开 master 视为该安装版的逐字源码。 |

D1 原样复制件在主工作区 `.scratch/sukuna-pet/research/deepseek-local-evidence/lib/main.js`；本报告不上传第三方提取源码。

OpenAI 信息先复用本地证据、再读实际官方页面补足。本文引用的当前官方文档不能自动代表本机版本实现了相应能力。

## DeepSeek：有具体配置入口的条件性路线

### 入口及现有桌面覆盖

D1 行 25–68 定义 `DSH_HOME`，优先级为显式根目录、环境变量、`~/.dsh`；行 76–82 的 `resolveDesktopPaths()` 指向 `<dshHome>/profiles/desktop`；行 3383 定义 `cordis.patch.yml`；3403–3426 初始化 `package.json`、补丁和 `pnpm-workspace.yaml`，保留已有文件。行 12051 的 `activeProject=paths.profile` 与 12182–12186 把该 profile 交给普通桌面启动的 `DesktopHostProcess`。因此这不是另建 sdk/headless runtime 的建议。

对应默认位置是 `C:/Users/xing/.dsh/profiles/desktop/`，但安装实施前须在宿主自己的 profile 信息中核对是否设置了 DSH_HOME；不能仅因默认目录存在就断言当前实际 profile 没有覆盖。无需读取凭据、会话或 cookie 来确认路径。

第一方[架构说明](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/architecture.md)把 profile、bundle、外部插件和补丁层定义为公开扩展机制；[首个插件教程](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/cordis-tutorial/01-first-plugin.md)说明插件 `apply(ctx)` 与依赖注入。以上支持扩展形态，不证明任意第三方桥已有成品。

### 后续一次配置的具体步骤（尚未执行）

1. 在开发阶段产出带固定版本、`engines.dsh` 兼容声明的桥接 bundle；它是待写的适配器，当前不存在已验证的可安装包。打包为本地目录或固定版本包，随桌宠安装到用户数据目录，不放入宿主安装目录。
2. 从 DeepSeek 当前桌面插件管理入口安装该本地目录/包，由宿主管理 profile 的 dependency 与 bundle 选择；优先使用宿主插件管理，不手工覆盖整份 YAML。第一方 [plugin-manager](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/boot/plugin-manager/src/index.ts)提供 `installBundle(spec)`/`removeBundle(name)`；[安装升级说明](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/upgrade-guide/v0.2.1-alpha.2/plugin-install-over-installed/guide.md)明确接受本地目录并要求先移除再替换已安装包。实际桌面按钮文案及本机兼容检查留作预检，不能凭当前 master 名称伪造本机 UI 步骤。
3. 插件在宿主内读 `ctx` 的 Agent/Session 及等待事实，只向桌宠本地桥发送不含正文的状态。建议 Windows 用户专属命名管道、当前用户 ACL、连接代际和快照序号；这是**拟定传输**，不是 Harness 内建协议。宿主内插件以用户明确安装信任授权；不复用 UI cookie，不争抢外部 owner。
4. 配置持久化后仍按普通桌面快捷方式启动。依赖服务就绪后先订阅、缓冲事件，再在同一宿主读完整快照并建立序号边界；不能靠一页 follow 历史恢复等待。插件必须从冷启动装载，且在桌宠晚启动/重连时主动提供最新状态。

### 撤回与停止条件

先备份当前 profile 的 `package.json`、`cordis.patch.yml`、`pnpm-lock.yaml`、`pnpm-workspace.yaml`，仅回退本次修改。正常撤回为插件管理禁用/移除桥接 bundle，再退出桌宠；不修改会话数据。[桌面原地 profile 决策](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/.agents/notes/archived/architecture/2026-09-09-desktop-in-place-profile.md)明确不存在通用自动回滚，失败可留部分修改。D1 行 3527–3549、3576–3586 另有停止 Host 后备份补丁、仅保留官方 Web bundles 的原生恢复；它会影响其他第三方插件，只作为故障恢复，不能当作普通卸载步骤。

若插件无法获得所有 live Session 的等待快照，或必须覆写 approval answerer/改变审批结果、promote 冷 Session、重放用户消息才能得状态，立即停止此路线的实现验收；不得将“能收到 running”降格冒充完整支持。

## Codex：具体候选已定位，当前前置条件不成立

### 现有 runtime 控制 socket

本机 C1 已确认 `codex app-server proxy --sock <path>` 是存在的连接入口；C2/C3 说明默认受管 socket 当前不可达。**不能运行 daemon start/bootstrap 试图让错误消失**，那可能产生另一个服务，而不是观察当前桌面 app-server。亦不能把 `--listen` 命令行参数写成未经文档支持的 config.toml 键。

官方 [App Server](https://learn.chatgpt.com/docs/app-server)描述传输、初始化、thread/read、thread/loaded/list、thread/status/changed 和 turn/completed；它提供状态协议原料。关键缺口是当前桌面运行中的同一 runtime 如何对外提供受支持入口，以及独立只读客户端是否可订阅全部活动任务。文档没有在本文限定搜索内给出 Windows Store 桌面开启该控制 socket 的具体设置。

本文末尾已补做一次限定的桌面设置资源/完整官方 schema 定点检索，仍未定位到公开的本地观察开关；具体成员、检索词与边界见补充记录。未来仅在上游给出受支持端点后，才用官方 proxy 的 initialize + loaded-list/read 验证进程/实例身份及覆盖，禁止 thread/start、resume、turn/start 和任何审批响应。当前没有找到足以指导“在哪里改什么”的桌面开关，因此**此刻不提出盲目修改配置的探针**。

若后续明确入口可用，适配器结束即关闭自己的 proxy 连接；不停止宿主，不建立 daemon，不写宿主配置。只有另有官方桌面配置入口且用户批准受限实施时，才备份并改那个确切配置项，撤回时恢复该项；不能预先编造文件和键名。

### Hooks 补充路线

官方 [Hooks](https://learn.chatgpt.com/docs/hooks)支持 `~/.codex/hooks.json` 或 config.toml 内 hooks，可用 UserPromptSubmit、PermissionRequest、PostToolUse、Stop、Interrupt 等，非托管定义需按哈希审阅信任。默认用户目录对应 `C:/Users/xing/.codex/hooks.json`。后续可安装仅转交必要标识的命令 hook，按受支持方式信任；撤回只移除该 handler，保留原 hooks。

但 Hooks 不提供完整启动快照和持续存活通道；Stop 还能被其他 hook 续跑；PermissionRequest 无法涵盖所有用户问题、取消/恢复与并发工作。因此它只能补充已有可靠状态源，不能成为满足当前要求的独立首选。没有为其完成快照而读取 transcript/session 文件，也不建议以文件尾追踪替代受支持的状态接口。

## 覆盖矩阵

“代码”指本机静态依据，“协议”指当前官方说明；均不等于运行验收。

| 必要能力 | Codex 同 runtime proxy | Codex Hooks 单独 | DeepSeek profile 内插件 | DeepSeek 外部 WS/API |
| --- | --- | --- | --- | --- |
| 逐任务身份与全桌面覆盖 | 协议有 thread/turn；入口/覆盖未证实，默认端点失败 | 有 session/部分 turn；子代理及当前全部任务不完整 | 代码有 Session/Agent；须证实全部 live 集合 | list 有 Session；认证与 owner 未证实 |
| 区分运行/审批等待 | 协议有 waitingOnApproval；实际转换未验 | 只能事件修正，恢复不完整 | running + asked/decided 原料；须处理并发工具 | 单独 running 不够 |
| 用户问题等待/恢复 | 有 requestUserInput/resolved 原料；快照范围待证 | 没有完整等待快照 | timed open/continued 与 legacy blocking 必须分开；live 全量快照未证实 | follow 分页遗漏/冷会话副作用，不能直接用 |
| 首次快照 | 同一 runtime loaded/read 候选，前置入口未过 | 没有 | 同宿主 registry + 等待快照候选，待探针 | list 不 resume，但不含全部等待 |
| 快照/订阅竞态 | 未证实无副作用观察订阅及序列边界 | 无序列化快照 | 拟用先订阅缓冲/同宿主序号；需验证 | follow 局部有缓冲，不能推定覆盖所有状态 |
| 完成/中断/错误 | 协议有 turn/completed 分类 | Stop/Interrupt 非完整结束事实 | turn/end 与 status/error 代码，需队列续跑验证 | 同左但受权限范围限制 |
| 确认断线 | 有连接后 EOF/close 可用；当前未接通 | 没有持久在线证据 | 拟定管道 close/心跳；须区分插件挂起和卸载 | WS 有心跳/close/error 静态证据 |
| 重连最新状态 | 需重建同 runtime 快照；未证实 | 不能独立满足 | 新代际全量快照 + 序号设计；等待仍是门槛 | ready/事件重投递不等于完整快照 |

## 后续最小验证与决策门槛

1. **先解决 Codex 入口，避免先做一套无法覆盖双宿主的桥。** 仅在第一方资源找到明确设置/端点后，做只读连接身份检查。通过条件：连接的就是普通桌面在用 runtime，能枚举桌面已加载任务，不需要另起服务、改日常启动器或取得 UI 私有凭据。未找到则停止 Codex 适配实施，记录需上游提供的“现有桌面只读观察端点 + 完整运行/等待快照/订阅”能力。
2. **DeepSeek 小型兼容探针，单独评估。** 在允许实施阶段，仅安装可卸载的状态探针 bundle，启动时记录无正文的能力清单、全量 Agent/Session 和 active waiting 标识；桌宠晚启动时重发快照。先不接正式动画。不改变 approval answerer、不回答用户问题、不激活冷 Session。若 SDK/profile 当前版不兼容或缺 live 等待注册表，就停止，向上游定位需要增加的 snapshot API；不是询问用户技术事实。
3. 两宿主各自通过入口与快照门槛后，才在可控测试任务验证：双聊天并发、一等审批另一运行；审批解除/取消；timed open→continued、legacy blocking；完成/中断/错误后队列续跑；模式切换时不会误修改宿主任务。预期只排除真正被阻塞的任务，其他运行任务继续驱动。
4. 最后测试桌宠先/后启动、宿主重启、连接中断及重连期间状态变化。空闲事件流沉默不能触发断线；收到明确 close/EOF 或定义好的探活失败后才开始 10 秒。新连接快照替换旧代际状态，旧请求不能复活。测试断线属于后续明确授权的集成验证，本轮没有执行。

如 Codex 门槛仍失败，可继续独立桌宠的已确认点击/持续模式开发，把任务联动保留为未通过的功能；**是否允许首版先交付这两种模式是未来产品范围决策，本文没有替用户选择**。另起受控 app-server、改用 CLI/专用启动器、外部读取私有日志都改变当前约束或覆盖，不列为本轮可接受替代实现。

## 调查结束边界

限定检索了本机同一 Codex 程序的帮助/版本/只读 daemon-version 诊断、既有 DeepSeek 发行成员的路径/加载/恢复代码、DeepSeek 第一方架构/插件管理与迁移文档、OpenAI 官方 Hooks/App Server/[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)/[开发设置](https://learn.chatgpt.com/docs/developer-settings)及相关检索。配置参考中未找到 `listen` 设置；这不是全产品不存在该能力的证明。一次官方搜索调用长时间未返回，结束等待后未引用其结果。

没有扫描用户消息或令牌、读取认证配置、调用任务业务 API、安装插件、改宿主配置/安装文件、启动 daemon、创建测试任务或执行真实断线。原视频、`D:/dsh-pet` 保持只读。当前结果足以拒绝“纸面已实现双宿主联动”，并把下一步分成明确的入口预检、DeepSeek 等待快照探针和未来产品范围决策。

## 同日补充：Codex 桌面公开设置的限定定点检索

这一步已在研究范围内完成，**不再把“查现有设置/schema”留给用户决定或作为未经执行的建议**。结论仍是：本次限定材料没有给出可配置的本地 Windows 桌面同 runtime 观察端点，不能选定 Codex 接入路径；这不证明产品整体绝对不存在其他入口。

### 官方完整 schema

实际打开 [config.toml JSON schema](https://learn.chatgpt.com/docs/config-schema.json)（官方旧地址 `https://developers.openai.com/codex/config-schema.json` 重定向到此）；工具返回完整页面索引 8,331 行。对该 JSON 页面逐词查询 `control_socket`、`app_server`、`daemon`、`listen`、`observer`，均没有匹配。配置参考的 `socket` 命中是沙箱网络 socket 许可规则，`supports_websockets` 是模型提供方 Responses 传输，不能当作桌面 app-server listener 设置。另一次 Python HTTPS 获取在 TLS 握手超时，未得到可解析字节，因此没有声称程序化遍历或取得该 schema 哈希。

这是当前公开 schema 的文本检索结果，不能推断所有未文档化设置不存在，也不能证明当前发行物完全等同这份最新 schema。

### 当前桌面发行资源

目标固定为 `C:/Program Files/WindowsApps/OpenAI.Codex_26.1016.8622.0_x64__2p2nqsd0c76g0/app/resources/app.asar`。先只读 ASAR JSON 成员索引，再用成员偏移定点读取下面 6 个第一方 JS 成员；没有全量提取、反编译、运行成员或读取用户配置。当前工具清单没有 REA 工具，按 REA 恢复指南使用受限的普通文件静态证据，**没有 REA Evidence ID，也不声称完成语义图分析**。

| ASAR 成员 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `/.vite/build/main-CT5a1yCd.js` | 4,080,823 | `cdac659a830908ec5202a887e5a37b302074bfc9e9ab0f52fed3e8abbdb9e713` |
| `/webview/assets/configuration-fields-14404446a1e8.js` | 157,275 | `fb252bbceeb79c1209ae3d9a30cfdd79406df4f46c246264d4b90e51191eba59` |
| `/webview/assets/general-settings-27118198cef3.js` | 161,768 | `2104c6f9f0183d8ad2c78fc3c622eab22c9a2a7e2372dd3d0c6d647f092ba19e` |
| `/webview/assets/security-settings-98d075740c14.js` | 152,927 | `c0696544a4a3a36106709dd2a513860bcf16b665c05e6c5382f21704c8295687` |
| `/webview/assets/remote-connections-settings-59c3870c0198.js` | 161,564 | `d4c57c4f8a3b975381e7cc6142ab68f728ea9cc4384b300b75c3217d00eaa04d` |
| `/webview/assets/_virtual_settings-search-documents-c229b8f25f3e.js` | 536,304 | `2fd72bacef280659e9bc6c4023bbd026922688fb0503ba087c1cce542bb1b33c` |

共同精确检索词（不区分大小写）：`app-server-control`、`app-server proxy`、`controlSocket`、`control_socket`、`CODEX_APP_SERVER`、`appServerSocket`、`app_server`、`--listen`、`--sock`。5 个 webview 设置/搜索成员中这些词均为 0 次命中。不能据此证明其全部依赖模块没有动态生成的别名设置。

主进程的直接相关命中与源码上下文：

- UTF-8 解码后字符偏移约 3,503,807 起的 3 个 `app-server-control` 命中构造 `$CODEX_HOME` 下的控制目录、日志和 forwarded SSH agent socket；附近有 SSH 连接参数。
- 偏移约 3,512,684 的 `--listen unix://` 位于 `runRemoteLoginShellCommand` 的 SSH bootstrap 命令；约 3,516,518 的 `app-server proxy` 在 `createSshProxyStream` 中，使用 `this.options.sshConnection`。两个 proxy 字面量命中均属于这段 SSH 代理/报错路径。**这补充了 proxy 与远程受管 daemon 的实际使用场景，没有给出本地 Windows 桌面开启 socket 的设置。**
- 两个 `CODEX_APP_SERVER_FORCE_CLI` 命中位于内部路由选择：一处结合 `kind!==ssh`，另一处在本地/远端 websocket 路由选择。只看见内部环境分支不能认定它是面向第三方观察者的受支持接口；改变它还可能改变桌面 backend 行为，因此本报告不建议设置这个环境变量。
- `--sock`、`controlSocket`、`control_socket`、`appServerSocket` 在该主进程成员中均没有命中。主进程另有 62 个 `app_server` 命中，大量属于日志/请求操作名；没有把这些字符串命中当作公开设置。

偏移为解码后的字符索引，不是 ASAR 原始文件字节偏移；哈希固定源成员后可复核。此检索不遍历所有动态依赖/混淆别名，不能证明无其他内部 IPC，更不能把内部 IPC 存在等同对第三方开放授权。

### 收敛后的下一步

当前没有一个已找到且受支持的本地桌面配置项可以合理改动并撤回；因此暂停 Codex 适配实现门槛，不让用户猜参数、不盲装插件或启动新服务。需要上游明确提供或确认：

1. 当前 Windows 桌面所持有同一 runtime 的第三方只读连接端点、授予方式与实际配置位置；若 socket 是受支持方案，应说明普通桌面启动如何创建/公布它，而非另起 daemon。
2. 连接后的实例身份判定、全部活动任务覆盖、完整运行/等待快照，以及不改变会话生命周期的订阅/快照序列边界。
3. 端点失效与恢复语义，允许重建最新状态，而不是依靠事件沉默、日志读取或漏失开始事件。

上游给出确切入口后，才执行前述只读实例身份验证，再讨论可控任务的运行验收。若没有这些材料，产品范围调整仍是未来决策；本研究没有预先缩减功能。此补查没有连接 proxy/daemon、调用业务 API、读取用户配置值/会话/凭据，或执行任何宿主改动。
