# 右键菜单 AI 对话无响应：修复与验证

任务：https://github.com/xyd-0811/skip-pet/issues/62 。用户确认入口是桌宠右键菜单。

## 排查与修改

安装版 0.4.1 的 22 个冻结模块与修改前源码一致；隔离安装自检、使用本机聊天记录副本直接打开窗口均通过。旧测试替换 QMenu.exec 或直接触发 action，未覆盖真实弹出菜单循环。

新增真实 QMenu.exec 回归，观察到旧实现于嵌套菜单循环中打开窗口（QThread.loopLevel 为 1，期望为 0），也曾出现最小化恢复/关闭重开后窗口未显示的失败；原生窗口恢复失败未稳定复现，不能将其宣称为用户现场唯一原因。

桌宠右键和托盘两处 AI 对话 action 均改为 Qt QueuedConnection，让菜单事件分发返回后再构造、显示和激活聊天窗口。参考固定提交 34d810b1eadd98d00e7cb9b3b51428a45b5bf03e 的 references/dsh-pet-indesktop/pet/app.py 中 open_modern_chat 和 _defer_while_popup_active；本项目用信号队列处理这两个同步 action 入口，保持既有单窗口复用与会话逻辑。

## 验证

- 真实菜单回归覆盖桌宠/托盘入口首次打开、最小化恢复、关闭重开、同一窗口复用及菜单循环外激活。
- 菜单、聊天窗口、托盘、会话窗口、设置和模式回归：37 passed，23.08 秒。沙箱内四个回环 HTTP 测试最初超时，在允许本机回环连接的环境原样重跑通过。
- 打包回归：3 passed；mypy src：23 个源文件通过。相关文件 diff 检查通过；未修改工作区已有的无关改动。
- 新增冻结安装自检：通过真正的 PetWindow.contextMenuEvent 选择 AI 对话，确认 action 触发时尚未同步构造窗口，菜单返回后聊天窗口可见。源码、冻结候选和实际安装目录三处均通过。
- 原生测试期间 Windows COM 的已处理异常 0x8001010d 会被 pytest faulthandler 打印；最终回归关闭该诊断插件，未跳过测试或放宽断言。

## 本机交付

构建输出：dist/chat-menu-fix/release/；版本保留 0.4.1，未公开发布。

原位更新 C:/Users/xing/AppData/Local/Programs/SukunaPet，安装器返回 0。186 个安装文件与构建报告逐个 SHA-256 相符；原 mode.json 和现有会话文件哈希保持不变。安装版自检返回 0，native_context_menu_opens_chat_after_popup=true。已启动更新后的桌宠。

原始记录：.scratch/chat-menu-native.xml、.scratch/chat-menu-build.log、.scratch/chat-menu-install.log、.scratch/chat-menu-installed-after/result.json。聊天记录副本已清理，未发起服务商请求。

自动化检查完成；用户现场原症状是否消失，仍以更新后从右键菜单复点的结果为准。
