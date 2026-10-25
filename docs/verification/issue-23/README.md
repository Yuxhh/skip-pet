# #23 V5 头颈与眼动正式接入验证

日期：2026-10-25。范围为点击推进头眼四阶段、分层素材、固定运动视口与动态 alpha 命中；整体回弹、V5 自动调度、贴边补偿、硬件多屏和安装器由后续票处理。未修改或关闭父规格 #22。

## 实现与独立基准

`PetApplication` 的点击、可控时间、模式、手势及只读 `view` 仍为应用测试边界。新增头部连续相位、角度、等比缩放；眨眼中点只换眼位，头部用独立连续进度运动。Qt 窗口通过公开事件、几何、掩码和只读最终 `frame` 验证，不为网格或缓存新增测试接口。

`tools/capture_v5_traces.mjs` 通过 `git show` 直接执行动作冻结提交 `32c9f985d4467c1527b09c34f6868a3ccd3f85b4` 的 `Motion.next/tick`、`Rig.sample` 和 `eyes`。`tests/fixtures/v5-traces.json` 记录 1ms 采样、7 组输入事件和输出。覆盖四阶段与停留、普通动作改目标、闭眼/睁眼期间点击、快速五次、连续目标替换和第二次眨眼。相位、眼位、角度、缩放和眼皮误差为 1e-8；期望未复制 Python 实现公式。

旧眼动轨迹仍用于验证相同眼位与眨眼；其中只知道眼睛的 `holding` 断言由完整 V5 轨迹接替。旧自动模式睁眼后停止眼动时，独立头部可能仍需收尾，相应断言等待头眼全部到位。自动调度暂保留旧规则，后续票替换为 V5 的段间等待及回弹。

三张 PNG 均从冻结动作提交逐字节迁入包资源，哈希见 `src/sukuna_pet/assets/provenance.json`。源视口固定为 `(90,-110,1250,1220)`；正式运行不读取 `.scratch`、网页、QJSEngine、参考程序或原视频。构建配置通过包数据收集三张 PNG。

## 本轮自动化

- 应用 V5：8 个测试，包含 7 组执行冻结 JS 生成的完整轨迹。
- Qt V5：14 个测试，覆盖三档尺寸 × DPR 1/1.25/1.5/2 的四个阶段；逐个逻辑像素检查最终物理图像中所有相交 alpha 与原生区域一致，检测遗漏边缘、过期轮廓及轮廓并集。另检验动作更新、停留和 DPR 事件重建。
- 既有模式、眼位、拖动、工作区和尺寸偏好回归保留。完整套件与类型检查的最终结果见 `review.md`。
- 三档实际逻辑画布为 193×188、278×271、328×320。正式窗口进行 165 个可达头部过渡帧采样，全部位于固定画布内，结果见 `native-capture.json`。这是栅格采样，不是连续空间数学证明。本票没有回弹，330 帧头部 × 回弹极值验收留给包含回弹的后续票。
- Python wheel 使用已有固定构建环境离线构建；三张素材及 provenance 的包内哈希、独立解压后运行结果见 `wheel-check.json`。开发 `.venv` 不含 setuptools，改用已有 `.scratch/issue17-build-env`，没有安装新依赖。

## 本轮真实 Windows 证据

环境见 `native-capture.json` / `interactive-environment.json`：Windows Qt 平台、单块 G24H1、DPR 1.0、1920×1080，工作区 1920×1032。

`tools/verify_v5_native.py --capture --compare-frozen` 显示正式 `PetWindow` 和专用下层窗口，记录三档 × 四终点。`WindowFromPoint` 验证当前可见处命中桌宠、透明处命中下层窗口，每次姿态变化另外检查最多 20 个发生改变的像素。Qt 动作中拖动记录明确标为 Qt 事件，与真实 OS 输入分开。原生置顶样式也已检查。

`desktop-light-stage-*.png`、`desktop-dark-stage-*.png`、`desktop-texture-stage-*.png` 为本轮实际 Windows 桌面裁图。`188/271/320-stage-*.png` 与 `transition-to-*.png` 为当前正式最终 RGBA 帧；`qt-contact-sheet.png` 是当前正式渲染器生成的对照图，不冒充桌面截图。

与原生冻结提交 `4ecb85c8a087ca89fb99a3a2125c826801b53e1c` 的 12 张对应终点图比较：11 张完全一致，320px 视线 3 仅一个 RGBA 通道差 1，其他通道一致。详见 `frozen-native-comparison.json`。浅、深和纹理背景中，完整下巴、高前领、前后衣领顺序、肩胸固定及颈部连接未见新增偏差。

额外使用 computer-use 插件发送真实 OS 鼠标输入，`os-input-trace.jsonl` 记录：

1. 在角色画布内的透明角落点击，下层接收窗计数从 0 变 1，角色仍为视线 0。
2. 依次四次点击可见脸部，头眼经 1、2、3 回到 0 并停留，视线 2 等待独立点击。
3. 在视线 3 拖动 `(650,300) → (730,350)`，释放后仍为视线 3。
4. 下层窗口前置时角色仍显示在其上方；原生 topmost 为 true。
5. 真实右键菜单显示“点击跳动”“持续跳动”“调整大小”“退出”；通过“退出”结束窗口，`os-session-result.json` 为 `exit_code=0`、`pet_closed=true`、最终视线 0。`os-context-menu.png` 保留实际菜单。

这些结果是本轮正式源码运行证据，不使用原型历史记录替代本轮运行；像素比较仅用于确认冻结外观迁移。

## 复现

```powershell
New-Item -ItemType Directory -Force .scratch/issue23-tests | Out-Null
$env:QT_QPA_PLATFORM = 'offscreen'
.venv/Scripts/python.exe -m mypy src
.venv/Scripts/python.exe -m pytest -q --basetemp=.scratch/issue23-tests/full
Remove-Item Env:QT_QPA_PLATFORM
.venv/Scripts/python.exe tools/verify_v5_native.py --capture --compare-frozen
.venv/Scripts/python.exe tools/verify_v5_native.py
```

交互验证会打开专用背景窗口，L/D/T 切换背景；操作角色后从其右键菜单退出。记录位于本目录，三档捕获的测试偏好也只写到本目录。正常模式/大小偏好不被读取或修改。可用 `node tools/capture_v5_traces.mjs` 重建轨迹；只有重建基准和可选冻结图比较需要本地历史 Git 对象，日常运行与测试不需要。

## 保留的限制与既有工作

真实双屏、负坐标硬件屏、混合 DPI 拖动、屏幕移除未验证；合成 DPR 不计为硬件通过。没有新建或替换 V5 安装器；现有 `dist/release/Setup.exe` 仍是 #17 安装器。

启动时工作区已有 #18 三档大小、偏好迁移与对应菜单/测试；本票保留并作为正式 V5 的必要前置整合。其他未提交规划、词表、实验目录和 #18 历史证据保持原状。本票改动前相关文件的快照保存在本地 `.scratch/issue23-baseline/`，未纳入提交。
