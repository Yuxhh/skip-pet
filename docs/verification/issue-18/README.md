# #18 调整大小验证

按用户修正，320px 为最大档。右键“调整大小”现提供 188px、271px、320px 三项，数值为 Qt 逻辑像素高度，宽度等比缩放为 193、278、328px。三档沿用此前的相对比例，将最大档由 544 缩至 320。默认 320px，选择即时生效并与播放模式共同保存在原有 mode.json；兼容旧版只包含模式的设置。旧 461 偏好恢复为 271，旧 544 恢复为 320，原有 320 保持为 320。

验证结果：

- `python -m pytest -q --basetemp=.scratch/resize/pytest-corrected`：66 项通过，含旧偏好迁移及最大高度限制。
- `python -m mypy src`：6 个源文件通过。
- `python tools/verify_resize_native.py`：Windows Qt 平台三个独立进程通过。依次从 320 切换 188、重启恢复 188 后切换 271、重启恢复 271 后切换 320。每次实际打开原生子菜单，通过 Qt 输入选择，复开检查唯一勾选、实际窗口宽高、最大高度 320 与可见轮廓工作区约束。当前结果与截图均在 `corrected-sizes/`，本目录根部的旧版结果与截图保留为历史记录。
- 自动测试覆盖缩放后的命中轮廓、菜单选项与勾选、放大后避开工作区边界、缩小后仍能点击推进、阶段与模式保持、旧设置兼容、异常大小回退、模式与大小互不覆盖、保存失败保持原大小。

原生验证使用工作区内 `test-preferences.json`，不更改正常启动的用户偏好。使用 Qt 输入事件而非操作系统鼠标注入；不把本次结果作为三种大小下的真实多屏、混合 DPI 或外部应用鼠标穿透验收。原生 QRegion 按每次缩放后的绘制尺寸重新建立，延续已有透明穿透实现。

新版安装包通过 `python tools/build_release.py --iscc .scratch/build-tools/InnoSetup/ISCC.exe` 构建，交付位于 `dist/release/Setup.exe`，目录式程序位于 `dist/app/SukunaPet/SukunaPet.exe`。
