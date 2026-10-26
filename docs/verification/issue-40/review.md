# #40 双轴代码审查

审查技能：`code-review`。固定范围 `git diff 097f1f1...8a680cd`，只包含 #40 实现；`097f1f1` 是并行聊天已提交的 #39，不将其混入本票审查。两位独立审查代理分别读取规范及 Issue 要求，后续复查修复工作树。

## Standards

初审：没有文档规范违反；1 项判断性建议——消费和留存清理重复实现有界 JSON 信封读取。

处理：抽出 `bridge_protocol.read_envelope(path, limit)`，统一实际读取上限、链接拒绝和 JSON 对象校验。复审确认已解决；新增 `_Tail.at_end`、轮次记录保留及结束字段校验职责一致，无新增可操作问题。

最终：0 项未解决，0 项硬性规范违反。

## Spec

初审发现三项 P1：

1. 新快照省略已结束的根任务时丢失轮次记录，随后迟到状态可复活任务。修复：快照更新活动集合时保留有界轮次及结束记录；新轮才替换对应旧轮记录。公开文件测试 `test_omitting_ended_root_in_snapshot_does_not_erase_round_watermark` 先失败后通过。
2. 待消费数据超过 1MiB 后仅跳到 EOF，校验片段还指向旧位置，误判重写并永久无法恢复。修复：所有跳过路径统一用 `_Tail.at_end` 同步 inode、偏移和校验片段。`test_overflow_skips_to_consistent_cursor_and_recovers_without_log_rewrite` 先失败后通过。
3. 观察快照含旧轮闲置子代理时被整体拒绝，阻挡当前根轮恢复。修复：合并根轮边界并过滤已过时的子代理行；仍拒绝当前根轮回退或复活。`test_old_idle_child_in_observed_registry_does_not_block_recovery` 先失败后通过。

复审逐项确认三处修复，35 项恢复测试通过。观察快照、实际文件系统/原生 Qt 与完整宿主覆盖的证据边界表述恰当。

最终：3 项发现全部解决，0 项未解决。

Standards：0 未解决；Spec：0 未解决。各轴原始发现与修复分别保留，不合并排序。
