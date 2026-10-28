# #65：音乐跟随耳机输出

2026-10-28（Asia/Shanghai），0.4.6 本地候选；任务：https://github.com/Yuxhh/skip-pet/issues/65 。

根因：MusicPlayer 首次播放时创建绑定具体设备的 QAudioSink，此后反复复用，没有更新其输出设备，也没有监听默认输出变化。先外放再连接耳机，下一轮仍使用旧扬声器。当前 Windows 默认输出为 OPPO Enco Free4，支持当前 PCM 格式。

每轮播放重新按默认设备构造输出；播放过程中监听 QMediaDevices.audioOutputsChanged，从已处理的采样位置恢复到新默认设备，保留节拍相位与原始 15 秒截止。释放旧输出时断开信号、延迟销毁，忽略已排队的旧状态回调；设备丢失先于设备列表通知到达时同样重选输出。无可用输出时停止，只在使用者手动操作后重播。

对照固定 dsh-pet 34d810b1eadd98d00e7cb9b3b51428a45b5bf03e 的 pet/click_sound.py:178–193：其持久化 QMediaPlayer/QAudioOutput 用于短音效。本项目需 PCM 采样时钟同步节拍，继续使用 QAudioSink，并显式更新绑定设备；参考副本未修改。

- 红灯命令：`.venv/Scripts/python.exe -m pytest -q tests/test_music_devices.py --basetemp=.scratch/music-headphones/red`。原版 3 failed、1 passed；明确捕获再次播放仍绑定 speakers、播放中无法切到 headphones、全部输出丢失不停止。
- 最终设备专项 6 项通过，包含上述场景、无关设备通知、设备丢失回调顺序和启动中切换。音乐/模式/设置联合回归 35 passed、2 个回环网络超时；允许回环访问补测这两项，2 passed。合计 37 项通过，报告在 .scratch/music-headphones/targeted.xml、network-recheck.xml。
- mypy：26 个源文件通过。
- 真实硬件输出替换：.scratch/music-headphones/native_handover.py，以真实 OPPO/Realtek 设备和 QAudioSink、合成默认变化通知进行耳机→扬声器→耳机切换；采样位置 156.439→202.856→260.339 ms 连续，原时钟未重启，按期停止一次，无失败。未改变系统输出偏好。证据 native-handover.json。
- 原生完整播放入口 `SukunaPet.exe --verify-music <新目录>` 增加当前默认设备与实际建流设备 ID 的一致性断言，结果记录设备名称。

合成设备通知不替代蓝牙物理断连/重连和人工听感确认。Qt/Windows 测试中仍会打印已知首次 COM 异常诊断，测试正常完成并按返回码及断言判定。

冻结版完整播放通过，当前默认耳机与建流设备 ID 一致，首次播放 14.972 秒；实际安装版同样绑定 OPPO 耳机，首次播放 14.996 秒。两者均验证 14 秒循环、到期静止、手动重播、模式切换和关闭停音，见 frozen-result.json 与 installed-result.json。

安装器退出码 0，无需重启 Windows；235 个安装文件逐一匹配构建报告，升级前记录的 2 个偏好/聊天 JSON 摘要保持一致。已恢复日常桌宠进程。安装包位于 dist/music-headphones-0.4.6/release/Setup.exe，未公开发布。源码 ZIP 另追加安装验收证据并更新 SHA256SUMS，安装器保持本次实际验收的字节不变。
