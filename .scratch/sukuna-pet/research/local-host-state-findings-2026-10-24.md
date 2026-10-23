# 本机双宿主任务联动状态调查

日期：2026-10-24（Asia/Shanghai）。研究票：[本机双宿主能否可靠提供任务联动所需状态](https://github.com/xyd-0811/skip-pet/issues/9)；地图：[宿傩点击弹跳桌宠规划地图](https://github.com/xyd-0811/skip-pet/issues/1)。

## 总体判断

**本轮证据不足以确认当前双宿主已能可靠满足全部任务联动规则，也没有证据证明目标不可实现。** 本轮完成的是受限只读研究；未安装适配器、修改宿主配置、启动测试任务或进行真实断线实验。发现的候选入口不等于已经通过兼容验收。

| 项目 | Codex | DeepSeek Harness |
| --- | --- | --- |
| 实际运行宿主 | Windows Store 桌面包 26.1016.8622.0，带 app-server 子进程；独立 CLI 未在一次快照中观察到 | Electron 桌面版 0.2.1-rc.2，发行物自报构建 332895e0f7c9d4dbfb29729f5eb367fa263ff986 |
| 每聊天/任务运行状态 | 内部工具返回按聊天区分的粗状态，但 active 尚不能解释为任务运行；App Server 协议仅文档候选 | 发行代码有每 Session running、状态与错误事件；尚未验证独立程序实际获取 |
| 等待审批或用户回答 | 本机转换未验证 | 基础 running 不能排除等待；审批要结合未决请求，用户问题须区分 open、continued 和 legacy blocking |
| 首次/恢复最新状态 | 未证实可连接现有桌面宿主；另起 app-server 不证明拥有桌面内存态 | list 有无 resume 的静态依据；follow 有分页、审批恢复缺口及冷会话 promote 副作用 |
| 确认断线 | 尚未证实独立观察者实际使用的传输 | 有 WS 心跳、close/error 的代码依据；实际接入、探活周期与重连仍未验证 |
| 独立桌宠连接当前宿主 | 未证实 | 有认证和 owner 约束，不能凭 localhost 监听判定可直连；宿主内桥接仍是候选 |

证据的出处、定位、哈希、失败的分析尝试及覆盖边界列于下文两份宿主调查。代码观察均是静态事实，不能冒充实际状态转换。官方文档能力单独标注，不能推定为本机版本已提供。

## 对交付决策的交接

已确认的产品规则保持原样：[三种模式与双宿主任务状态如何协同](https://github.com/xyd-0811/skip-pet/issues/8#issuecomment-6369365376)。所有来源按任务独立记账；任一任务运行则跳动；等待不计运行；完成、中断、错误只清除相应任务。没有新事件不代表断线，10 秒宽限从确认断线起算，恢复后用最新状态重建。

[第一版采用怎样的独立运行与交付方案](https://github.com/xyd-0811/skip-pet/issues/6)需要基于这些证据选择接入路径与验证条件。若必须安装桥接、改变启动方式或收窄桌面/CLI覆盖，应将影响使用的取舍交给用户；本研究不替用户接受，也不默默退化已确认行为。

后续集成验证的先后条件：

1. 先证明独立观察者可访问真实在用的宿主状态与合法的权限入口；不能以另起实例、窗口存在或内部模型工具可用代替。
2. 获得一次完整的初始运行与等待状态；证明订阅与快照之间没有漏事件，分页及历史尾部不会留下假等待。
3. 在可控任务中验证多聊天并行、一项等待另一项运行、审批解除/取消、问题 open→continued 与 legacy blocking、完成/中断/错误及队列续跑。
4. 分别验证事件流沉默、明确断线、确认断线后 10 秒失效和恢复时的最新状态；区分心跳判定耗时与 10 秒宽限。
5. 桥接后仍需验证双宿主合并、独立桌宠先启动/后启动及宿主重启。当前没有执行这些实验。

这些步骤是后续方案的验证条件，不是本规划轮次已获授权执行的任务。本轮未编写桌宠生产程序，没有更改原视频或参考目录。

---
## 本机 Codex 状态接入证据（2026-10-24）

关联：[本机双宿主能否可靠提供任务联动所需状态](https://github.com/xyd-0811/skip-pet/issues/9)。调查时区为 Asia/Shanghai。只读调查；没有启动 Codex、创建任务、读取用户消息/会话文件或凭据配置、修改宿主配置、安装插件。

### 结论

**已核实本机实际桌面宿主及其 app-server 子进程；没有核实独立桌宠可以接入该进程的任务状态。** 官方 App Server 协议值得继续验证，但不能据此宣布本机已实现“任一聊天运行则跳动”、等待排除、断线后 10 秒或重连快照。现阶段完整行为的兼容性仍未证实，也没有证据证明它绝对不可行。

### 本机已观察

| 证据 | 观察及边界 |
|---|---|
| L1：`Get-AppxPackage -Name OpenAI.Codex` | 包名 OpenAI.Codex；版本 **26.1016.8622.0**；PackageFullName 为 `OpenAI.Codex_26.1016.8622.0_x64__2p2nqsd0c76g0`。这是应用包版本。 |
| L2：`Get-CimInstance Win32_Process`，仅筛选 Codex 及明确父 PID | 桌面进程 `ChatGPT.exe` PID 91228，位于该包的 `app` 目录。其子进程 `codex.exe` PID 64732 带 `app-server` 参数；另有同父进程的 `codex.exe` PID 12864 带 `exec-server --remote` 参数。报告不复制远端环境标识。 |
| L3：`Get-Command codex`、文件元数据及 SHA-256 | 命令解析为 `C:\Users\xing\AppData\Local\OpenAI\Codex\bin\37f54d68e5533a51\codex.exe`，与 L2 两个子进程相同。文件 336134960 字节；SHA-256 `C81ED464E5E7CAFD09A5FA26AF390C480BED8E9FAB2A87A54B285FBD56E7122A`。PE ProductVersion/FileVersion 为空；未运行 `--version`，**CLI 语义版本未知**。路径哈希段不是语义版本。 |
| L4：`Get-Item ...\app\ChatGPT.exe` VersionInfo | ProductVersion/FileVersion 均为 `155.0.8059.80`。这与 Chromium 资源命名一致，但不将它当作 Codex 产品版本。 |
| L5：app-server 参数 + `Get-NetTCPConnection -State Listen` | 观察到的 app-server 命令行没有 `--listen`。针对 L2 三个 PID 的一次 TCP 监听快照没有返回记录。**只证明该时刻这些 PID 没有被此查询枚举出的 TCP listener**；没有查清命名管道或其他进程转发，也没有证明永远不开放接口。普通出站 TCP 连接存在不等于桌宠可订阅的接口。 |
| L6：已连接的 `codex-app-tools` 工具 `list_threads({limit:1})` | 成功返回 schemaVersion 4、一个按聊天标识区分的条目，`kind=codex`、`status=active`。未保留标题、摘要、ID或消息内容。**该工具的 active 未核验为模型正在运行**，不能映射为“应跳动”；也未观测等待、结束或重连转换。这证明本会话已有宿主工具能够查询一份聊天列表，不证明独立进程获得了工具或访问权。 |

进程观察范围中没有发现另一个独立交互式 Codex CLI。此为一次有界进程快照，不证明用户从未使用 CLI。桌面 app-server、远端 exec-server 和独立 CLI 不能互相替代覆盖证明。

### 发行物分析边界（REA）

定位到本机同一应用包下 `app\resources\app.asar`（625947531 字节）。按 REA 技能调用 `analyze_javascript_application`，`format=asar`、`detail=summary`、`analysis_timeout_ms=30000`。调用返回 `artifact_integrity_mismatch`，没有成功的应用图或 Evidence ID。

工具指出 unpacked 成员 `node_modules/@worklouder/device-kit-oai/node_modules/@serialport/bindings-cpp/build/Release/bindings.node` 的声明 SHA-256 `9bde6f6115f3788e5b3dea91b024850196c522ba5117c4ddf6936a652bc8f09d` 与实测 `26f4f2191290bc8365631421a1d4035b6e983e99b811353da6de127b2d8d9d14` 不同。REA 提示打包后签名或 strip 也可能产生这种差异。**这里只表示本次严格完整性模式未能分析，不表示应用损坏或不可信。**

随后进行一次只读恢复尝试：同一目标、`detail=summary`，改用工具明确支持的 `integrity_policy=record-and-continue`，继续设置 `analysis_timeout_ms=30000`。此参数实际限制每个 JavaScript 来源，不限制整个大归档总时间。调用超过初始 30 秒等待后仍未返回，又进行了有限等待，最终结束客户端等待。**没有收到完成图、部分图或可引用 Evidence ID；也没有收到服务端超时结果，不能声称分析服务端已取消。** 恢复模式若返回图，其发生完整性矛盾的观察也必须视为 untrusted/partial；本次未获得图，未据此作任何静态能力结论。未改动安装包、宿主配置或执行目标。

因此本报告没有从发行物证实内部 IPC、外部订阅接口、状态字段语义或断线处理。

### 仅文档支持的候选能力

本次按 OpenAI Docs 顺序先搜索官方主题，再实际打开 [官方 App Server 文档](https://learn.chatgpt.com/docs/app-server)（原 `developers.openai.com/codex/app-server` 重定向）。以下均为文档事实，**并非本机对应版本验证**：

- 默认 stdio；可显式指定 WebSocket；初始化握手按连接进行。
- `thread/read` 提供含 runtime status 的摘要且不订阅；`thread/status/changed` 表达状态变化，示例含 `waitingOnApproval`。
- `turn/completed` 区分 completed/interrupted/failed；`item/tool/requestUserInput` 与 `serverRequest/resolved` 是用户输入请求及清理方向。
- `thread/list` 有来源过滤和分页；默认来源不代表所有桌面/子代理聊天。

未在所读页面找到 `waitingOnUserInput` 这一精确拼写，不能捏造该字段。等待请求存在也不自动证明其期间其他并发工作均停止。

这些协议在“已能连接到持有真实 runtime 状态的同一 app-server”的条件下，提供快照与事件的设计方向。L2/L5 尚未证明这个前提。另起 app-server 即使读到历史记录，也不能据此认为它拥有桌面另一个进程的内存态。

[上一轮接口调查](https://github.com/xyd-0811/skip-pet/issues/7#issuecomment-6369155738)提到的 Hooks 仍只是候选方向。本次没有读取 Hooks 用户配置、启用 Hook 或观察 Hook 执行；不能把它当作已接入，也不能仅靠开始/停止事件解决首次快照和连接存活。

### 需求逐项覆盖

| 需求 | 本机证据等级 | 尚缺证据 |
|---|---|---|
| 按聊天/任务区分运行 | 部分：工具返回聊天条目与粗状态；语义未验证 | 精确 task/turn 身份、正在运行定义、多聊天完整枚举及子代理规则 |
| 排除等待审批/用户回答 | 文档候选；本机未验证 | 本机字段、等待期间并发工作的语义、恢复运行转换 |
| 完成/中断/错误只清除对应任务 | 文档候选；本机未验证 | 对应 turn 的真实转换以及乱序/重复事件处理依据 |
| 首次连接最新状态 | 未验证 | 独立观察者连接现有宿主并完整读取当前快照，且处理订阅与快照之间竞态 |
| 确认断线 | 未验证 | 独立观察者使用的实际传输、明确 close/EOF/process exit 或其他可验证存活信号 |
| 断线后最多保留 10 秒 | 目标规则，无本机实现证据 | 从确认断线时刻计时；事件沉默不能启动计时 |
| 恢复后最新状态 | 未验证 | 重连同一真实宿主，重新快照/订阅、丢弃旧代状态、覆盖断线期间变化 |
| 独立桌宠读取而不改变现有工作方式 | 未验证 | 既有外部只读入口与授权/生命周期；本会话模型工具可调用不等于任意程序可调用 |

状态账本必须跨双宿主和多任务合并；任何一个仍运行则继续。进程存在、窗口存在、聊天列表的 active、最后事件时间以及出站连接均不能单独满足该判定。

### 需要后续验证或由用户决定的兼容取舍

后续若允许单独的集成验证，应先证明独立观察者能只读连接现有桌面宿主，再验证两聊天并行、一项等待另一项运行、完成/中断/错误、空闲事件流沉默、明确断线与重连期间任务变化。这些验证没有在本票只读调查中执行。

若现有桌面没有可用的外部观察入口，交由交付方案票比较：继续研究受支持的桥接方式；要求在受控 app-server/适配启动方式下运行并明确不覆盖普通桌面聊天；或调整首版任务联动覆盖范围。后两者改变使用条件或覆盖，**本研究没有替用户选择，也没有更改已确认目标行为**。


---

## 本机 DeepSeek Harness 任务状态证据

调查日期：2026-10-24（Asia/Shanghai）。供「本机双宿主能否可靠提供任务联动所需状态」研究票使用；不代替兼容性取舍。

### 结论

本机正在运行 DeepSeek Harness **桌面 Electron 版 0.2.1-rc.2**。该发行物具备每 Session 的 live running、状态变更和错误信号，以及当前列表、带序号的日志/投影、WebSocket 心跳和关闭机制的代码证据。但**不能把 `agent/status === running` 直接当作桌宠要求的“运行”**：审批和阻塞式用户提问可以发生在 running phase 内。现有静态证据支持“宿主内适配器汇总状态，再向独立桌宠桥接”的接入方向，不证明独立桌宠已经能连接当前宿主，也不证明初始/恢复快照能完整恢复所有等待情形。

本轮没有连接业务 API、获取聊天正文、读取认证配置/令牌、安装插件、修改宿主、发起/取消任务或启动程序。没有制造审批/问题/报错/断线，因此没有端到端验收证据。`D:\dsh-pet` 只列过顶层目录，未执行或写入。

### 证据等级与方法

- **被动运行环境事实**：通过 Win32_Process 仅取进程名、PID、ExecutablePath；Get-NetTCPConnection 仅取监听地址/端口/PID。不是任务状态观察。
- **实际发行物静态事实**：只读解析实际运行目标相邻 `resources\app.asar` 的成员索引，将限定的第一方代码成员原样复制到本项目 `.scratch/sukuna-pet/research/deepseek-local-evidence/`，按 UTF-8 逐行核对。保留成员 SHA-256，可回到用户本机发行物复核；这些复制件是本地证据，不需要上传第三方代码。
- 已按 reverse-engineer-anything 技能调用 REA `analyze_javascript_application`，目标为该 ASAR，`format=asar, detail=summary, analysis_timeout_ms=60000`。调用持续运行且没有返回 summary/Evidence ID，随后终止该等待。**没有可引用的完成 REA Evidence，不声称 REA 图分析完成**；以下源码结论是对原样提取发行成员的人工静态读证，覆盖仅限列出的文件，不是全应用扫描或运行验证。
- 不使用事件沉默、窗口存在或单纯进程存在推断任务运行/断线。

### 目标身份

1. 查询时有 5 个 `DeepSeek Harness.exe` 进程，ExecutablePath 均为 `D:\deepseek harness\DeepSeek Harness.exe`。可执行文件版本信息：ProductName `DeepSeek Harness`，ProductVersion `0.2.1.0`，FileVersion `0.2.1-rc.2`。
2. 实际 ASAR `/package.json`：`@deepseek-ai/dsh-desktop`，version `0.2.1-rc.2`，description 为 Electron shell for bundled dsh runtime and external plugins，main `lib/main.js`，build commit `332895e0f7c9d4dbfb29729f5eb367fa263ff986`，build dirty false，update channel nightly。内部 dsh-agent 包也是 `0.2.1-rc.2`。这是**发行物自报元数据**，未独立验证其与远端仓库提交字节完全一致。
3. `resources\runtime\versions.json` 记录 Node `24.21.0`、pnpm `11.28.5`。这是捆绑清单，不等同观察运行时执行了哪一个 Node。
4. 查询时 PID 72500 在 `127.0.0.1:58443` 监听。监听属于上述 Electron 可执行文件；端口可能随重启改变。没有向该端口发请求，故**不证明它是可供桌宠使用且通过认证的 API**。没有观察到可直接复用的调试端口，未启动调试模式。

第一方源码入口：[发行物自报构建提交](https://github.com/deepseek-ai/deepseek-harness/tree/332895e0f7c9d4dbfb29729f5eb367fa263ff986)。本轮源码事实以本机 ASAR 为准，不假设仓库 master 与该安装版相同。

### 能力逐项核对

以下源文件均位于该 ASAR 的 `/dsh/node_modules/@deepseek-ai/<包名>/lib/index.js`，除明确指出的 `/lib/main.js`。行号以原样复制件为准。

| 要求 | 本机静态证据 | 能断言什么 / 仍缺什么 |
| --- | --- | --- |
| 按聊天区分运行 | `dsh-agent-loop:790–798`；`dsh-api-session-controller:1940–1952,2991–2995` | Agent status 是 idle/running；Session summary 有 sessionId、agentAvailable、running。状态事件转发为 `api-session/status(agent.id, boolean)`，错误为 `api-session/error(agent.id, ...)`。可按 Session 保存独立状态，不能用最后一个事件覆盖全宿主。未验证运行实例实际启用了哪些事件转发。 |
| 完成/中断/错误 | `dsh-agent-loop:887–900,939–1040` | 每轮日志含 turn/start、turn/end，后者 reason 可是 completed、blocked、aborted、error 等；driver finally 置 idle，可能因队列再唤醒，不能无条件把单个 turn/end 当全 Session 长期 idle。错误有 agent/error。未观察实际取消、异常、工具恢复路径。 |
| 等待审批 | `dsh-user-approval:128–143,172–188`；`dsh-agent-loop:790–798` | approval/asked 带 request id、工具和可选 callId；await decide 后写 approval/decided，同 id 带 outcome。取消信号映射 cancelled。此等待没有改变 phase 的代码；仅用 running 会误判等待仍在运行。可以在宿主内按 Session+审批 id 跟踪未决请求，但必须验证并发工具/其他工作仍运行时的语义，不能简单“有一项审批就停整个宿主”。 |
| 等待用户回答 | `dsh-user-questions:169–180,185–265,267–291,613–650,653–685` | timed ask 有 `userQuestions` 投影，active 项为 open 或 continued。open 来自工具调用；超时 pending 或 TOOL_OUTCOME_UNKNOWN 会成为 continued，可迟后回答。**continued 不等于任务停下来等待**，Agent 可以继续工作。legacy blocking ask 明确不进入该 fold；仍需监听 user-questions/request 或其他活跃等待事实。不能只据 active 非空抑制跳动。 |
| 首次连接当前列表 | `dsh-api-session-controller:1935–1999,3055–3065` | list 明确读取全部可见 Session，**不 resume Agent**；live summary 的 running 来自 agents registry，持久化冷 Session 为 running false。适合作为候选初始 running 查询，仍须设计订阅与查询的顺序/缓冲，消除期间状态变化竞态；尚未调用验证。 |
| 最新投影/恢复基线 | `dsh-api-session-controller:1221–1249,1508–1595,3275–3295` | control 首帧 baseline 含当前 attached Sessions 的 projection blocks；projections 方法有 live 快径；follow 先订阅缓冲再给 snapshot，含 cursor、records、hasMore、projections。**follow records 经过 maxMessages/turnWindow 分页，不保证首帧包含全部 approval/asked**。不能把一页历史当成完整等待恢复。 |
| 只读边界 | `dsh-api-session-controller:1566,1586–1589,2967–2969` | follow 对 source=prepared 的冷 Session 会 promote，可能激活 Agent；**不是普遍无副作用的读取接口**，本轮没有调用。仅 list 明确无 resume。使用 follow 或深读冷会话作生产恢复前，应明确允许的生命周期影响。 |
| 确认连接失效 | `dsh-api-gateway:293,361–378,397–424,785–815` | WebSocket mux 有 ping、pong/收到 frame 活性处理、MAX_MISSED_HEARTBEATS=2 后 terminate；error/close 会 release 连接。它提供与业务事件无关的断线证据来源。不能将“10 秒无任务事件”当断线；客户端仍需真实 close/error 或经过定义的探活失败证据。未观察实际心跳/断线，未证明现有端口采用哪个配置周期。 |
| 连接/事件通道恢复 | `dsh-api-gateway:130–137,993–1024` | `/api/remote.mux` 承载流，`$events` 首帧 ready，带 clientId、host；owner client 新建时会重新投递当前 pendingRemoteEvents。ready 只证明事件源 ready，不能替代所有 Session 当前状态快照。未证明独立客户端的权限/事件集合与重放覆盖。 |
| 独立桌宠接入 | `/lib/main.js:8225–8236,8239–8255,12448–12468`；`dsh-api-gateway:785–790` | Shell 将 Host launch URL 交换为认证 cookie，屏蔽 set-cookie；仅对主窗口匹配的 WS 请求注入 hostCookie。WS upgrade 有 admitConnection。**不能由 localhost 监听推断外部程序无凭据直连可用**。宿主插件读取 ctx 事件再桥接是候选；本轮未安装插件，无法证明该插件入口在当前实例可用。没有读取 cookie/launch URL/配置或复用认证。 |

### 等待恢复的易错点

审批审计的 `approval/asked`/`approval/decided` 是事实对，和正在等待的 UI 请求不能简单画等号：never policy、无 answerer、取消都会迅速完成；非正常崩溃也可能留下历史尾部。因此初始化必须有完整且限定在有效 live/open turn 的事实范围，或得到宿主内 live pending registry，并在重建后与 live running 对齐。本轮选读的 approval 模块未发现专用 pending approval wire projection；这只是**限定文件搜索结果**，不宣称整应用没有该接口。`dsh-user-approval/lib/types/invariant.js:9–38,47–83` 提供 asked/decided 配对和 open-turn 约束，不是独立客户端的 live snapshot API。

用户问题更不能统一为 pending：timed open 表示前台等待，continued 是超时后还可回答的题；continued 与自动继续工作可能共存。legacy blocking 问题在此投影中为空，不表示它没在等人。失败结果会从 active 移除，成功/迟后答案会 settle；TOOL_OUTCOME_UNKNOWN 留 continued。取消、宿主重启、多个并行工具/子代理、队列继续运行、等待终端人工交互，均缺本机运行验收。普通 terminal/job 独立进程存在也不能代替 Session 正在运行。

### 对已确认目标行为的约束

「任一任务运行则跳动」有 per-Session running 原料；**还没有可靠完成 waiting 修正与全实例覆盖**，不能据此宣布可交付。「确认断线后最多保留 10 秒」可以在桥接层收到真实连接 close/error 或定义好的探活失败后启动 10 秒宽限；这个 10 秒是已确认产品规则，不是本机宿主内置超时。心跳探测时间属于确认断线之前的时间，二者不可偷换。恢复时需先确认新连接代际并拉取最新状态，再清理旧请求/旧代际；不能仅等下一条 running 事件。

下一轮验证至少需要授权一个可控测试环境/任务、确定接入权限，然后验证：多 Session 与子代理并发，审批进入/解除/取消，timed open→continued 及 legacy blocking ask，结束/错误后队列再运行，桥接先启动/后启动与断开重连，冷 Session 读取的副作用，以及终端命令仍运行时 Agent 等待人工的边界。此次只读研究无法补齐这些运行证据，不自行更改用户规则。

### 可复核定位与哈希

ASAR：`D:\deepseek harness\resources\app.asar`，SHA-256 `47874618bf5b3011fcaac10cd4c85f69da333e70d4f99b921207c78d0999512a`。

本机证据复制根：`.scratch/sukuna-pet/research/deepseek-local-evidence/`。`manifest.json` 保存提取成员名、字节数、SHA-256；从 ASAR 成员取原始字节再按 UTF-8 换行计行即可复核上文定位。

| ASAR 成员 | SHA-256 |
| --- | --- |
| `/lib/main.js` | `6f3d1ddd1106371452c2204be6dfb2e5460a8e8259cdd05cdccb5387b3f9a85a` |
| `/dsh/node_modules/@deepseek-ai/dsh-agent-loop/lib/index.js` | `cf57e3ecd487ac5c2553455aaa5cef2c6fb41e6bd61be5aa455675d1d7193033` |
| `/dsh/node_modules/@deepseek-ai/dsh-api-gateway/lib/index.js` | `4fbe460fec585ebc2cf2887261f6c33f024081a539d9fb5d6557a9002324b23f` |
| `/dsh/node_modules/@deepseek-ai/dsh-api-session-controller/lib/index.js` | `a9801acb577b03053c5d5a3191ff555c5f1d791d0acddec113bea4511e33b386` |
| `/dsh/node_modules/@deepseek-ai/dsh-user-approval/lib/index.js` | `6a5ad1ba3c3dc3abbbae52e6c8c4463970ee0c1c8988cebb0d5cf2acd17ee90b` |
| `/dsh/node_modules/@deepseek-ai/dsh-user-questions/lib/index.js` | `e1c51afac2e31be8593c6426976e5f31dbe2a709b85ae1ea43ed406146f54265` |

既有一手文档方向参见[状态接口文档调查结论](https://github.com/xyd-0811/skip-pet/issues/7#issuecomment-6369155738)。产品规则以[三种模式与双宿主任务状态如何协同](https://github.com/xyd-0811/skip-pet/issues/8#issuecomment-6369365376)为准；这些目标规则不是版本兼容证据。
