# 宿傩桌宠

原生 Windows 透明半身角色，首次启动静止，点击一次推进一个视线阶段并停留。
当前实现对应 [#13](https://github.com/xyd-0811/skip-pet/issues/13)–[#16](https://github.com/xyd-0811/skip-pet/issues/16)，使用已认可原型的重绘素材与固定 3× 眼动，身体不摆动。

## 从源码运行

在 Windows x64、Python 3.12 或更新版本中执行；本次实际验证环境是 Python 3.14.4。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\pythonw.exe -m sukuna_pet
```

单击角色依次进入视线 1、2、3、0，每次结束保持。视线 2 不自行眨眼；下一次单独点击进入视线 3 时眨眼，240ms 完成，闭合 120ms 时直接换位。连点覆盖前方目标，从当前位置衔接。按住可见角色拖动调整位置，拖动及释放不推进阶段；透明区域鼠标穿透到下方 Windows 应用，其他普通应用前置时角色仍置顶。

右键菜单提供“点击跳动”“持续跳动”和“退出”，勾选当前模式。持续模式连续眼动，仍接受点击互动；切回点击模式完成当前视线阶段后保持，并保留正在进行的眨眼。沿用原型的持续播放规则，睁眼期间已开始下一段眼动时会完成该段，同时让本次眨眼完整结束。

选择模式后立即保存，下次启动恢复；首次无设置或设置损坏时使用点击模式。设置仅包含模式，存放于 Qt 的用户配置目录（Windows 通常为 `%LOCALAPPDATA%\skip-pet\sukuna-pet\mode.json`）。保存失败时提示重试，继续使用原模式。选择“退出”结束进程。

素材已随 Python 包提供，运行不需要 `.scratch`、参考程序、原型网页、原视频或联网。
拖动时按鼠标所在屏幕的可用区域限制角色非透明轮廓，避开任务栏；支持负坐标与各屏幕独立的 Qt 逻辑坐标，不用整个虚拟桌面的外包矩形代替工作区。DPI、屏幕布局或工作区变化后重新检查位置，不保存位置、不增加缩放设置。
这一步交付源码运行入口；Setup.exe 在 #17 中交付。#16 已完成本机单屏 100% 缩放的真实 Windows 验证；真实多屏和混合 DPI 尚未验证，详见 [#16 验证记录](docs/verification/issue-16/README.md)。

## 维护与验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest tests/test_playback.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_modes.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_pointer.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_desktop.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/visual_check.py --show
.\.venv\Scripts\python.exe tools/verify_modes_native.py
.\.venv\Scripts\python.exe tools/verify_pointer_native.py
.\.venv\Scripts\python.exe tools/verify_pointer_native.py --output docs/verification/issue-16
```

`PetApplication.click()`、`select_mode("click" | "always")`、`advance(elapsed_ms)` 与只读 `view`/`mode` 是父规格已确认的应用级测试边界；通过同一设置路径建立新实例验证模式恢复。
`view` 提供源图坐标下两眼中心、眼皮闭合程度及阶段/停留状态；Qt 仅将真实时间和输入接入此边界。绘制不决定播放时序。

同一入口的 `pointer_press(position, window_position, drag_distance=...)`、`pointer_move(position)`、`pointer_release(position)` 和 `cancel_pointer()` 接收左键手势。坐标与拖动距离采用 Qt 逻辑像素，距离由 `QApplication.startDragDistance()` 提供；移动/释放返回需要移动到的窗口位置，只有未达到拖动阈值的释放才调用统一 `click()`。已进入拖动的手势即使回到起点也不变成点击，丢失鼠标捕获时取消手势。

窗口以绘制裁剪和缩放后的非零 alpha 轮廓建立原生 `QRegion` 掩码；保留半透明边缘，透明空白不在窗口命中区域内。轮廓不随眼动变化，因此无需逐帧重建。原生穿透、拖动与置顶证据见 [#15 验证记录](docs/verification/issue-15/README.md)。

#16 经用户确认，新增 Qt 窗口公开输入与几何结果的测试边界。`test_desktop.py` 通过窗口鼠标事件、位置和掩码观察约束；多屏布局夹具替换系统屏幕查询及屏幕选择，不模拟真实 Windows DPI 切换，不能替代物理设备验收。原生观察工具可指定输出目录，记录屏幕布局、可用区域、DPI、鼠标与可见范围；运行会新建/覆盖该目录中的本次记录，不读写模式偏好。

行为基准来自原型提交 `9eef9e2418d536fe6a5b71235841ae98da64329c`。
测试夹具直接执行该提交中的原始 `StageRules`、`next`、`tick`、`paintSprite` 生成，覆盖普通周期、动作中改目标、闭眼/睁眼中点击、跨周期快速点击及再次眨眼。夹具以 1ms 虚拟绘制步长采样，眼中心比较容许 0.2 个源像素的采样差异；断言不重写轨迹公式。
如本地保留了该历史 Git 对象，可用 Node.js 重新生成夹具：`node tools/capture_prototype_traces.mjs`。日常运行及测试不需要 Node.js 或该 Git 对象。

持续模式的 6 组轨迹同样直接执行固定原型生成，覆盖跨周期、自动播放中点击、闭合/睁眼中点击和连点；为累计的 1ms 事件采样差异容许 0.5 个源像素和 0.03 的眼皮闭合误差。模式切换及保存恢复通过同一应用入口验证。`verify_modes_native.py` 在真实 Windows/Qt 平台显示并点击原生菜单，用三个独立进程复核保存、重启和退出，使用 Qt 测试配置目录并保留其中的原设置。

素材来源及 SHA-256 见 `src/sukuna_pet/assets/provenance.json`；原生观察与背景检查见 [#13 验证记录](docs/verification/issue-13/README.md)，模式与重启验证见 [#14 验证记录](docs/verification/issue-14/README.md)。
