# 宿傩桌宠

原生 Windows 透明半身角色，首次启动静止，点击一次使头颈与眼睛推进一个视线阶段并停留。
当前源码已接入 [#23](https://github.com/xyd-0811/skip-pet/issues/23) 的冻结 V5 分层头颈动作、固定 3× 眼动及动态透明命中。三张素材随包提供；整体点击回弹、V5 自动节奏和动态贴边由后续票接入。正式窗口证据见 [#23 验证记录](docs/verification/issue-23/README.md)。

## 安装版

当前 `dist/release/Setup.exe` 是 #17 的首版眼动安装器；V5 安装器由后续交付票更新。本票验证的是下方源码入口运行的正式窗口。

双击 `dist/release/Setup.exe`，安装后从开始菜单“宿傩桌宠”启动，也可在向导中选择桌面快捷方式。无需安装 Python、保留原视频或配置宿主。通过 Windows“已安装的应用”或开始菜单卸载入口移除；模式偏好保留。详见[使用说明](docs/user-guide.md)、[固定依赖与构建说明](docs/build.md)、[#17 验证记录](docs/verification/issue-17/README.md)。源码 ZIP 与 SHA-256 清单随安装器交付。

## 从源码运行

在 Windows x64、Python 3.12 或更新版本中执行；本次实际验证环境是 Python 3.14.4。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\pythonw.exe -m sukuna_pet
```

单击角色依次进入视线 1、2、3、0，头颈与眼睛连续运动，每次结束保持。肩胸固定，头部等比偏转，上颈随动并平滑连回领口。视线 2 不自行眨眼；下一次单独点击进入视线 3 时眨眼，240ms 完成，闭合 120ms 时只换眼位，头部仍连续运动。连点覆盖前方目标，从当前位置衔接。按住可见角色拖动调整位置，拖动及释放不推进阶段；透明区域鼠标穿透到下方 Windows 应用，其他普通应用前置时角色仍置顶。

右键菜单提供“点击跳动”“持续跳动”“调整大小”和“退出”，勾选当前模式与大小。“调整大小”可选 188px、271px、320px（最大）画布高度（Qt 逻辑像素），对应 193×188、278×271、328×320 的固定完整运动视口，默认 320px。切换后即时更新显示与鼠标命中轮廓，并保持角色在屏幕工作区内。持续模式暂保留旧版连续眼动调度并附带头部运动，仍接受点击互动；切回点击模式完成当前视线阶段后保持，并保留正在进行的眨眼。V5 的段间 450ms 等待与自动回弹由后续票替换。

选择模式或大小后立即保存，下次启动恢复；首次无设置或设置损坏时使用点击模式与 320px。设置存放于 Qt 的用户配置目录（Windows 通常为 `%LOCALAPPDATA%\skip-pet\sukuna-pet\mode.json`），兼容旧版只含模式的偏好。保存失败时提示重试，继续使用原选项。选择“退出”结束进程。

素材已随 Python 包提供，运行不需要 `.scratch`、参考程序、原型网页、原视频或联网。
拖动时按鼠标所在屏幕的可用区域限制角色非透明轮廓，避开任务栏；支持负坐标与各屏幕独立的 Qt 逻辑坐标，不用整个虚拟桌面的外包矩形代替工作区。DPI、屏幕布局或工作区变化后重新检查位置，不保存位置。
安装器由 #17 交付。#16 已完成本机单屏 100% 缩放的真实 Windows 验证；真实多屏和混合 DPI 尚未验证，详见 [#16 验证记录](docs/verification/issue-16/README.md)。

## 维护与验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest tests/test_playback.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_modes.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_pointer.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_desktop.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_v5.py tests/test_v5_desktop.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/visual_check.py --show
.\.venv\Scripts\python.exe tools/verify_modes_native.py
.\.venv\Scripts\python.exe tools/verify_pointer_native.py
.\.venv\Scripts\python.exe tools/verify_pointer_native.py --output docs/verification/issue-16
.\.venv\Scripts\python.exe tools/verify_v5_native.py --capture
```

`PetApplication.click()`、`select_mode("click" | "always")`、`advance(elapsed_ms)` 与只读 `view`/`mode` 是父规格已确认的应用级测试边界；通过同一设置路径建立新实例验证模式恢复。
`view` 提供源图坐标下两眼中心、眼皮闭合程度、头部连续相位/角度/等比缩放及阶段/停留状态；Qt 将真实帧时间至多计入 150ms，并以不超过 4ms 的子步接入此边界。应用的虚拟时间入口不截断。绘制不决定播放时序。V5 轨迹直接执行冻结提交 `32c9f985d4467c1527b09c34f6868a3ccd3f85b4` 的 `Motion`、`Rig` 与眼睛绘制生成，可用 `node tools/capture_v5_traces.mjs` 重建；测试不需要 Node.js 或历史 Git 对象。

同一入口的 `pointer_press(position, window_position, drag_distance=...)`、`pointer_move(position)`、`pointer_release(position)` 和 `cancel_pointer()` 接收左键手势。坐标与拖动距离采用 Qt 逻辑像素，距离由 `QApplication.startDragDistance()` 提供；移动/释放返回需要移动到的窗口位置，只有未达到拖动阈值的释放才调用统一 `click()`。已进入拖动的手势即使回到起点也不变成点击，丢失鼠标捕获时取消手势。

窗口在当前屏幕 DPR 生成一张最终帧，绘制与原生 `QRegion` 掩码消费同一帧。非零 alpha 的物理像素向外覆盖逻辑区域，保留半透明边缘；画面、大小或 DPR 改变时同步更新，停留时复用已生成图像。窗口的只读 `frame` 提供该最终帧的副本。当前生产窗口的原生穿透、拖动、置顶及浅/深/纹理背景证据见 [#23 验证记录](docs/verification/issue-23/README.md)；历史首版证据保留在 [#15](docs/verification/issue-15/README.md)。

#16 经用户确认，新增 Qt 窗口公开输入与几何结果的测试边界。`test_desktop.py` 通过窗口鼠标事件、位置和掩码观察约束；多屏布局夹具替换系统屏幕查询及屏幕选择，不模拟真实 Windows DPI 切换，不能替代物理设备验收。原生观察工具可指定输出目录，记录屏幕布局、可用区域、DPI、鼠标与可见范围；运行会新建/覆盖该目录中的本次记录，不读写模式偏好。

行为基准来自原型提交 `9eef9e2418d536fe6a5b71235841ae98da64329c`。
测试夹具直接执行该提交中的原始 `StageRules`、`next`、`tick`、`paintSprite` 生成，覆盖普通周期、动作中改目标、闭眼/睁眼中点击、跨周期快速点击及再次眨眼。夹具以 1ms 虚拟绘制步长采样，眼中心比较容许 0.2 个源像素的采样差异；断言不重写轨迹公式。
如本地保留了该历史 Git 对象，可用 Node.js 重新生成夹具：`node tools/capture_prototype_traces.mjs`。日常运行及测试不需要 Node.js 或该 Git 对象。

持续模式的 6 组轨迹同样直接执行固定原型生成，覆盖跨周期、自动播放中点击、闭合/睁眼中点击和连点；为累计的 1ms 事件采样差异容许 0.5 个源像素和 0.03 的眼皮闭合误差。模式切换及保存恢复通过同一应用入口验证。`verify_modes_native.py` 在真实 Windows/Qt 平台显示并点击原生菜单，用三个独立进程复核保存、重启和退出，使用 Qt 测试配置目录并保留其中的原设置。

素材来源及 SHA-256 见 `src/sukuna_pet/assets/provenance.json`；原生观察与背景检查见 [#13 验证记录](docs/verification/issue-13/README.md)，模式与重启验证见 [#14 验证记录](docs/verification/issue-14/README.md)。
