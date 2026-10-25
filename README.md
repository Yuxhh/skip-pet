# 宿傩桌宠

原生 Windows 透明半身角色，首次启动静止，点击一次使头颈与眼睛推进一个视线阶段并停留。
当前源码已接入 [#23](https://github.com/xyd-0811/skip-pet/issues/23) 的冻结 V5 分层头颈动作、固定 3× 眼动及动态透明命中、[#24](https://github.com/xyd-0811/skip-pet/issues/24) 的整体点击回弹与连点接续、[#25](https://github.com/xyd-0811/skip-pet/issues/25) 的持续跳动与模式切换，以及 [#26](https://github.com/xyd-0811/skip-pet/issues/26) 的动态贴边和贴边缩放。三张素材随包提供。正式窗口证据见 [#23 验证记录](docs/verification/issue-23/README.md)、[#24 验证记录](docs/verification/issue-24/README.md)、[#25 验证记录](docs/verification/issue-25/README.md)和 [#26 验证记录](docs/verification/issue-26/README.md)。

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

每次点击同时触发整个人物的 220ms 回弹，110ms 时宽 110%、高 85%，随后恢复，头眼继续停在目标阶段。连点从当前头部动作接续，每次仅重启一次回弹，幅度不叠加、不排队。拖动、拖回起点后释放、捕获中断和隐藏窗口均不触发点击动作。

右键菜单提供“点击跳动”“持续跳动”“调整大小”和“退出”，勾选当前模式与大小。“调整大小”可选 188px、271px、320px（最大）画布高度（Qt 逻辑像素），对应 193×188、278×271、328×320 的固定完整运动视口，默认 320px。切换后即时更新显示与鼠标命中轮廓，并保持角色在屏幕工作区内。持续模式在当前阶段、眨眼与回弹全部完成后约等待 450ms，再推进下一阶段并回弹，仍接受点击互动。手动点击替换目标并重启回弹及等待；切回点击模式立即停止后续调度，当前阶段、眨眼和回弹自然完成并停留，等待中切换不额外推进。

选择模式或大小后立即保存，下次启动恢复；首次无设置或设置损坏时使用点击模式与 320px。设置存放于 Qt 的用户配置目录（Windows 通常为 `%LOCALAPPDATA%\skip-pet\sukuna-pet\mode.json`），兼容旧版只含模式的偏好。保存失败时提示重试，继续使用原选项。选择“退出”结束进程。

素材已随 Python 包提供，运行不需要 `.scratch`、参考程序、原型网页、原视频或联网。
拖动时按鼠标所在屏幕的可用区域限制角色非透明轮廓，避开任务栏；支持负坐标与各屏幕独立的 Qt 逻辑坐标，不用整个虚拟桌面的外包矩形代替工作区。DPI、屏幕布局或工作区变化后重新检查位置，不保存位置。
人物可贴齐工作区四边和四角，透明画布允许越界。偏头和回弹时按当前最终 alpha 轮廓补偿窗口位置，始终接触所贴边；三档缩放后保留贴边。拖离某条边即解除该方向的贴边，居中播放保持窗口位置稳定。贴边状态不保存，重启恢复默认位置。单屏 Windows 操作与透明穿透证据见 [#26 验证记录](docs/verification/issue-26/README.md)；真实跨屏和混合 DPI 仍由后续票验收。
安装器由 #17 交付。#16 已完成本机单屏 100% 缩放的真实 Windows 验证；真实多屏和混合 DPI 尚未验证，详见 [#16 验证记录](docs/verification/issue-16/README.md)。

## 维护与验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest tests/test_playback.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_modes.py tests/test_v5_modes.py tests/test_modes_desktop.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_pointer.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_desktop.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_v5.py tests/test_v5_desktop.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_bounce.py tests/test_bounce_desktop.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_edges.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/visual_check.py --show
.\.venv\Scripts\python.exe tools/verify_v5_modes_native.py
.\.venv\Scripts\python.exe tools/verify_pointer_native.py
.\.venv\Scripts\python.exe tools/verify_pointer_native.py --output docs/verification/issue-16
.\.venv\Scripts\python.exe tools/verify_v5_native.py --capture
.\.venv\Scripts\python.exe tools/verify_bounce_native.py --capture
.\.venv\Scripts\python.exe tools/verify_edges_native.py --capture
```

`PetApplication.click()`、`select_mode("click" | "always")`、`advance(elapsed_ms)` 与只读 `view`/`mode` 是父规格已确认的应用级测试边界；通过同一设置路径建立新实例验证模式恢复。
`view` 提供源图坐标下两眼中心、眼皮闭合程度、头部连续相位/角度/等比缩放及阶段/停留状态；Qt 将真实帧时间至多计入 150ms，每帧只调用一次应用入口，应用内部以不超过 4ms 的子步推进动作。应用的虚拟时间入口不截断，每次调用代表一帧，自动等待与调度在该帧结束时处理。绘制不决定播放时序。V5 轨迹直接执行冻结提交 `32c9f985d4467c1527b09c34f6868a3ccd3f85b4` 的 `Motion`、`Rig` 与眼睛绘制生成，可用 `node tools/capture_v5_traces.mjs` 重建；测试不需要 Node.js 或历史 Git 对象。

`view.bounce_scale` 表达独立的整体回弹比例；`holding` 仍只表示头眼阶段已到位，回弹可能还在恢复。冻结轨迹现含 `Bounce.sample` 输出。`tools/capture_bounce_references.py` 从不可变原生提交生成 32 张组合动作 PNG，Qt 公开输入测试与它们逐像素对照；日常测试不执行实验代码。原生工具另对三档各作 165 头部相位 × 两个回弹极值的范围采样，并记录真实可达的点击轨迹，采样不构成连续空间证明。

同一入口的 `pointer_press(position, window_position, drag_distance=...)`、`pointer_move(position)`、`pointer_release(position)` 和 `cancel_pointer()` 接收左键手势。坐标与拖动距离采用 Qt 逻辑像素，距离由 `QApplication.startDragDistance()` 提供；移动/释放返回需要移动到的窗口位置，只有未达到拖动阈值的释放才调用统一 `click()`。已进入拖动的手势即使回到起点也不变成点击，丢失鼠标捕获时取消手势。

窗口在当前屏幕 DPR 生成一张最终帧，绘制与原生 `QRegion` 掩码消费同一帧。非零 alpha 的物理像素向外覆盖逻辑区域，保留半透明边缘；画面、大小或 DPR 改变时同步更新，停留时复用已生成图像。窗口的只读 `frame` 提供该最终帧的副本。当前生产窗口的原生穿透、拖动、置顶及浅/深/纹理背景证据见 [#23 验证记录](docs/verification/issue-23/README.md)；历史首版证据保留在 [#15](docs/verification/issue-15/README.md)。

#16 经用户确认，新增 Qt 窗口公开输入与几何结果的测试边界。`test_desktop.py` 通过窗口鼠标事件、位置和掩码观察约束；多屏布局夹具替换系统屏幕查询及屏幕选择，不模拟真实 Windows DPI 切换，不能替代物理设备验收。原生观察工具可指定输出目录，记录屏幕布局、可用区域、DPI、鼠标与可见范围；运行会新建/覆盖该目录中的本次记录，不读写模式偏好。

行为基准来自原型提交 `9eef9e2418d536fe6a5b71235841ae98da64329c`。
测试夹具直接执行该提交中的原始 `StageRules`、`next`、`tick`、`paintSprite` 生成，覆盖普通周期、动作中改目标、闭眼/睁眼中点击、跨周期快速点击及再次眨眼。夹具以 1ms 虚拟绘制步长采样，眼中心比较容许 0.2 个源像素的采样差异；断言不重写轨迹公式。
如本地保留了该历史 Git 对象，可用 Node.js 重新生成夹具：`node tools/capture_prototype_traces.mjs`。日常运行及测试不需要 Node.js 或该 Git 对象。

持续模式的 15 组轨迹由 `tools/capture_v5_mode_traces.py` 直接执行冻结原生提交 `4ecb85c8a087ca89fb99a3a2125c826801b53e1c` 的调度方法与 JS 模型生成。覆盖 16/33ms 帧、240ms 延迟帧（原生限为 150ms）、途中点击、五连点、各种时机切回点击与恢复持续。等待累计包含首次观察到动作完成的整帧，约 450ms 保留帧粒度误差；不能用不同的帧输入序列要求相同等待结果。比较同一输入时，头眼、眨眼和回弹容差为 1e-8。旧无间隔持续测试已替换；点击眼位、指针与设置回归继续保留。`holding` 在两个模式均表示头眼已停留，不代表独立回弹已经结束。三次独立 Windows 进程与菜单、真实鼠标补充记录见 [#25 验证记录](docs/verification/issue-25/README.md)。

素材来源及 SHA-256 见 `src/sukuna_pet/assets/provenance.json`；原生观察与背景检查见 [#13 验证记录](docs/verification/issue-13/README.md)，模式与重启验证见 [#14 验证记录](docs/verification/issue-14/README.md)。
