# 接入安装与自动维护验证

日期：2026-10-26（Asia/Shanghai）。执行票：[接入安装与自动维护](https://github.com/xyd-0811/skip-pet/issues/39)。安装管理、原生 Qt 菜单及卸载入口三个测试边界，以及审查起点 `8ff3604`，已由用户确认。

## 实现与参考

对照 dsh-pet 固定提交 `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e` 的 `DshMonitor.install_bridge`、`refresh_stale_bridge_links`、`uninstall_bridge`、`AgentLinkManager.set_enabled` 与 `uninstall_cleanup`，采用 Node 直调 pnpm、配置备份、bundle 登记、后台维护和共享占用保护。

必要差异：默认仅操作已存在的实际 desktop profile，不创建 web profile，也不遍历安装到无关 profile；本项目插件仍为 `@sukuna-pet/dsh-bridge`。只有拥有安装记录且依赖未被用户更改的本地链接参与自动维护或移除；registry 覆盖保留。缺失其他插件的路径提供明确诊断，不擅自猜测修正。

## 自动化验证

- `tests/test_bridge_install.py`：预检不创建 profile，真实 pnpm 安装与备份，旧构建及失效路径刷新，实际链接丢失修复，预检后配置变化，registry 与后续修改保护，多实例占用，无 pnpm JSON 移除兜底，多 profile 部分失败及重试，坏依赖诊断。
- `tests/test_bridge_desktop.py`：原生菜单拒绝/确认、后台慢安装期间帧继续推进、失败重试、开关成功后持久化、切换模式保持气泡、启动自动刷新与退出保留共享插件。Qt 测试使用隔离 profile；协议测试发布器提供身份、独立健康与观察快照。
- `tests/test_bridge_uninstall.py`：真实子进程经 `--uninstall-cleanup` 入口，跨进程仍有占用时保留，无占用时移除自己的条目并留下结果日志。

完整回归、类型检查及双轴审查结果将在最终提交前补记。

## 实际 desktop profile

普通桌面宿主为 `D:/deepseek harness/DeepSeek Harness.exe`，实际 profile 为当前用户 `~/.dsh/profiles/desktop`。使用本机 `C:/Program Files/nodejs/node.exe` 和已有 pnpm JS 入口，未安装全局工具、未修改宿主安装目录。

先将随包插件复制到项目内的临时旧构建目录，通过安装接口安装；随后使用当前随包目录的启动维护接口刷新。两次操作成功，最终依赖指向本项目 `src/sukuna_pet/integrations/dsh-bridge`，其他依赖、bundle 及配置的结构化比较一致。备份分别为 `sukuna-bridge-backup-20261026-124728-422009`、`sukuna-bridge-backup-20261026-124729-311695`。原始结构化结果保留于本地 `.scratch/issue39-live/install-refresh.json`。

以独立预览偏好启用原生产品窗口，接通真实文件桥，不覆盖用户原有播放模式。用户正常退出并重开 Harness、发送短测试任务后回复：“已重开并测试，气泡与联动正常”。同一次预览记录到：

| 本地时间 | 真实汇总与原生表现 |
| --- | --- |
| 12:48:43 | 运行任务 1，jump=true，气泡可见，动作从阶段 1 推进至 2 |
| 12:48:44 | 完成 1，运行任务归零；完成气泡可见，角色继续自然收尾 |
| 12:48:44.987 | 角色回到阶段 0，完成提示仍显示 |
| 12:48:52.187 | 完成提示到期，气泡隐藏 |

该次是同一个真实任务、实际文件桥与原生窗口的联动观察；只记录计数、状态、是否显示与阶段，不保存聊天正文或凭据。原始观察保留于 `.scratch/issue39-live/observations.jsonl`，预览 stderr 为空。

## 边界

新版 Setup 的构建、升级与真实安装版卸载属于[正式安装版与实机验收](https://github.com/xyd-0811/skip-pet/issues/42)，本次只验证源码的卸载入口并接入安装脚本。当前工作区另有文件桥协议的并行改动；本票只提交安装维护相关文件，不把协议或完整等待能力计为本票交付。
