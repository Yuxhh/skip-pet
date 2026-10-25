# DeepSeek 与 dsh-pet：任务状态气泡来源的有界研究

日期：2026-10-25（Asia/Shanghai）。研究票：[DeepSeek 与 dsh-pet 如何提供完整任务状态](https://github.com/xyd-0811/skip-pet/issues/32)。地图：[宿傩桌宠双宿主任务状态气泡规划地图](https://github.com/xyd-0811/skip-pet/issues/30)。后续标题与需求以 Issues 最新正文为准。

## 结论

**本轮找到可直接核对的 dsh-pet 宿主桥接源码，支持“在 Harness 内加载小插件，再将状态交给独立桌宠”的具体方向。不能直接复制它就承诺完整接入。** 这份桥本身只追加事件文件，没有提供本项目要求的完整初次/重连状态快照或独立周期心跳。消费者可能有其他补偿机制，本轮没有逆向证明它们不存在。

建议后续优先评估自建精简状态插件：只传任务身份、运行/真实等待/结束状态和连接代际；另行补齐快照与存活能力，供桌宠上方文字气泡提示。这里是候选方案，用户尚未接受一次性配置；没有安装、修改或运行桥接，更没有通过端到端验收。

## 范围与证据身份

- 已先认领本研究票。只读研究，未运行参考程序/安装包、未访问实际桥接日志、凭据或用户会话正文，未创建测试任务。
- 沿用[上次本机状态调查](https://github.com/xyd-0811/skip-pet/blob/b54846f70e0404cab4f31339f15bf98bd1aa3ccb/.scratch/sukuna-pet/research/local-host-state-findings-2026-10-24.md)和[桌面接入调查](https://github.com/xyd-0811/skip-pet/blob/4c264eb0ae10624c6d987684adbf279333395aa7/.scratch/sukuna-pet/research/desktop-host-connection.md)的版本与等待状态边界，不重复动画取证。
- 本轮重新计算 `D:/deepseek harness/resources/app.asar` SHA-256 为 `47874618bf5b3011fcaac10cd4c85f69da333e70d4f99b921207c78d0999512a`，与既有 `deepseek-local-evidence/manifest.json` 的来源哈希相同；既有 `/lib/main.js` 副本重新计算为 `6f3d1ddd1106371452c2204be6dfb2e5460a8e8259cdd05cdccb5387b3f9a85a`。该发行包 `package.json` 是桌面版 `0.2.1-rc.2`、构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986`。安装目录下 `version` 文件值为 Electron 运行时 `44.7.0`，不将其误当产品版本。
- `D:/dsh-pet/app/dsh-pet-standalone-webm-chat.exe` SHA-256 为 `687255faea034bd0e672a870da732650dbbd5b9aae050586e143ac1e55c50407`。REA `open_binary` 成功；`inspect_artifact` Evidence `ev_5be435179d11e15269e10aa19ee4a6b510f0f3bfa82100f095abd84884789d5f` 仅辨识 PE 根文件，未列出 PyInstaller 子模块，不能把它算作消费者语义分析。
- 新发现：发行目录包含可读 `D:/dsh-pet/app/_internal/integrations/dsh-pet-bridge/`。`package.json` 声明 `@dsh-pet/bridge` `0.2.0`，ES module、MIT；`dsh.bundle.patch` 指向 `cordis.patch.yml`。本轮不复制或上传第三方源码。
- REA 对该小目录执行 `analyze_javascript_application(format=directory, detail=summary, analysis_timeout_ms=30000)` 成功。父 Evidence：`ev_ad817ffcc3ed7d356986443b3dc0f10d3163bd9555089541b119089e1f3083dc`，摘要 Evidence：`ev_389ebb9cb124fb74a0de79bdf26e0339a3cb3e8f726bb104dc7c8d9eac414632`；目录内容哈希 `f48134fd6c6b55b98d026743bca6faa9d6d9a0bec247cd836374f2b96598cf2d`。3 个相关文本文件、2 个 JS 均无解析失败；application coverage complete，但 semantic coverage unknown、1061 个语义 unknown。静态语法图不代表运行证明。
- 核心 `index.js` 单文件 SHA-256 为 `4e2803bb73affd1a37b0727d6015b0f72a84f5515df293a2de8390dcee5dbf53`。下文行号均指该发行文件，非远端 master 或推测源码。

## dsh-pet 桥实际做了什么

| 能力 | 可核对的静态事实 | 可复用程度 |
| --- | --- | --- |
| 宿主扩展形态 | `package.json` 与 `cordis.patch.yml` 将 `@dsh-pet/bridge` 插入 Cordis；`index.js:725` 导出 `apply(ctx)`，没有外部运行依赖 | 可以借鉴零依赖小插件形态，不要求复制其功能全集 |
| 多 Agent | `32–45` 分 Agent 记 working/idle 后执行“任一忙即忙”的聚合；`740–799` 在 `agent/created` 后订阅各 Agent 的 `agent/status`，销毁时移除 | 按 Agent 记账可借鉴，但 working 聚合没有排除等待，不能直接用作本项目最终判断 |
| 状态事件 | `448–468`、`821–1090` 转发 turn/step/assistant/tool/approval 等会话事件；`803–815` 转发真实需要审批的 Cordis 请求及 resolved | 可用作规范化输入；具体等待规则须对齐本机版本，不只看事件名字 |
| 问题配对 | `524–585` 使用 sessionId 与 callId 复合身份去重问题，tool/result 才解除；`929–935` 兼容 message.source.callId | 复合身份可借鉴，但不能据此证明覆盖 timed questions 的全部 continued、取消、恢复情形 |
| 失败与恢复 | `207–243`、`1018–1045` 根据 turn/end 的 error 原因与重试/工具结果统计判最终失败；中途错误恢复不直接当最终失败 | 方向可借鉴，仍需明确任务结束与错误细分，避免套用阈值冒充宿主事实 |
| 传输 | `72–82` Windows 目录为 `%APPDATA%/dsh-pet-bridge`；`596–657` 每进程写 `dsh-{pid}.jsonl`，80ms 合批，超过 1MB 轮转 | 说明本地文件桥可工作于这种架构；轮转、漏行、晚启动、跨进程 ACL 需自行验证 |
| 多实例与代际 | `602` 为插件每次加载生成 UUID；`630–644` 在记录末尾强制覆盖 inst，并带秒级 ts | 可借鉴避免 PID 复用与旧代际事件污染，但没有看到单调事件序号 |
| 元数据 | `299–387` 尝试 apiProxy 的 sessions/workspace list；缺服务时读 session_projcache 标题/目录，再写 session/meta | 标题刷新不等于运行/等待全量快照；本项目可先使用最少标识，不必照搬缓存读取 |

源码注释中的“实测验证”属于发行作者的说明，本文没有重现实验，不能转换为本项目已验证。

## 不能直接照搬的缺口

1. **快照/重连。** 这份 JS 的 liveAgents 在收到 agent/created 时建立；聚合仅在后续 status/销毁事件变化时追加。没有发现向晚启动消费者或重连者提供全量运行及未决等待状态的请求/响应，也没有发现枚举既有 Agent 注册表来重建所有等待。文件顶部说明 Python DshMonitor 用 byte-offset tail 且不回放历史，但本轮未解析 Python 消费者，不将这段注释当作其运行实现已经核验。仅依赖“从现在开始读新增行”会存在晚开错过既有状态的风险，这是设计推论，须实测。
2. **存活。** JS 计时器用于写盘合批、元数据刷新与去重；未发现独立周期心跳或断线确认协议。文件长期无新增既可能是空闲，也可能是插件/宿主退出。不能依据最后一条事件超时，开始本项目的 10 秒断线宽限。Python 消费者是否检查进程/其他存活来源未核实；即使检查进程存在，也不能单独证明插件仍健康。
3. **等待。** 此桥明确将普通 approval/asked 视作可能只是审计信号，不以它创建真实审批请求；真实锁存来源是 Cordis requiresApproval。用户问题主要追 ask_user_question 的调用/结果。它提供了比单独 running 更好的事件原料，但不是完整 live 等待快照。上次研究已指出 timed open/continued 与 legacy blocking 的不同，本轮没有运行探针推翻这项边界。
4. **数据范围。** 顶部注释说不落正文，代码仍在 `563–573` 将 questions 全对象写入事件；`803–807` 还携带 request payload，若仅需状态就不应全量转发。本项目候选插件应改为明确的必要字段白名单，不把“作者注释声称脱敏”当作数据最小化证明。本文没有读取任何实际问题或日志。
5. **异步/可靠性。** JS 合批仍使用同步文件写盘且异常静默；说明它避免影响宿主，但消费者不能据缺失事件证明任务结束。1MB 轮转不等于有缺口恢复机制。

## 给后续决策的候选方案与用户实际操作

用户最新明确只需要桌宠上方的文字气泡提示任务进程，取消点击进入任务及任务列表。保持现有角色单击动画；是否还让运行状态驱动自动跳动，留待独立人工决策。用户希望日常照常打开两个软件，设置尽量少；尚未理解并接受抽象的插件/本地桥安装边界。任务定位与导航已移出本轮研究目标。

候选插件路线的通俗解释是：**给 Harness 加一个小配件，只告诉桌宠它现在忙不忙、是否正在等你处理；以后照常启动 Harness。** 后续开发者先产出精简兼容探针，再展示确切安装位置、界面步骤、影响文件和卸载入口，由用户选择是否采用；不要求用户提前判断技术名词。

若该路线通过探针，预期最少用户操作是：关闭 Harness，运行桌宠中可审阅的一次接入设置（或在 Harness 插件管理中添加本地小配件），重新打开 Harness，看到连接自检结果。这里仍是候选交互，当前没有完成可安装包或核验本机 UI 按钮，不能把这段写成已验证安装教程。宿主升级可能使插件失配，应显示“当前版本待适配”并提供移除入口，而非静默失联。

开发前须先证明以下门槛：

1. 由普通桌面启动加载到真正的桌面 profile，而非另起服务；安装、禁用、卸载和回退只影响该小配件。
2. 以有副作用边界的方式拿到全部 live Agent 与真实未决等待快照；先订阅/缓冲再快照或有明确序号边界，晚开与重连均可重建，旧代际不能复活任务。
3. 心跳、连接关闭或同等明确来源能确认插件/宿主失联；从确认断线后才开始 10 秒宽限，沉默不会误判。
4. 实机验证审批、问题 continued/真正阻塞、取消、并行任务及结束/失败；联动判断与列表一致，不让一个任务结束清掉其他任务。
5. 将状态映射到短文字气泡，明确正在运行、等待处理、完成、失败和失联的语义；仅给有数据依据的定性阶段，不虚构百分比。多任务排序与气泡保留时间另作产品决策。

本次研究已回答桥接实现形态并缩小后续验证范围；完整任务状态接入仍有明确未过门槛。报告不替用户做兼容、安装或气泡交互取舍，也不宣布生产功能完成。
