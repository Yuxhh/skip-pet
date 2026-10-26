# 上游接口确认单

状态：用户于 2026-10-26 明确批准后，已通过其账号 `xyd-0811` 发布至 [deepseek-ai/deepseek-harness · Q&A #11053](https://github.com/deepseek-ai/deepseek-harness/discussions/11053)。已回读核对作者、分类、标题及正文与获准稿完全相同；未附本地验证文件、路径、PID、会话标识或硬件信息。以下保留提交正文，不表示已获维护者答复。

标题：**[API question] Read-only recovery of actual human waits and execution state in desktop plugins**

---

我们在普通 Windows DeepSeek Harness 桌面实例中开发一个只读状态观察插件，希望在插件晚加载或重载后恢复当前任务状态。只导出必要 ID 和状态枚举，不导出聊天、问题、命令或答复正文，也不改变审批或任务执行。

目标安装版本是 `0.2.1-rc.2`，构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986`（dirty=false）。我们已对照实际安装字节，公开 rc.2 标签仅作为可链接的源码参考，不假定二者逐字相同。如果新版已有支持路径，请指出最低版本。

任务口径：一个聊天的一轮请求算一个任务，内部子代理归入该轮。只要内部仍有助手执行工作，即使同时待批准或待回答，仍属于运行；有真实待操作事项且内部已无执行时，才属于等待。

## 1. 通用审批：怎样只读枚举当前真正等待人的请求？

在 [`ApprovalService.request/decide`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/interaction/user-approval/src/index.ts) 中，`approval/asked` 写于 policy/answerer 决策之前。因此 asked/decided 未配对，可能是人类等待、机器 answerer 尚未返回或历史尾部，单凭审计对无法区分。

- 第三方插件是否有可依赖的只读入口，枚举真实人工 pending 请求并返回 request/call ID、所属 Agent/原生轮次及实际阻塞关系？
- 若推荐回填审计或使用某个投影，怎样可靠区分上述情况，并排除取消、重载及崩溃后的残留？

动态插件激活的 `cordis/request-run` 属于独立域，我们不把它当作通用工具/命令审批全集，也不把 pending 激活当作整轮停止。

## 2. 问题与执行：怎样被动恢复 legacy/timed 等待及继续执行状态？

[`UserQuestionService`](https://github.com/deepseek-ai/deepseek-harness/blob/687f282e8625c6b8d11ff58211a90524be2e4317/packages/interaction/user-questions/src/index.ts) 的 `userQuestions` 投影排除 legacy blocking；foreground waits 仅在 `askTimed` 路径登记。`attachWait` 会取得 claim，`answer` 会提交消息，均不适合作为纯观察入口。

- 是否已有覆盖 legacy 和 timed 的只读枚举/变更接口，能区分 open-blocking、continued、settled，并给出 Agent/轮次/调用 ID？
- 怎样判断该 Agent 或同轮子代理仍有执行？Agent `status=running`、open turn、未闭合 step 均可能包含人类等待。
- 若没有现成接口，能否明确当前不支持的范围，以及适合补充观察服务的位置？

## 已找到的一致性原料

已安装版的 `Session.append` 在提交后同步通知 `session/event`；`sessionProjections.stateOf` 将状态推进到当前 Session 水位，`snapshot(session, [])` 可同步取得该水位而不导出 wire 正文。我们考虑先监听，再在一个无 await 的同步读取段枚举 live Agent、运行时 ownership 和 host-only `turnBoundary`，随后继续接收事件；不要求跨 Session 全局序号。

这个组合是否属于受支持的插件使用方式，有无重入/生命周期限制？目前我们将它视为版本限定的采样候选，并未由此推断完整等待和真实执行已可读取。

希望回复给出可用的服务/方法/事件、所需 inject/权限、desktop profile 适用范围、最低版本及缺能力时的行为。若目前确无覆盖全部语义的被动接口，明确这一点也有助于我们停止完整能力验收并保留未知。谢谢！
