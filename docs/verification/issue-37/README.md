# 完整现态入口：当前安装版补证

2026-10-26（Asia/Shanghai）。对应 [研究 #37](https://github.com/xyd-0811/skip-pet/issues/37) 和 [执行 #41](https://github.com/xyd-0811/skip-pet/issues/41)。用户已授权继续推进，真实审批、回答及对外提交需要时再请用户配合。

## 当前安装版身份

只读核验 `D:/deepseek harness/resources/app.asar`，未修改宿主文件。版本为 `0.2.1-rc.2`，构建 `332895e0f7c9d4dbfb29729f5eb367fa263ff986`，dirty=false。整个 ASAR 的 SHA-256 与此前调查的来源完全相同；Agent、AgentLoop、UserApproval、UserQuestions 四个关键实现逐字节匹配保留源码。因此此前对这四个模块的安装版源码结论适用于当前磁盘安装包。

逐项哈希见 [installed-identity.json](installed-identity.json)。其中 `matches_preserved_source=false` 的 Session/SessionProjection 表示此前提取目录没有对应文件，本次另存供阅读；不表示发现了新旧字节差异。未宣称该安装构建与公开标签逐字同版。

## 日常桌面实例

从本项目自有文件桥快照只选取版本、profile 哈希、协议能力、代际、健康及 Agent 数量字段，见 [live-bridge-identity.json](live-bridge-identity.json)。PID 90916 的宿主版本为 `0.2.1-rc.2`；profile 哈希与真实 `~/.dsh/profiles/desktop` 相符，间隔 1.5 秒读取时同代际 `health_seq` 增长。系统进程只读核对显示该 PID 是日常 `DeepSeek Harness.exe` 实例的进程之一。

这证明既有插件在当前日常实例继续发布。它声明 `observed-state`，不证明权威完整等待集合、晚加载覆盖或完整恢复。本次没有创建测试任务、触发真实审批、读取聊天或问题正文、接管答复权、重启宿主或安装额外探针。

## 下一步门槛

完整等待和执行契约的补查见 [源码复核](../../research/dsh-state-contract-audit-20261026.md)。先完成只读能力判断；若已有源码说明缺少所需契约，按原研究的停止条件停止完整能力验收，不要求真人反复制造等待来代替接口证据。

上游确认单经用户明确批准，已发布至 [官方 Q&A #11053](https://github.com/deepseek-ai/deepseek-harness/discussions/11053)，并回读核对正文。#37 和 #41 的验收条件及原生依赖保持不变，不以发帖或本次版本核验冒充完整入口通过。现等待受支持接口路径或缺能力范围的明确依据。
