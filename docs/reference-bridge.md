# DeepSeek 参考文件桥运行版

采用 dsh-pet 固定提交 `34d810b1eadd98d00e7cb9b3b51428a45b5bf03e` 的宿主插件、JSONL 与后台读取机制。完整现态要求仍为后续验收目标；本版快照标记 `coverage=observed`，仅表示插件已经观察到的状态。

## 安装与运行

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m sukuna_pet.bridge_install inspect
.\.venv\Scripts\python.exe -m sukuna_pet.bridge_install install
.\.venv\Scripts\pythonw.exe tools\run_reference_pet.py
```

安装器使用现有 Node/pnpm 离线安装本项目的零依赖插件，只操作既有 `desktop` profile，先备份 package.json、已有锁文件与 workspace 配置。不会创建新 profile、安装全局工具或修改宿主安装文件。首次安装后正常打开或重开 Harness。

预览默认任务联动，不改原有桌宠模式偏好。右键保留点击跳动、持续跳动及新增任务联动；气泡优先放头顶，上方不足时移到下方并限制在工作区内。右键“退出”只关闭桌宠。

常规源码入口 `pythonw -m sukuna_pet` 同样具备监测，在右键菜单选择“任务联动”。当前已安装的旧版 Setup 程序没有更新，请使用上述源码预览入口。

## 刷新与移除

源码路径改变后再次执行 `install` 刷新自己的链接。插件改动后需要重开 Harness 才会加载新代码。移除：

```powershell
.\.venv\Scripts\python.exe -m sukuna_pet.bridge_install remove
```

移除只处理 `@sukuna-pet/dsh-bridge` 依赖与 bundle，保留其他条目和备份，重开宿主生效。多个桌宠共用插件，退出单个预览不自动卸载。当前尚无安装管理菜单或自动路径刷新线程。

## 当前范围与差距

- 观察原生 turn/start、turn/end 和 Agent 状态；按根轮次归并，子代理不重复计数。
- 参考式 ask_user_question 调用/结果配对；同一 Agent 还有已观察到的其他工具调用，或同轮子代理仍执行时，继续归为运行任务。
- 运行/等待气泡常驻，结束提示 8 秒；独立健康信号 3 秒不增长确认失联，立即隐藏旧文字，原运行状态最多再用于 5 秒跳动宽限。
- JSONL 按进程分文件、80ms 合批、超过 1MiB 轮转保留一代、每次加载新 UUID；额外每秒发布观察快照和健康信息。只输出身份和状态，不写参数、正文、命令、问题或答复。
- 普通审批只记录 ID 审计对，不直接标为真实人工等待。legacy、嵌套工具及 timed 前台等待尚未全部实测；参考式问题配对不能证明所有并发执行均被覆盖。
- 插件在已运行轮次中加载时，该轮记为未知，等下一轮原生开始事件建立观察。消费者晚开能读取插件已经观察到的快照，不回放历史结束提示。
- 多屏/混合 DPI、宿主/插件重载、真实审批及子代理并行仍需现场补验。自动维护与发行安装包尚未完成；Codex 尚未接入，不增加接入能力状态说明。

## 参考与许可

参考：[上游插件](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/integrations/dsh-pet-bridge/index.js)、[上游安装与后台读取](https://github.com/MerZlin/dsh-pet-indesktop/blob/34d810b1eadd98d00e7cb9b3b51428a45b5bf03e/pet/agent_link/__init__.py)。本项目按其机制重新实现精简桥接，健康发布、观察快照与根轮次气泡归并为补充。随包插件保留上游 MIT 许可证：Copyright (c) 2026 Merzlin。
