# #54：右键菜单设置入口与安装版更新

## 用户更正后的最终结果

2026-10-27（Asia/Shanghai）。用户更正要求为：“退出”始终在最后，“桌宠设置”紧邻其上方。源码和说明已按此调整，并再次更新本机安装版。下方早期顺序已被本次更正取代。

- 当前安装包：`dist/menu-exit-last/release/Setup.exe`，版本 0.4.0。
- 当前 Setup SHA-256：`cb0d4dfc19579fdaef44c8cbd69913c0e3c0389e9f59129e7e6e56f35633daca`。
- 锁定环境重建成功，冻结代码与本次源码一致；安装器退出 0，186 个安装文件与新包逐一校验一致。
- 6 项菜单相关测试通过，日志 `.scratch/menu-exit-last-tests.log`；Windows Qt 仍输出 0x8001010d 诊断，测试进程退出 0。
- 安装目录的隔离运行检查退出 0，结果 `.scratch/menu-exit-last-installed-verification/result.json`，凭据、会话、窗口生命周期、偏好兼容和 CA 加载检查均通过。
- 实际打开安装版右键菜单，确认底部为“调整大小 / 桌宠设置 / 退出”，退出是最后一项。验证后保留桌宠运行。
- 偏好文件前后 SHA-256 仍为 `7c5efffcd1318410abd3aae3d3c3de5ebf51a1ab3377d1bae5053998f23655ea`。
- 沿用固定 dsh-pet 的原生 QMenu 动作顺序与当前用户 Inno 覆盖安装机制；没有改动桥接或聊天实现。#53 作者试聊验收仍独立待完成。

## 早期安装记录（已被用户更正）

2026-10-27（Asia/Shanghai）。按用户要求将“桌宠设置”移动至角色右键菜单最后一项，位于“退出”之后；随后按用户要求构建并更新本机安装版。

- 新安装包：`dist/menu-settings-bottom/release/Setup.exe`，版本 0.4.0。
- Setup SHA-256：`fe56a6eff0d8a368f76096412db9b8e1cf8908bc2087108d627edd4d5ed031d3`。
- 使用既有 `.scratch/i28e` 锁定环境和 Inno Setup 6.7.3，构建脚本检查全部冻结模块与当前源码一致。源码 ZIP、build-report.json、SHA256SUMS.txt 同目录。
- 退出旧桌宠后通过 Inno 安装器覆盖当前用户原安装目录，安装器退出 0；逐文件检查安装内容与报告 bundled_files 一致。
- 原偏好文件安装前后 SHA-256 均为 `7c5efffcd1318410abd3aae3d3c3de5ebf51a1ab3377d1bae5053998f23655ea`。
- 实际安装目录运行 `--verify-installation` 退出 0，凭据与会话的隔离合成检查、原生窗口生命周期、偏好兼容和 Windows CA 加载均通过。结果位于 `.scratch/menu-settings-bottom-installed-verification/result.json`。
- 通过 computer-use 打开实际安装版右键菜单，确认底部顺序为“调整大小 / 退出 / 桌宠设置”，设置是最后一项；收起菜单后保留桌宠运行。
- 源码阶段 6 项菜单相关检查通过；扩大检查另有 2 项连接测试超时，详见 #54 评论。本次没有改动连接实现。

参考固定 dsh-pet `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e` 的原生 QMenu 建树与 Inno 当前用户覆盖安装机制，继续沿用本项目既有实现。新包是工作区实际快照；未公开发布，#53 作者试聊验收仍独立待完成。
