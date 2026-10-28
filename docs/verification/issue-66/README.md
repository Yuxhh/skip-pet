# AI 对话无响应复发 · 0.4.7

2026-10-28；任务：https://github.com/Yuxhh/skip-pet/issues/66 。

现场只有一个 0.4.6 进程，25 个冻结模块与源码一致；重复点击后 Windows 聊天窗口仍隐藏，未最小化且坐标在屏内。正常退出并启动诊断源码后，用户确认窗口出现；未证实最初操作序列。

新增重入菜单回归在旧版两入口均失败：QueuedConnection 仍可能在原生菜单跟踪期间执行。对照 dsh-pet 34d810b1 的 pet/app.py:988，打开前等待 activePopupWidget 消失；单次计时器合并重试，退出取消。增加零参数 Qt 槽。

ChatWindow.showNormal 后查询 Windows IsWindowVisible，若仍隐藏则 hide/showNormal 重新呈现同一实例。旧冻结候选正常启动自检通过、隐藏启动 AssertionError；未捕获断言位置，不能断言其唯一根因。最终冻结自检受审批连续超时影响未完成，受限环境补跑在合成凭据阶段 OSError。

最终相关回归 58 passed（29.84 秒），mypy 26 个文件通过。报告 `.scratch/chat-reopen-20261028/final-tests.xml`。保留首次打开、关闭重开、最小化恢复、草稿、会话和音乐行为。

用户授权原位更新，通过安装器界面完成 0.4.7 安装；235 个安装文件与构建报告哈希全部一致，25 个模块匹配最终源码。聊天 JSON 哈希不变；偏好从诊断开始已有变动，未回滚，也不宣称其全程哈希不变。未公开发布。

用户在最终安装版实测首次打开及关闭重开后明确回复“两次都正常”。这证明本机已恢复；完整隔离验收的缺口仍保留。最终包 `dist/chat-reopen-final-0.4.7/release/Setup.exe`。临时诊断留在 .scratch，不随包交付。

## 0.4.7 发布补验（2026-10-28）

用户随后授权推送 GitHub。完整回归 **396 passed，304.39 秒**，mypy 检查 src 与构建脚本共 **27 个文件通过**。同一最终冻结程序与实际安装目录的完整隔离自检均返回 **0**，包括隐藏启动下的菜单等待、Windows 原生可见性、关闭重开、合成凭据跨进程恢复与安全降级、合成会话恢复、兼容偏好和 TLS。此前审批超时留下的完整隔离验收缺口现已补齐。

原始补验证据见 [pytest-release.xml](pytest-release.xml)、[frozen-release.json](frozen-release.json) 和 [installed-release.json](installed-release.json)。发布保留用户验收过的 Setup.exe 字节，源码 ZIP 从本次提交的干净快照生成；构建报告分别记录原安装包的构建基点和本次发布提交。运行代码、素材、桥插件及实际安装文件逐项核验，发布不改动个人设置或聊天记录。

归档核验发现 Git 默认换行转换会改变桥插件字节。新增 .gitattributes 保留已打包桥文件的原始格式，源码归档也携带该规则；插件逻辑及本机文件字节不变。打包专项补测 3 项通过，类型检查仍为 27 个文件通过。
