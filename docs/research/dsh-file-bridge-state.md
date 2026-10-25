# DeepSeek 文件桥完整现态入口：有界源码调查

2026-10-26（Asia/Shanghai）。研究问题：[DeepSeek 文件桥完整现态入口能否满足只读接入门槛](https://github.com/xyd-0811/skip-pet/issues/37)。本报告只读本地已保存的一手源码与已有提取证据，没有执行目标、安装插件、改宿主、读取实际日志/凭据/聊天正文或运行探针。

## 结论

**dsh-pet 的文件桥及消费者不能直接提供本项目要求的首次/重连全量状态。宿主源码确有 live Agent 枚举、运行根归属及带序号的投影快照原料，但完整真实等待集合、公开稳定的当前轮次取态及无副作用的联合快照仍未证明。** 因此可以确定“文件桥须增加权威现态导出与健康发布”的设计，仍不能把本研究结论写成生产接入已具备全部入口或实机已通过。

## 证据身份与边界

- 用户指定的 dsh-pet 源码固定在 `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e`，本地路径 `references/dsh-pet-indesktop/`。以下上游链接均固定此提交。
- 宿主证据复用此前只读提取目录 `.scratch/sukuna-pet/research/deepseek-local-evidence/`。其 `manifest.json` 标明来源 ASAR SHA-256 `47874618bf5b3011fcaac10cd4c85f69da333e70d4f99b921207c78d0999512a`。此前身份调查记录为桌面 `0.2.1-rc.2`、构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986`，见[已有研究](https://github.com/xyd-0811/skip-pet/blob/1089112810ddcad6b291a793454ab35051f28e03/.scratch/sukuna-pet/research/dsh-observer-2026-10-25.md)。本次没有重新核验当前运行安装包或证明所有成员都被提取；本报告的宿主结论限于这些保留字节。
- 重新计算的重要宿主文件 SHA-256：`dsh-agent/lib/index.js` 为 `7b59cf82c2784c25bdce4e3e24e5e5303b02b9f1003efacf50255492d17baf8b`；`dsh-agent-loop/lib/index.js` 为 `cf57e3ecd487ac5c2553455aaa5cef2c6fb41e6bd61be5aa455675d1d7193033`；`dsh-user-questions/lib/index.js` 为 `e1c51afac2e31be8593c6426976e5f31dbe2a709b85ae1ea43ed406146f54265`；`dsh-user-approval/lib/index.js` 为 `6a5ad1ba3c3dc3abbbae52e6c8c4463970ee0c1c8988cebb0d5cf2acd17ee90b`；`dsh-api-session-controller/lib/index.js` 为 `a9801acb577b03053c5d5a3191ff555c5f1d791d0acddec113bea4511e33b386`。

## 能力矩阵

| 能力 | 源码已证明 | 尚不能声称 |
| --- | --- | --- |
| 全部 live Agent | 保留宿主 `dsh-agent/lib/index.js:311–332, 611–625` 的 `AgentRegistry` 暴露 `ctx.agents.list()` 和 `roots()`，返回注册表中现有对象的新数组；`get(id)` 为精确 live 对象查询 | list 不等于当前运行任务列表。`Agent.status` 把等待审批/回答也算 running；所有活动工作是否均在这个服务以及插件是否拿到同一根服务，须以普通桌面实例探针确认 |
| 根与子 Agent 归属 | 同文件 `enter(agent, owner):509–526` 保存显式运行时 owner，`isOwnedBy(id, owner):604–608` 查询；`roots()` 取 owner 未定义的项。源码明确运行时父子关系与持久化 Session lineage 不同 | 不能用历史 fork parent 代替本轮子代理归属；也未证明一个运行根下面没有 detached/并发工作等边界遗漏 |
| 稳定原生轮次 | `dsh-agent-loop/lib/index.js:938–949` 将原生 `turn` 递增并写 `turn/start`；运行 phase 保存 `turn/step`，`throwError:878–887` 使用该值。dsh-pet [sourceTurnOf/writeStateEvent](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/integrations/dsh-pet-bridge/index.js#L483)转发原始回合号，消费者 [TurnCompletionTracker](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/dsh_state.py#L198)绑定 session/原生回合号以抵御迟到副本 | 原生轮次并非不存在，但本次未证实向第三方插件承诺的“读当前活动轮次”接口。直接读 `agent.phase.turn` 是具体 driver 的内部字段，不应无条件承诺跨版本或所有 Agent 实现。仅从未来 turn/start 自造编号不能恢复插件重载前的任务身份 |
| 真审批等待 | dsh-pet [真实请求监听](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/integrations/dsh-pet-bridge/index.js#L803)只在 `requiresApproval === true` 写 `cordis/request-run`，并配对 resolved；这比普通 approval/asked 审计事件更精确 | 本次读取保留的 `dsh-user-approval/lib/index.js`，只核到请求/策略/answerer 与 asked/decided 审计，没有确认供观察插件读取“当前全部真实未决审批”的公开 list/snapshot。保留提取目录不包含完整 Cordis 请求服务，不能据此断言其他模块绝无该能力。禁止通过替换 answerer 或响应请求来补快照 |
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
