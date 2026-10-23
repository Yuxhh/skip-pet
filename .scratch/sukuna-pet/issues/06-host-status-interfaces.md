# Codex 与 DeepSeek Harness 有哪些可用的任务状态接口

Id: 06
Parent: ../map.md
Labels: wayfinder:research
Type: research
Mode: AFK
Status: resolved
Assignee: inspect_reference
Blocked by: none

## Question

哪些官方事件、插件或生命周期接口能把 Codex 和 DeepSeek Harness 的任务状态传给独立桌宠？明确可证实的接入方向、宿主版本核验需求、桌面应用与 CLI 的覆盖边界，以及不能据文档推断为已验证的部分。

## Context

- 用户确认独立桌宠联动两个宿主，任务运行时跳动，空闲静止；不是单纯共存或内置宠物包导入。
- 最新范围：共有持续跳动、点击跳动、任务联动三种模式；本票的状态接口只影响任务联动模式。其他两种模式不应依赖宿主启动。
- 一手资料：[Codex hooks](https://learn.chatgpt.com/docs/hooks)、[DeepSeek Harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness)。这些页面已由父代理打开。
- 不将任意社区桌宠插件的存在视作官方协议。先完成有限文档调查，实际安装版本和端到端接入留作后续验证；不修改用户宿主设置。
- 初始仓库无提交，研究上下文保存在本票，不创建研究分支或提交。

## Comments

- 2026-10-23：已认领；只做接口研究，不编写适配程序或安装插件。

## Answer

2026-10-23：inspect_reference 完成一手文档调查，父代理保存结论。关闭本票表示接入方向调查完成，不代表本机端到端兼容已经验证。

### Codex 候选入口

[官方 Hooks 文档](https://learn.chatgpt.com/docs/hooks) 提供 UserPromptSubmit、Stop、Interrupt、SessionEnd 等生命周期事件，以及会话和部分回合标识，可作为开始、停止和中断信号的接入方向。不能将每次 Stop 无条件等同最终空闲：Stop 的处理可能导致继续运行。还需要确认实际版本、桌面端覆盖及错误和等待审批的表达方式。

### DeepSeek Harness 候选入口

[官方生命周期文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/agent-lifecycle.md) 说明实时 agent/status 的 running / idle 状态及回合生命周期；agent/* 属于实时状态方向，session/event 是可重放事实方向。[官方架构文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) 支持插件接入方向。建议通过 Cordis 插件订阅状态并转交独立桌宠，但仍需核验用户安装版本和具体事件签名。

### 建议的结构与尚未决定的部分

建议采用两个宿主适配器，汇入桌宠本地状态桥，再由三种模式中的“任务联动”模式消费状态。持续跳动和点击跳动两种模式不依赖宿主状态；没有运行宿主时，桌宠仍能独立使用。

“任一来源还有运行任务则跳动、全部无运行任务则自然收尾”只是可供后续讨论的建议，不是用户已确认规则。多会话、状态过期、断线恢复、等待审批、失败和中途续跑的优先级，均交由“三种模式与双宿主任务状态如何协同”确认。

仍需核验：本机两款宿主的版本与形态、桌面应用和 CLI 的覆盖边界、事件传输及初始化快照、重启后的状态恢复、实际配置入口和任务状态误判的验收方法。不使用窗口是否存在来替代任务状态，也不把社区桌宠包格式相似视为已完成联动适配。

研究未访问本机、安装插件、改动宿主配置或编写适配程序。
