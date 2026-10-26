# 接入安装与自动维护代码审查

用户确认的固定起点为 `8ff3604`。本票提交为 `097f1f1`、`98d99f8`、`cdb1035` 及最后的卸载事件接线与验收记录；中间的 `8a680cd` 属于并行文件桥恢复议题，审查按本票文件过滤，不将其当作安装维护改动。

按 code-review 技能分别由两个只读子代理执行 Standards 与 Spec 审查，随后各自复核修复。

## Standards

最终复核通过，0 项硬性违规，0 项待处理 smell。

初审的三个非阻断判断均已处理：单帧 summary 统一读取、manifest 类型验证集中在读取边界、关闭状态用于禁止后续启动及异步结果消费。共享副本保留、互斥锁错误类型和重试均服务于既定需求，未发现新的明显无用抽象。

## Spec

最终复核通过，0 项待处理。

已修正并验证：

- 卸载程序目录时，仍在使用的共享桥会复制并重连至独立用户数据目录。
- 启动遇到其他实例维护锁时退避重试，取得占用登记后再开启监测；关闭后不再重新启动。
- 用户指定 registry 版本时保留版本选择，但实际插件缺失会报告失败，不保存虚假成功。
- 共享副本复制期间检查配置和物理链接变化，先于删除旧链接拒绝用户后续修改。
- 迁移日志同时证明旧、新依赖的归属，最终 owner 写入失败仍能重试清理；pnpm 已移除依赖而 bundle 写失败也可重试。
- 卸载清理在用户确认后、删除程序文件前执行；失败阻止删除，取消卸载不改变接入。

最后一项对照锁定版 Inno 官方源码核实：[初始化与确认顺序](https://github.com/jrsoftware/issrc/blob/is-6_7_3/Projects/Src/Setup.Uninstall.pas#L685)、[fatal 异常处理](https://github.com/jrsoftware/issrc/blob/is-6_7_3/Projects/Src/Setup.Uninstall.pas#L341)、[确认后的清理事件与实际删除顺序](https://github.com/jrsoftware/issrc/blob/is-6_7_3/Projects/Src/Setup.Uninstall.pas#L726)。最终脚本已由 Inno Setup 6.7.3 编译通过。

最终计数：Standards 0 项待处理；Spec 0 项待处理。
