# 桌面启动找不到 pnpm：修复与验收

日期：2026-10-27（Asia/Shanghai）。任务：[修复桌面启动找不到 DeepSeek 自带 pnpm 导致任务接入失败 #61](https://github.com/xyd-0811/skip-pet/issues/61)。

## 原因与改动

安装版预检实际显示“找不到 pnpm JS 入口；可用 --pnpm-cli 指定现有入口。”。同机继承开发终端 PATH 时预检通过，清空 PATH 时复现失败。pnpm 仅在开发终端可见，但 DeepSeek 实际另有自己管理的 Node/pnpm；原工具发现逻辑没有检查其运行时目录。

在现有工具发现之后补充 `DSH_HOME/dsh-runtimes/dsh-primary-runtime/dependencies/pnpm`，未设置 DSH_HOME 则使用用户的 `.dsh`。Node 缺失时使用同目录的 `node/bin`。环境提示支持文件或入口目录，失效后继续自动发现。

对照参考固定提交 `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e` 的 `pet/agent_link/__init__.py` 中 `_resolve_cli_hint`、`_find_pnpm_cli` 和 `_pnpm_command`。沿用提示回退和 Node 直调 JS；Harness 管理的运行时目录是本项目针对此次故障新增的搜索位置，不安装全局工具。参考工作树保持干净。

## 验证

- 新增 `tests/test_bridge_tools.py`。修复前 **4 failed、1 passed**，修复后 **5 passed**；覆盖无终端 PATH 的完整预检、自定义 DSH_HOME、默认用户目录、文件/目录提示和失效提示回退。
- 使用实际 Harness 的 Node/pnpm、禁用 `_which` 并清空 PATH，在含空格的隔离 profile 中真实安装插件成功；配置备份、bundle 登记和实际插件入口均存在。
- 接入安装/卸载/桌面控制/恢复/协议回归 **76 passed，84.98 秒**。第一次沙箱内运行有 15 项因 pnpm 无法建立 Windows 目录链接而失败；在允许目录链接的原生环境中重跑全部通过，未修改测试断言来回避错误。
- `mypy src`：**23 个源文件通过**。相关改动 `git diff --check` 通过。
- 构建输出：`dist/issue-61/release/`，版本仍为 **0.4.0**；Setup、源码 ZIP、构建报告和 SHA-256 清单齐全。冻结模块由构建脚本校验与当前源码一致。
- 更新原用户安装目录 `C:/Users/xing/AppData/Local/Programs/SukunaPet`，安装器返回 **0**；**186 个安装文件**与构建报告逐个哈希相等。
- 使用空 PATH 为实际 `~/.dsh/profiles/desktop` 恢复安装版随包插件，保留备份 `sukuna-bridge-backup-20261027-225226-862632`。依赖归属、bundle 和链接目标均验证正确。
- 当前原偏好为 `click`，接入关闭。按用户要求恢复任务响应后保存为 **task 模式、接入启用、320px**，其余设置通过原保存入口保留。
- 已安装程序 `--verify-installation` 返回 **0**，冻结运行、合成凭据/会话跨进程恢复、生命周期、偏好兼容和 TLS CA 检查通过。启动安装版时清空 PATH，后台 refresh 没有报错。
- 用户正常重开 DeepSeek 后，明确反馈：**“重开后已恢复跳动”**。据此确认用户报告的真实任务联动故障已解决。

原始隔离测试、构建、安装和自检记录保存在 `.scratch/deepseek-tools*`。本次没有改动 DeepSeek 的对话、审批或任务执行逻辑，也未向宿主注入模拟任务来充当真实验收。
