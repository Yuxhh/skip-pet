# DeepSeek 接入安装与维护

源码启动：`.venv\Scripts\pythonw.exe -m sukuna_pet`。右键选择“启用 DeepSeek 接入”，预检完成后查看 profile、插件和 Node/pnpm 路径，确认才会安装。安装在后台执行，成功后保存接入开关；按结果提示正常重开 Harness。

默认只操作 `%DSH_HOME%/profiles/desktop`，未设置 `DSH_HOME` 时使用当前用户的 `~/.dsh/profiles/desktop`。缺少实际 profile 时报告错误，不创建替代 profile。不会安装全局工具；找不到现有 pnpm 时，可通过 `SUKUNA_PET_PNPM_CLI` 或 `DSH_PNPM_BIN` 指定现有入口后重启桌宠。

接入和播放模式分别保存。启用后选择“点击跳动”或“持续跳动”仍显示任务气泡；选择“任务联动”才由任务驱动自动播放。“关闭 DeepSeek 接入”停止该窗口监测，并在后台尝试移除自己拥有的插件。退出桌宠只释放该实例占用，不卸载插件。

启动已启用接入时，后台检查旧构建路径、失效目标和丢失的实际插件链接；只维护已安装且拥有安装记录的本地依赖。用户改为 registry 版本或安装后自行改变依赖时予以保留。CLI 参考版留下的旧安装可以通过菜单首次启用接管，不会凭一个无关 profile 宣称接通桌面。

安装、刷新、移除前备份 package.json、现有 pnpm 锁文件、workspace 配置及本项目安装记录；备份位于 profile 的 `sukuna-bridge-backup-*`。不整份还原旧备份覆盖用户后续设置。预检后配置已变化时要求重新预检；多个明确指定的 profile 部分成功会逐一报告，成功项不自动回滚。其他插件的缺失本地依赖会显示名称和路径，请修正后重试，不猜测替换其他插件。

多个当前版本桌宠使用进程占用记录保护共享插件。其他实例还在使用时保留插件；卸载程序目录前会把仍使用的插件复制到独立用户数据目录，并重连共享入口，避免留下指向已删除安装目录的链接。进程异常退出后的陈旧占用由操作系统进程锁判断。维护操作使用跨进程互斥锁；启动遇到锁冲突会在后台逐步延长间隔重试，取得占用登记后开启监测。缺 Node/pnpm 的移除和共享副本保留不依赖 pnpm，不递归删除链接目标。

命令行仍可使用 `python -m sukuna_pet.bridge_install inspect|install|refresh|remove`，重复 `--profile` 可明确指定多个已有 profile。`--pnpm-cli` 指定现有入口；`--maintenance-dir` 用于隔离验证。本项目的 `.sukuna-bridge.json` 是安装归属记录，修改后会失去自动维护与清理凭据。

原生启动器的 `--uninstall-cleanup` 参数会在创建桌宠窗口前分流。安装脚本在删除程序文件前调用该入口，清理失败会停止卸载并保留程序文件；结果记录在当前用户数据目录 `sukuna-pet/uninstall-cleanup.log`，后台安装维护诊断在同目录 `maintenance.log`。共享迁移先记录旧、新依赖归属，写入中途失败仍可重试。本次提供卸载接线，不代表新版 Setup 已构建或发布。

本次实现与验收见[接入安装与自动维护验证](verification/issue-39/README.md)。任务状态仍按当前文件桥的能力范围呈现；完整等待和现态恢复由独立议题跟进。
