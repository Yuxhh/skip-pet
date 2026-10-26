# DeepSeek 文件桥完整现态入口：有界源码调查

2026-10-26（Asia/Shanghai）。研究问题：[DeepSeek 文件桥完整现态入口能否满足只读接入门槛](https://github.com/xyd-0811/skip-pet/issues/37)。本报告只读本地已保存的一手源码与已有提取证据，没有执行目标、安装插件、改宿主、读取实际日志/凭据/聊天正文或运行探针。

## 结论

**dsh-pet 的文件桥及消费者不能直接提供本项目要求的首次/重连全量状态。宿主源码确有 live Agent 枚举、运行根归属、原生轮次只读投影及带序号的部分投影快照原料，但完整真实等待集合和无控制副作用的联合现态仍未证明。** 因此文件桥仍需权威现态导出与健康发布，不能宣称生产入口或实机已经通过。

2026-10-26 补查修正：安装版已有 host-only `turnBoundary` 原料，当前官方源码还提供领域方法 `agents.turnBoundaryOf(session)`；两者不能无条件混用。参考 `cordis/request-run` 属于动态插件激活审批，不能当通用工具审批或整轮阻塞证明。完整补证、版本边界和最小上游契约见文末“完整现态入口补查”。能力矩阵的轮次与审批两行已据此修正。

## 证据身份与边界

- 用户指定的 dsh-pet 源码固定在 `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e`，本地路径 `references/dsh-pet-indesktop/`。以下上游链接均固定此提交。
- 宿主证据复用此前只读提取目录 `.scratch/sukuna-pet/research/deepseek-local-evidence/`。其 `manifest.json` 标明来源 ASAR SHA-256 `47874618bf5b3011fcaac10cd4c85f69da333e70d4f99b921207c78d0999512a`。此前身份调查记录为桌面 `0.2.1-rc.2`、构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986`，见[已有研究](https://github.com/xyd-0811/skip-pet/blob/1089112810ddcad6b291a793454ab35051f28e03/.scratch/sukuna-pet/research/dsh-observer-2026-10-25.md)。本次没有重新核验当前运行安装包或证明所有成员都被提取；本报告的宿主结论限于这些保留字节。
- 重新计算的重要宿主文件 SHA-256：`dsh-agent/lib/index.js` 为 `7b59cf82c2784c25bdce4e3e24e5e5303b02b9f1003efacf50255492d17baf8b`；`dsh-agent-loop/lib/index.js` 为 `cf57e3ecd487ac5c2553455aaa5cef2c6fb41e6bd61be5aa455675d1d7193033`；`dsh-user-questions/lib/index.js` 为 `e1c51afac2e31be8593c6426976e5f31dbe2a709b85ae1ea43ed406146f54265`；`dsh-user-approval/lib/index.js` 为 `6a5ad1ba3c3dc3abbbae52e6c8c4463970ee0c1c8988cebb0d5cf2acd17ee90b`；`dsh-api-session-controller/lib/index.js` 为 `a9801acb577b03053c5d5a3191ff555c5f1d791d0acddec113bea4511e33b386`。

## 能力矩阵

| 能力 | 源码已证明 | 尚不能声称 |
| --- | --- | --- |
| 全部 live Agent | 保留宿主 `dsh-agent/lib/index.js:311–332, 611–625` 的 `AgentRegistry` 暴露 `ctx.agents.list()` 和 `roots()`，返回注册表中现有对象的新数组；`get(id)` 为精确 live 对象查询 | list 不等于当前运行任务列表。`Agent.status` 把等待审批/回答也算 running；所有活动工作是否均在这个服务以及插件是否拿到同一根服务，须以普通桌面实例探针确认 |
| 根与子 Agent 归属 | 同文件 `enter(agent, owner):509–526` 保存显式运行时 owner，`isOwnedBy(id, owner):604–608` 查询；`roots()` 取 owner 未定义的项。源码明确运行时父子关系与持久化 Session lineage 不同 | 不能用历史 fork parent 代替本轮子代理归属；也未证明一个运行根下面没有 detached/并发工作等边界遗漏 |
| 稳定原生轮次 | 安装字节 `dsh-agent-loop/lib/index.js:1365–1412,1581` 定义并注册 host-only `turnBoundary`；`781–785` 自身读取该投影。当前官方源码另有 `agents.turnBoundaryOf(session)`，详见文末补查 | 已定位只读原料；旧版 keyed `stateOf` 与当前领域方法需分别适配。不能假定缺 key 等于无任务，也未通过普通桌面同实例验证；host-only 原料不自动包含在 client-visible 快照流 |
| 审批等待的不同域 | 参考桥监听 `cordis/request-run/resolved`；补查确认其属于动态插件激活。当前官方该服务有 `inventory/snapshot` 子集读口，通用工具审批则走 `ApprovalService.request` 的独立 waterfall | 动态激活请求发出后可立即返回，不能单凭 pending 判整轮阻塞；未证实通用审批的完整权威 pending 集合。禁止接管 answerer 或响应请求补状态，详见文末补查 |
| 用户问题等待 | 宿主 `dsh-user-questions/lib/index.js:48–80` 的投影 active 集合区分 `open` 与 `continued`；`continued(agent):536–537` 从 `sessionProjections.stateOf(..., "userQuestions")` 读继续等待的问答。`askTimed:613–644` 用 foreground waits 跟踪限时等待 | 同文件 `169–181` 明确 blocking legacy schema 不进入该投影，空 active 不证明没有真实问题等待。`waits` 是具体实现内部 Map，不能只取 timed active 集合冒充全部等待；也未证实 legacy 等待公开只读集合 |
| 首次/重连完整现态 | 宿主 `dsh-api-session-controller/lib/index.js:1216–1250` 的 `control(signal)` 先登记队列，再输出 `baseline()`，baseline 遍历 `ctx.sessions.list()` 并带 `sessionProjections.snapshot(session).asOfSeq/values`；存在 host-wide 投影 baseline 原料 | 这不是完整任务/审批快照的证明，也不证明外部插件可以直接借用 controller 或无需权限与副作用。尤其 userQuestions 投影有 legacy 缺口；不能调用会 promote 冷 Session 的 follow 路线补状态 |
| 事件边界和文件缺口 | dsh-pet 有文件身份、字节偏移与写者 boot UUID，识别轮转和同路径新文件；其控制 baseline 之外，宿主 Session 投影有 asOfSeq | 文件偏移是消费者摄入口径，不是宿主状态修订号。参考桥没有提供带快照边界的连续状态序列，不能据“读到了某行”证明轮转期间未漏事件 |
| 可信存活 | dsh-pet 消费者有约 3 秒端口/进程探活，以及活跃写者 PID 的明确死亡回收，不是完全没有补偿；明确 `False` 才退役，不以文件静默退役 | 进程仍活着不能证明插件仍在发布；同 PID 插件重载的旧 boot 可保留忙态。当前机制不能证明文件桥健康，不能把它直接当成本项目 5 秒宽限的可信起算协议 |

## 晚启动与重连的关键实证

1. 参考插件 [apply 的 agent/created 监听](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/integrations/dsh-pet-bridge/index.js#L740)在事件发生时建立 `liveAgents`；未在这一路径枚举 `ctx.agents.list()`。元数据刷新处理标题/项目名，不能当作运行与未决等待全量快照。
2. [ByteOffsetTailer:1390–1470](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/__init__.py#L1390)在第一次读取已有文件时设 offset 为当前文件末尾并直接返回空，明确防止重放历史。该功能名含 backfill，不是把历史回放为现态。
3. 上游[中途挂载回归测试说明](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/tests/test_dsh_mid_attach_done.py#L1)也写明，回合开始前历史被跳过，后来 turn/end 的呈现必须专门处理。这个测试证明参考作者覆盖了部分晚挂载结束提示，不证明此前运行/等待已经重建。
4. [DshMonitor.start:2240](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/__init__.py#L2240)重置收敛器和身份记账；[端口探活:2381](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/__init__.py#L2381)不能补回未决等待。重启后回 idle 属参考策略，不能照搬为本项目“已确认无任务”。
5. [低频死写者探测:2320–2367](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/__init__.py#L2320)明确描述同进程插件重载产生新 boot、旧忙态却可能仍留下的边界。该逻辑最多证明 PID 死亡时可回收，不证明插件代际仍健康。
6. [dsh_state.tick:932–960](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/dsh_state.py#L932)在 120 秒锁存超时后强制回 WORKING。此处与本项目“无证据不认恢复运行”不同，应作为必要差异，不把参考超时兜底照搬成真实状态。

## 后续最小只读探针（未执行）

在后续明确允许安装/实机验证的阶段，先产出可卸载探针，再执行：

1. **服务身份预检**：验证插件加载在普通桌面当前 profile，并取得同一根 `agents/sessionProjections` 服务；记录版本、能力布尔值和不含正文的数量/身份。没有安全的同实例入口立即停止，不能另起服务补成功。
2. **首发全量**：在已运行及已等待的可控任务存在时晚装/晚开消费者，枚举 list/roots 并核原生当前 turn 读口，读取真实 pending 集合，只导出 ID/枚举；不能将等待表不存在解释为零项。
3. **等待分类**：分别覆盖真实审批、timed open→continued、legacy blocking 与同轮子代理仍执行；只观察，不接管 answerer、不答复问题、不读问题/审批正文。缺任一所需等待入口，则记录不满足当前完整状态门槛。
4. **一致性**：先订阅再建立同宿主序号边界，验证枚举时发生的状态变化、文件轮转与重复/迟到记录。仅有字节游标而无权威状态边界时，不能标记完整同步。
5. **重载/恢复**：消费者先后启动、插件重载、桌面重启后，使用同一真实 session/原生 turn 恢复，transport boot 更新；旧 boot 消息不得重建旧轮或清掉新轮。
6. **健康与关闭**：健康发布必须独立于业务事件且绑定插件代际。端口/进程仍在但插件不再发布时能转为不可信，确认断线后才开始最多 5 秒跳动宽限；无新业务事件时仍保持健康。此项需要未来实机，不在本报告中视为通过。

**停止条件**：缺公开/经版本明确支持的完整等待集合、无法无副作用读稳定当前轮次、不能建立订阅/快照边界，或需要激活冷 Session、读聊天日志、抢审批处理权才可恢复时，停止该接入路线的生产验收。向上游提出精确缺项或另作真人范围决策，不自动降低语义。

## 研究完成边界

本次有界源码阶段已完成，澄清了可用原料、参考补偿机制和剩余入口阻塞。完整只读入口仍未证实，研究票继续保留以跟踪上游补充依据或未来获准的最小探针；不把源码阶段结束算作接入门槛通过。当前可进入明确能力检查的探针设计/实现，生产发布仍须过上述门槛。已定 Q2/Q3 无需重复询问，只有验证暴露确切能力缺失并需要改变用户需求时才回到人工决策。

---

## 完整现态入口补查：轮次读口已定位，完整等待仍有缺口

2026-10-26（Asia/Shanghai）。本次只读既有提取字节及第一方固定源码，未运行宿主、桥接、探针或安装器，未修改配置，未读取真实日志、聊天正文或凭据。此文补充并修正原报告，不把未找到写成接口绝对不存在。

## 证据身份

- 安装版保留字节：`.scratch/sukuna-pet/research/deepseek-local-evidence/dsh/node_modules/@deepseek-ai/`；来源身份沿用原报告。没有重新证明当前运行安装包与这些字节相同。
- 第一方源码固定为 [`22ddee3792402c3e70ec5f86a63c3e3e895a2f60`](https://github.com/deepseek-ai/deepseek-harness/tree/22ddee3792402c3e70ec5f86a63c3e3e895a2f60)。安装包声明的构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986` 未能通过 GitHub commit/contents API 取得对应内容；不能把当前公开源码称作安装版逐字同版。
- 当前固定源码取回至 `.scratch/wayfinder37/`，文件名用双下划线替换上游路径分隔符。第三方源码仅用于本地阅读，不随研究文本上传。

## 一、修正原生轮次读口结论

**现有安装字节已经提供可具体定位的 host-only 轮次投影原料，不能再说只有 `agent.phase.turn`。**

保留的 `dsh-agent-loop/lib/index.js:1365–1412` 定义 `turnBoundary`，含 `openTurnStartSeq`、`lastTurn`；`turn/start` 设置两者，`turn/end` 清空 `openTurnStartSeq`。同文件 `1581` 注册该投影，`781–785` 自身通过 `sessionProjections.stateOf(session, "turnBoundary")` 读取 `lastTurn` 初始化运行。该路线无需插件读取聊天日志，也无需直接访问具体 driver 的 phase。

当前公开源码进一步提供正式领域服务 [`AgentRegistry.turnBoundaryOf(session)`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/agent/src/index.ts#L301)（301–307）；[公开类型](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/agent/src/types.ts#L67)说明 open turn 与原生 turn number，不能把当前新服务直接假定安装版已有。

版本适配可优先采用已证实在对应版本存在的领域方法；旧版 keyed `stateOf` 需限定版本、检查 key 与 schema，缺失时转未知。当前源码的 keyed `stateOf` 已 deprecated，会记录警告；“不控制任务”不等于保证没有任何内部缓存/诊断写入。必须确认普通桌面实际加载同一 `agents/sessionProjections` 服务、投影已注册及调用许可，实机未通过。

## 二、审批有两个独立域，不能混称完整真实等待

### 动态插件激活审批

参考桥监听的 `cordis/request-run` 来自动态插件运行器，不是通用工具审批的全集。当前固定源码 [`DynamicCordisRunnerService.run`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/extensions/cordis-host-runner/src/index.ts#L295)（295–329）把 Client 插件激活请求登记后发事件并立即返回 `awaiting-approval`/`starting`；因此 pending 激活本身不能证明整个根任务停止执行。

同一服务有可读子集：[同步 `inventory()` / `snapshot(agent)`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/extensions/cordis-host-runner/src/index.ts#L538)（538–592）返回每插件 `latestRun`；[类型](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/extensions/cordis-host-runner/src/types.ts#L156)含 `approvalRequestId/requiresApproval/status`。实现是读取 registry 并克隆 attempt，不调用 resolver。它说明该域已有现态读取候选，不能扩大为全部审批，也未证明与安装版匹配。

内部 [`DynamicCordisRegistry`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/extensions/cordis-host-runner/src/registry.ts#L140)有 private pendingRequests；`peekRequest`（238–243）不认领，但 registry 是运行器私有字段。不能因 JavaScript 可访问内部对象，就把其当作给观察插件承诺的完整 API。

### 普通工具/命令审批

安装字节 `dsh-user-approval/lib/index.js:128–143,172–188` 与当前固定源码 [`ApprovalService.request/decide`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/interaction/user-approval/src/index.ts#L225)通过 `approval/request` answerer waterfall 等结果，并写 `approval/asked/decided` 审计。所读服务没有公开完整 live pending 集合。审计 asked 在 policy/answerer 决策前写入，不能一出现就锁存为真实人工等待；现有历史折叠也不能替代插件晚加载时的权威 unresolved 集合。

浏览器 [`ui-approval`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/client/ui-approval/src/client/index.ts#L47)的 pending 对象属于答复 waterfall 与呈现层，注册/代理会参与处理权，不是宿主全量只读入口。没有通过接管 answerer、调用 resolve 或更改请求来补调查。

## 三、用户问题与一致性边界仍不能覆盖全部现态

安装字节 `dsh-user-questions/lib/index.js:487–497,613–650` 的 waits 只覆盖 `askTimed` 前台等待；`ask:668–690` 可直接发 legacy 请求，不登记此 Map。投影 active 也明确不含 blocking legacy。因此 timed active/waits 为空不能推断没有用户问题等待。当前固定源码同样把 waits 设为 private，并只在 askTimed 登记（`packages/interaction/user-questions/src/index.ts:82,241–273`）。`attachWait` 会取得等待 claim，`answer` 会 steer 用户消息，二者均不属于被动观察。

安装字节 `dsh-api-session-controller/lib/index.js:1202–1250` 的 control 确有“先登记队列，再同步 baseline”的投影路径。当前 [`sessionProjections.snapshot`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session/session-projection/src/index.ts#L450)明确同一 Session 的 client-visible 一致切片；但 [`onChanged`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session/session-projection/src/index.ts#L434)同样只通知 client-visible units，snapshot 实现 467 行跳过无 wire 的定义。`turnBoundary` 是 host-only、没有 wire，故不能假设 control baseline 或 onChanged 自动包含原生轮次与全部等待。

本次已找到 **轮次原料 + 部分同步投影边界 + 动态激活审批子集**，尚未找到支持跨 Agent、通用审批、legacy/timed 问题与运行状态的公开统一一致快照。不能用每项“分别能读”推导联合现态无缺口；也不能据所读范围否定上游其他服务可能存在。

## 四、使这张研究票可结束的最小接口契约

不必要求上游实现本项目 JSONL 协议；至少需要明确、版本化地提供以下观察能力（同名方法仅示意，不是声称已有）：

1. **完整范围与身份**：普通桌面当前 profile 的所有 live Agent/root ownership；每个当前活动轮次的稳定 session/native turn、执行已知性及相应内部活动，插件晚加载/重载可枚举，缺能力必须显式 unknown。
2. **真实未决等待集合**：通用 approval 与 legacy/timed question 的 stable request/call ID、所属 Agent/轮次、open-blocking/continued/settled 与是否实际仍在执行；动态插件激活请求另标域，不能当作整个任务阻塞。只传 ID/枚举，不需正文、reason、命令、答复或凭据。
3. **无控制副作用的订阅与恢复**：只读订阅可在快照前建立，快照返回宿主代际和明确覆盖范围/边界 N，后续事件可与 N 去重并识别缺口；必须覆盖 host-only turnBoundary 与等待变动，不能仅提供 client-visible projections。声明读取不会 activate/promote 冷 Session、claim 答复权、resolve 请求或发消息。
4. **版本/可用性依据**：给出支持这些契约的第一方版本/源码、必要 inject/权限、普通桌面实际服务组成，以及缺服务/key/权限/范围时的显式失败行为。未来可关闭探针只验证这些字段及订阅边界；在未获准阶段不执行。

可结束研究的新增证据应是上述完整读口与一致性契约的确切第一方依据，或在随后获准的最小探针中证明同实例覆盖；若上游明确缺失，则记录缺失契约与停止条件，再由真人决定是否改需求。当前结论仍是 **生产入口门槛未通过**，但已将“当前轮次读口无具体依据”缩小为“已定位版本相关 host-only 读口，待同实例验证”，并区分了两种审批域。
