# DeepSeek Harness 只读任务状态接口确认单

本地修订草稿，2026-10-26（Asia/Shanghai），尚未提交。建议提交至 [Q&A Discussions](https://github.com/deepseek-ai/deepseek-harness/discussions/categories/q-a)。关联：[DeepSeek 文件桥完整现态入口能否满足只读接入门槛](https://github.com/xyd-0811/skip-pet/issues/37)。

建议标题：**[API question] 插件能否依赖审批日志、问题等待信号和轮次投影，恢复只读任务现态？**

下方为可提交的 Discussion 正文。提交时使用上面的建议标题，复制分隔线后的内容。

---

## 使用场景

我们希望通过普通 Windows DeepSeek Harness 桌面实例中的插件，向独立状态指示器提供必要的任务身份和状态枚举；日常仍从原快捷方式启动 Harness。

一个任务对应一个聊天中的一轮用户请求，子代理归入所属轮次。该轮内部仍有助手执行工作时算运行任务，即使同时有未处理的审批或问题；有待处理事项且内部没有助手继续执行工作时，才算等待任务。

我们已找到 Agent 枚举、轮次投影及事件接口，希望确认以下组合是否属于第三方插件可依赖的观察契约，尤其是插件晚加载、重载与消费者重连时的语义。只导出身份和状态，不传问题、命令、答复或聊天正文；不通过接管 answerer、调用 `attachWait/answer/resolve` 来获取观察能力。

## 版本与已有路径

本机安装包内可核验：`0.2.1-rc.2`，`dshBuildCommit=332895e0f7c9d4dbfb29729f5eb367fa263ff986`，`dshBuildDirty=false`。该 SHA 未能从公开仓库取回。

本文用公开标签 [dsh-v0.2.1-rc.2](https://github.com/deepseek-ai/deepseek-harness/tree/687f282e8625c6b8d11ff58211a90524be2e4317) 作为 rc.2 文档基准，另将较新 master 快照固定在 [22ddee3](https://github.com/deepseek-ai/deepseek-harness/tree/22ddee3792402c3e70ec5f86a63c3e3e895a2f60)。公开标签与安装构建不视为逐字同版。已看到 [rc.3 预发布](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.1-rc.3)（2026-10-23）；如它已有相关能力，也请指出支持路径及是否需要升级。

已读到的路径如下，链接固定版本，正文以符号名区分接口：

| 范围 | 已知路径 |
| --- | --- |
| live Agent 与运行时归属 | rc.2 的 [`ctx.agents.list()/roots()/get()/isOwnedBy()`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/core/agent/src/index.ts)；运行时 owner 与持久化 Session lineage 不同 |
| 原生轮次及步骤 | rc.2 的 [`stateOf(session, 'turnBoundary')`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/session/session-projection/README.md)；22ddee3 推荐通过领域服务读取，例如 [`ctx.agents.turnBoundaryOf(session)`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/agent/src/index.ts) |
| 客户端轮次轮廓 | rc.2 的 [`turnOutline`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/session/session-turn-outline/README.md)；包括轮次号、起始 seq 和文本预览，不直接等于真实执行/等待状态，我们只需身份字段 |
| 审批 | rc.2 的 [`ApprovalService.request` / `hasOpenTurn`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/interaction/user-approval/src/index.ts)，以及 `approval/asked` / `approval/decided` 审计对 |
| 用户问题 | 22ddee3 的 [`userQuestions` 文档](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/subsystems/user-questions.md)：timed `open/continued` 投影排除 blocking legacy 问题；等待 claim 不落日志 |
| 快照与变更 | [`snapshot(session)` / `asOfSeq` / `onChanged`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/session/session-projection/README.md) 及 `session/event`；普通快照与变更通知仅覆盖 client-visible 单元，`turnBoundary` 为 host-only |

另已区分动态插件激活域：22ddee3 的 [`DynamicCordisRunnerService.inventory()/snapshot()` 与 `cordis/request-run`](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/extensions/cordis-host-runner/src/index.ts) 不作为普通工具审批全集；这些方法名也不假定在 rc.2 安装版存在。

## Q1：审批审计对的缺口重建，是否是可依赖的观察契约？

候选做法是按 Session 和请求 `id` 配对 `approval/asked` / `approval/decided`，用 `callId` 关联工具调用，再结合原生轮次。这样可形成“已 asked、尚未观察到 decided”的集合。rc.2 公开源码也已有 `hasOpenTurn` 前置检查；我们不因安装版没有名为 `approvalState` 的单元就认为没有该检查。

想确认：

1. 插件通过受支持的 Session 事件/投影读取与回填上述审计对，重建未决请求，是否属于官方可依赖的契约？它与 open turn、取消、崩溃尾部修复及重载后的存活请求是什么关系？
2. asked 先于策略与 answerer 决策写入。怎样把“尚未 decided”进一步区分为真正等待人类、策略自动处理、机器 answerer 尚未返回或历史残留？若没有这样的信号，请明确它只能表达审计未配对，而不能保证当前人工等待。
3. 晚加载时，能否仅从宿主内读取所需事件的 ID/枚举恢复状态，而不激活冷 Session 或接管答复流程？如果已有投影/领域服务，推荐哪条路径？

## Q2：host 侧能否被动区分真实问题等待与仍在执行？

我们理解 `userQuestions.active` 不覆盖 legacy blocking 问题；未闭合的 legacy 工具调用本身，也可能无法与普通长工具执行区分。timed 问题的 `open/continued` 与“当前是否有前台 claim”又是不同维度。

想确认：

1. 是否已有 host 侧只读信号，能区分 legacy 人工问题等待与一般未完成工具调用，并关联 Agent/轮次/调用 ID？
2. 对 timed 问题，是否有被动读取前台 wait/claim 状态的入口？`open` 是否足以判断执行被问题阻塞，还是必须另读等待生命周期？claim 的存在是否只表示 UI 接管计时，而不是整轮已无其他工作？
3. 如何区分 `continued` 后仍待回答但助手已经继续执行、等待已解除，以及缺服务或未覆盖类型造成的“未知”？

我们不将取得 claim 的 `attachWait` 或会提交回复的 `answer` 当作观察接口。

## Q3：已有快照、事件与归属读口的组合，对插件承诺哪些一致性和执行语义？

已知 `snapshot(session)` 同步返回带 `asOfSeq` 的 client-visible 一致切面，`onChanged` 提供相应变更，host-only 单元另有服务读取和 `session/event`。注册模型也有版本差异：rc.2 是同步注册/旧 keyed 读取；22ddee3 要求领域拥有者 await 注册后再暴露同步服务方法，消费者注入领域服务。

我们考虑先建立监听并缓冲，再在同一同步读取段取得快照与所需 host 状态，按该 Session 的 `asOfSeq` 去重并继续接收；若推荐的是无异步间隔的“先快照、立即订阅”，也希望了解其成立条件。想确认：

1. 第三方插件应采用哪种受支持的顺序？`session/event` 回调相对投影更新的时序有什么保证，读取 host-only `turnBoundary` 能否与 client-visible 快照建立同一边界？这里不将单 Session 的水位当作跨 Session 的全局序号。
2. 对子代理，我们会结合父轮次中的委派调用、子 Session 的轮次状态及运行时 ownership；不会用历史 fork parent 代替当前 owner。`list/roots/get/isOwnedBy` 是否足以恢复这种归属，如何处理父 Agent 开始新轮次、子代理销毁或脱离所有权等边界？
3. rc.2 的 [`agent-instructions.stepIsOpen`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/context/agent-instructions/src/index.ts) 使用以下候选判据：

   ```ts
   boundary.openTurnStartSeq !== null
     && boundary.lastStepBoundary?.kind === 'start'
     && boundary.lastStepBoundary.seq > boundary.openTurnStartSeq
   ```

   该判据承诺的是否仅是“步骤未闭合”，而非“助手仍在执行工作”？审批或问题等待发生在步骤内时，应怎样与 Q1/Q2 合并判断？`turnOutline` 可用于轮次身份，但其预览/边界能否承担更多状态语义？

4. Agent 创建/销毁、插件重载与宿主重启时，应组合哪些生命周期通知和稳定身份以避免旧状态复活？缺必需服务、key 或覆盖范围时，推荐怎样显式返回未知？

读取应不启动任务、不 promote 冷 Session、不取得答复权、不解除请求、不发送消息；允许正常投影计算和内部缓存行为。

## 希望确认的结果

请分别说明：上述候选组合是否受支持、服务/方法/事件名及依据、所需 `inject` 与权限、普通 desktop profile 的可用性、rc.2/rc.3 兼容路径，以及仍不能区分的状态。

如果只能覆盖“审计未配对”“步骤未闭合”等较弱状态，也请明确说明。我们会保留未知，不将这些候选直接视为完整真实等待或执行状态。谢谢！
