# 宿傩桌宠 0.4.0

2026-10-27 作者已确认安装版试聊通过，#53 正式交付。最终产物位于 `dist/accepted-0.4.0/release/`，包含安装包、对应源码、构建报告、校验和及验收结论；保留当前安装的菜单和托盘更新。

请阅读[使用说明](docs/user-guide.md)和[最终验收记录](docs/verification/issue-53/acceptance.md)。提示词版本 sukuna-2026-10-27-v1，固定 deepseek-flash、关闭思考；用户自备 Key，主动测试、发送及重试可能计费。包内候选文字是构建时快照，最终作者结论见交付目录的 验收结论.md。

以下为历史说明；当前交付及验证范围以上文与最终验收记录为准。

# 宿傩桌宠 V5 · 0.2.1

Windows 透明置顶桌宠，包含已认可的 V5 头颈与眼动、点击回弹、持续节奏、动态透明命中和贴边。首次无设置启动静止；安装后无需 Python、实验预览、原视频、参考程序或联网。

0.2.1 修复快速连点时头发与衣服边缘的瞬态残影；透明显示和原生命中使用同一张完整图像的 alpha，保留既有动作与交互。复现方式及结果见[残影修复验证](docs/verification/issue-29/README.md)。

## 安装与使用

双击 `dist/release/Setup.exe`，安装后从开始菜单“宿傩桌宠”启动；安装向导可选创建桌面快捷方式。右键角色可选择点击跳动、持续跳动、188/271/320px 三档大小或退出。模式和大小立即保存，更新兼容已有合法偏好。

单击推进视线 0→1→2→3→0，头眼到位停留；进入视线 3 时眨眼。每次点击同时触发 220ms 整体回弹，连点从当前动作接续并重启一次回弹。持续模式在当前动作、眨眼和回弹完成后约等待 450ms，再推进。切回点击模式停止后续调度，当前动作自然完成。

按住可见人物拖动，释放不算点击；透明位置可操作下方应用。可将人物轮廓拖到工作区四边和四角，播放及调整大小时保持所贴边，透明留白允许越界。往内拖动即可解除对应贴边；位置和贴边不保存。

详见[使用说明](docs/user-guide.md)。安装目录的 `验收说明.md` 列出验证范围；[本轮验证记录](docs/verification/issue-28/README.md)区分自动化、本机安装、独立源码和真实硬件结果。真实多屏、负坐标屏、混合 DPI、任务栏及屏幕连接变化仍待硬件补验，不能视为全部验收完成。

交付还包含 `sukuna-pet-0.2.1-source.zip`、`build-report.json` 和 `SHA256SUMS.txt`。报告记录依赖、三张冻结素材与每个运行文件的哈希；程序模型包含在源码中。第三方许可随安装包提供。

## 从源码运行

Windows x64、Python 3.12+；本轮固定构建环境为 x64 CPython 3.14.4。其他 Python 版本打包未验证。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\pythonw.exe -m sukuna_pet
```

[固定依赖与独立构建说明](docs/build.md)包含完整测试、构建及安装验收步骤。日常验证：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mypy src tools/build_release.py
.\.venv\Scripts\python.exe -m pytest tests/test_v5_modes.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

测试沿用已确认的两处边界：`PetApplication` 的点击、模式、可控时间、鼠标手势、设置路径及只读可绘制状态；Qt 窗口的公开输入、最终图像和几何结果。冻结轨迹与原生参考帧随测试提供，日常测试无需实验目录或历史 Git 对象。可见区域由最终帧计算，仅用于几何限位；Windows 原生显示与透明命中由整帧 alpha 决定。静止时复用该帧，不以降低动作精度换取缓存。

冻结动作提交 `32c9f985d4467c1527b09c34f6868a3ccd3f85b4`，原生路线及自动节奏提交 `4ecb85c8a087ca89fb99a3a2125c826801b53e1c`。素材来源见 `src/sukuna_pet/assets/provenance.json`。历史源码验证保留在 [#23](docs/verification/issue-23/README.md)、[#24](docs/verification/issue-24/README.md)、[#25](docs/verification/issue-25/README.md)、[#26](docs/verification/issue-26/README.md)、[#27](docs/verification/issue-27/README.md)，历史 #17 安装版不代表本版验收。
