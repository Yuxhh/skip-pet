# #25 持续跳动与模式切换验证

日期：2026-10-25。正式源码窗口，基线提交 `ea49574fc180028275023dbd3e6ad3dd29793562`。本票接入持续调度；动态贴边、更新安装器及真实多屏验收属于后续票。未修改或关闭父规格 #22。

## 实现与时间边界

持续与手动推进统一调用 `PetApplication.click()`，同时替换下一阶段目标、重启 220ms 回弹并清零等待。自动模式的头眼模型仍采用 V5 的逐阶段规则，不调用旧版无间隔连续眼动。只有阶段、头部、眨眼和回弹均结束，才累计约 450ms 等待。切回点击模式只关闭调度，当前动作自然完成；等待中切换不会启动额外阶段。

`advance(elapsed_ms)` 每次调用代表一个虚拟帧，不截断时间；内部模型子步不超过 4ms。Qt 每帧只提交一次 `min(150, real_elapsed_ms)`，避免把等待也拆成多个子帧。等待按冻结原生预览累计整帧：首次在帧末观察到空闲时，整帧时间计入等待；达到 450ms 后在帧末启动下一阶段，不回放积压动作。不同帧输入可有不同的段间误差，比较基准必须使用同一帧序列。`holding` 在两种模式均表示头眼已到位，独立回弹可以尚在恢复。

选择持续模式时，空闲则立即推进，已有动作则先完成。启动恢复已存持续模式时也进入同一动作入口。重复选择当前模式保持原有动作及等待。仅模式和大小写入设置；仍兼容只含模式及旧大小偏好，保存失败先提示并保持旧选项。

## 独立基准与回归

`tools/capture_v5_mode_traces.py` 从冻结原生提交 `4ecb85c8a087ca89fb99a3a2125c826801b53e1c` 提取并执行 `Model` 与 `Pet.advance_elapsed/click_stage/select_mode` 的原始方法，同时执行冻结的眼睛绘制、Rig、Bounce。绘制替换为空操作；输入事件已经推进到对应帧，`select_mode` 的墙钟刷新为空操作。未导入正式播放实现，也未用 Python 公式制造期望。

`tests/fixtures/v5-mode-traces.json` 保存 15 组逐帧状态：16ms 和 33ms 的多周期、240ms 延迟帧（原生截断至 150ms）、普通动作/等待/闭合/睁眼中点击、五连点；普通动作、头已停而回弹未完、等待、闭合、睁眼时切回点击；动作中及等待中恢复持续。阶段、头部连续相位、头部矩阵、双眼中心、眼皮、回弹与停留均对照，浮点容差 1e-8。日常测试只读取夹具，不依赖 Node、QJSEngine、实验目录或历史 Git 对象。

沿用父规格已确认的应用入口与 Qt 公开输入/图像/区域边界。先由持续基准暴露旧调度不立即推进的问题，再实现统一动作；Qt 时间测试随后暴露子步拆分等待的问题，修正后通过。15 个旧无间隔持续测试被新规则取代，适用的点击眼位、眨眼、连点、指针、图像、大小与设置回归保留。额外检查大虚拟帧只调度一次、同模式不重启，以及菜单模式/三档大小互不覆盖、失败提示与新实例恢复。

完整回归先在共享工作区通过 137 项；为排除同期动态贴边改动，又导出本票暂存快照到 `.scratch/issue25-verification-checkout`，最终复验 **137 passed in 42.18s**；严格类型检查：**6 个源文件无错误**。自动化使用 offscreen Qt，不能替代下面的真实 Windows 证据。结果见 [pytest.txt](pytest.txt)、[mypy.txt](mypy.txt)；两轴审查见 [review.md](review.md)。

## 正式 Windows 证据

`tools/verify_v5_modes_native.py` 在 Windows Qt 平台实际显示生产 `PetWindow`、原生菜单及大小子菜单，用 Qt 公开鼠标事件选择。它不读取用户日常偏好，三个独立进程共用本证据目录的隔离设置路径。

| 进程 | 启动偏好 | 本轮操作与退出时偏好 |
| --- | --- | --- |
| select-always | 点击 / 320 | 菜单改 188、启用持续，途中点击，退出保存持续 / 188 |
| restore-always | 持续 / 188 | 菜单改 271、途中点击、切回点击并验证自然停留，退出保存点击 / 271 |
| restore-click | 点击 / 271 | 菜单改 320、点击，退出保存点击 / 320 |

三个原生进程也在上述本票快照中复验。三个 `*-trace.json` 的退出码均为 0、failures 均为空，记录当前勾选、真实帧采样、点击前后阶段及最终设置。`*-menu.png` 与 `*-sizes.png` 为实际 popup 截图；`*-startup/manual-click/final.png` 为正式最终帧。逐帧采样可观察阶段完成、短暂停留及下一阶段回弹；停留保留完成帧整帧计入等待及观察采样偏差。记录的手动点击会打断停留，初次启动前静止也不计作自动段间等待。精确时序比较以上面的同输入冻结轨迹为准。

本机 Python 3.14.4、PySide6 6.12.0，单块 G24H1 / 1920×1080 / DPR 1.0。

另在共享工作区用 computer-use 的真实 OS 鼠标补录两场会话（不作为动态贴边验收），压缩原始记录为 `os-input-trace.jsonl.gz` 和 `os-stop-session/os-input-trace.jsonl.gz`。真实右键打开菜单并启用持续模式，运行中单击可重启回弹并继续播放；第二场再次打开菜单可见持续模式勾选。`os-menu-*.png` 保存菜单，`os-session-result.json` 保存隔离偏好与进程退出结果。两场均由 **180000ms 安全计时器**结束，未完成真实鼠标切回点击与菜单退出；没有把超时关闭写成鼠标退出验收。切回、自然停留、菜单退出与独立进程恢复已由上表的真实 Windows / Qt 公开事件验证，和 OS 注入记录分别表述。

## 重现与限制

```powershell
.\.venv\Scripts\python.exe tools/capture_v5_mode_traces.py
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest tests/test_v5_modes.py tests/test_modes_desktop.py -q --basetemp=.scratch/issue25-repeat
.\.venv\Scripts\python.exe -m mypy src
Remove-Item Env:QT_QPA_PLATFORM
.\.venv\Scripts\python.exe tools/verify_v5_modes_native.py
.\.venv\Scripts\python.exe tools/verify_v5_modes_native.py --interactive --output .scratch/issue25-os-repeat
```

原生工具会覆盖指定目录的本次隔离偏好与证据，应使用单独输出目录。没有修改动作参数、素材、渲染、贴边或安装器；没有复验真实多屏、混合 DPI，也没有把已有合成 DPR 回归写成硬件验收。
