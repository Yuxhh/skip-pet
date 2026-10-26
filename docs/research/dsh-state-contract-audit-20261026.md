# DeepSeek 完整等待与恢复接口复核

日期：2026-10-26（Asia/Shanghai）。关联 [研究 #37](https://github.com/xyd-0811/skip-pet/issues/37) 与 [完整等待及现态恢复 #41](https://github.com/xyd-0811/skip-pet/issues/41)。本次只读源码，没有安装或加载探针，没有获取等待 claim、接管 answerer、发送消息或读取真实会话内容。

## 结论与身份

**当前安装版的轮次、部分问题投影及同步采样有具体源码依据；完整真实人工等待和执行状态不能由本次已审计的公开观察接口重建。** 对这些接口，已能指出具体缺项；不能扩大成“整个上游绝对没有其他入口”。

主代理重新读取 `D:/deepseek harness/resources/app.asar` 的静态元数据及指定程序源码，核验 `0.2.1-rc.2`、构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986`、dirty=false；ASAR SHA-256 `47874618bf5b3011fcaac10cd4c85f69da333e70d4f99b921207c78d0999512a` 与旧包相同。Agent、Agent Loop、Approval、User Questions 四个成员逐字匹配。身份与日常实例的健康记录见[安装版补证](../verification/issue-37/README.md)；因此旧研究的静态安装身份疑问已补证。现有桥在日常实例继续发布，不证明尚未实现的完整等待服务已可注入。

安装源码：`.scratch/sukuna-pet/research/deepseek-local-evidence/dsh/node_modules/@deepseek-ai/`；新提取的 Session 和 Session Projection 在 `.scratch/issue37-verification/installed-source/`。以下安装行号均针对这些字节。公开比较基线为 [`22ddee3792402c3e70ec5f86a63c3e3e895a2f60`](https://github.com/deepseek-ai/deepseek-harness/tree/22ddee3792402c3e70ec5f86a63c3e3e895a2f60)，rc.2 标签为 [`687f282e8625c6b8d11ff58211a90524be2e4317`](https://github.com/deepseek-ai/deepseek-harness/tree/687f282e8625c6b8d11ff58211a90524be2e4317)。公开标签不是安装构建的逐字证明。

## 可用原料及限制

| 原料 | 安装源码依据 | 限制 |
| --- | --- | --- |
| live Agent 与直接 owner | `dsh-agent/lib/index.js:509–526,594–625`：get/list/roots/isOwnedBy | 可恢复直接运行时归属；没有父轮次身份，不能自动归到父 Agent 最新轮次 |
| 当前原生轮次 | `dsh-agent-loop/lib/index.js:1365–1412,1581`：注册 turnBoundary，含 openTurnStartSeq、lastTurn、lastStepBoundary | host-only，普通 snapshot 不输出；key 缺失为未知；开步骤不等于仍执行 |
| timed 问题 | `dsh-user-questions/lib/index.js:169–181,267–293`：open/continued/settled 投影 | 明确排除 legacy blocking，空集合不证明没有问题 |
| 同步投影读取 | `dsh-session-projection/index.js:119–155`：stateOf materialize 到当前 cursor，snapshot 同步返回 asOfSeq | client-visible 与 host-only 范围不同；只读最小字段，不异步持有或修改 live state |

较新版本推荐消费者注入领域服务并使用领域方法，例如 [AgentRegistry.turnBoundaryOf](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/core/agent/src/index.ts#L301)；不能将旧 keyed reader 无条件跨版本沿用。

## 完整等待的具体缺口

### 普通审批

安装 `dsh-user-approval/lib/index.js:128–143` 先写 approval/asked，再 await decide。`decide:172–188` 可能被策略拒绝，也可能等待机器或 UI answerer；asked 数据没有 human-pending 分类。该服务没有公开 pending 枚举方法或权威 pending collection。公开 rc.2 对照为 [request/decide](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/interaction/user-approval/src/index.ts#L215)。

机器 answerer 尚未返回与 UI 正在等待人类，此时都可以只有 asked、没有 decided；完整回填也只能恢复“审计未配对”。策略为 ask 不能排除机器处理。UI 的实际 pending 对象属于 [客户端 answerApproval](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/client/ui-approval/src/client/index.ts#L47) 的答复生命周期，没有据此证明宿主插件可安全枚举全部等待。

动态插件 cordis/request-run 属另一审批域。参考 [dsh-pet 桥](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/integrations/dsh-pet-bridge/index.js#L901) 也明确不将裸 asked 升级为等待。

### Legacy 与 timed 问题

安装 `dsh-user-questions/lib/index.js:613–650` 仅 askTimed 登记 waits；`ask:668–690` 直接等待 answerer waterfall，不登记该集合，投影又排除 legacy。晚加载时组合 timed 投影与 waits 仍不完整。

公开源码把 [waits 声明为 private](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/interaction/user-questions/src/index.ts#L82)。安装 bundle 中属性可见不构成第三方 API；`attachWait:595–600` 会取得影响倒计时的 claim，answer 会提交答复，均不作被动观察读口。公开对应为 [attachWait](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/interaction/user-questions/src/index.ts#L214) 与 [askTimed](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/interaction/user-questions/src/index.ts#L239)。

### 执行与轮次归属

安装 `dsh-agent-loop/lib/index.js:790–791` 的 status 把 idle/maintenance 之外都称 running；`1044–1166` 在 running phase 内等待工具结果。开轮次、开步骤和 status=running 均不足以排除人工阻塞；还需区分同轮并行工具及子代理是否继续执行。直接 runtime owner 又不自带父轮次/委派调用身份，因此不能由这些原料自动完成 #41 的任务归并。

## 一致性：同步采样路径可以推进

安装 `dsh-session/index.js:1481–1486,1579–1595`：append 先 log.push，然后同步通知 session/event 观察者。安装 Projection 的 `stateOf:126–131` 会补至 Session 当前 cursor；`drive:401–423` 跳过已达到水位的 cell。这让读取者不必依赖自己监听器与 Projection 监听器的先后顺序。

**源码推论，非实机通过**：同一宿主线程内先注册生命周期及 session/event 监听，再无 await、timer 或异步 I/O 地同步枚举 Agent，并读取各 Session cursor 和必要投影，可得到调用栈内的切面；各 Session cursor 组成边界向量，不必伪造跨 Session 全局序号。回调错误、缺号、key/schema 缺失均转未知。同步复制 ID/枚举，不持有 live state 引用。

要核验注册投影同步、无任务控制副作用，并覆盖 Agent 生命周期与所需 host-only 事件。公开 [Projection 文档](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/session/session-projection/README.md) 也要求同 tick 读取保持一致切面。onChanged 仅覆盖 wire 单元，不能独自覆盖 turnBoundary。同步切面不会补出缺失的等待字段，也不能自动把所有运行时状态归入 Session 水位。

## 新版本定点核对

2026-10-26 通过官方 GitHub API 再核对，master 仍为 `22ddee3792402c3e70ec5f86a63c3e3e895a2f60`，与上述较新公开基线相同。rc.3 标签对应 `1f81c047fc48fa190a683e469daa699857e9afe8`；定点取回其两个服务全文，而非仅由 release notes 推断能力。

- rc.3 的 [ApprovalService.request](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/interaction/user-approval/src/index.ts#L215) 和 [decide](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/interaction/user-approval/src/index.ts#L267) 仍是审计先行、随后 policy/answerer waterfall；该服务未增加真实人工 pending 的枚举接口。
- rc.3 的 [waits](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/interaction/user-questions/src/index.ts#L81) 仍为 private，仅 [askTimed](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/interaction/user-questions/src/index.ts#L234) 登记；[ask](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/interaction/user-questions/src/index.ts#L287) 直接 waterfall，[attachWait](https://github.com/deepseek-ai/deepseek-harness/blob/1f81c047fc48fa190a683e469daa699857e9afe8/packages/interaction/user-questions/src/index.ts#L216) 仍取得 claim。这两个服务的所需缺口未因 rc.3 而消失。

这是对指定服务的有界源码结论，没有升级或运行 rc.3，也没有排除其他未审计服务可能提供受支持入口。

## 下一步和停止条件

当前已审计接口不足以满足完整等待要求，按既有停止条件，无需先安装诊断插件或让用户制造真实审批去弥补字段缺失。可以静态核对并将完整等待能力记录为未证实；完整能力实机验收须先取得足够契约。

上游最小确认项：可由第三方插件注入的 human-pending、legacy/timed wait 只读枚举，实际执行与父轮次关联，及相应订阅/同步采样支持条件。主代理已取得用户明确授权，将[精简确认单](dsh-state-api-request.md)发布至[官方 Q&A #11053](https://github.com/deepseek-ai/deepseek-harness/discussions/11053)，并回读核对作者、分类及完整正文。发布不等于维护者认可或答复。

对 #37 可给出的确定负结论是“当前安装版本次审计的公开接口不足以满足完整接入要求”；不能宣称上游所有其他入口均不存在。研究收口不自动解除 #41 的技术前提。
