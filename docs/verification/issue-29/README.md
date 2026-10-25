# 快速连点残影修复 · 0.2.1

日期：2026-10-25，Asia/Shanghai。任务：[修复快速连点时头发与衣服边缘的瞬态残影](https://github.com/xyd-0811/skip-pet/issues/29)。用户确认残影只在连点运动时出现、停下后消失，并授权直接修复与验证。本问题收敛为一轮修复，没有另建大型 wayfinder 地图。

## 原因与修复

原窗口每次生成新帧，先 `setMask` 更新 Windows 原生裁剪，再由异步 `update()` 上传新图像。这两个变化不是一次完整图像更新，运动期间会出现不属于任何完整绘制帧的混合轮廓。仅停稳后截图不会捕捉到这个问题。

0.2.1 移除逐帧原生裁剪。Qt 上传完整透明帧，Windows 根据该帧 alpha 同时决定外观及透明处命中；`visible_region` 保留同帧 alpha 的逻辑覆盖，仅用于拖动限位、贴边与缩放。没有修改素材、头颈模型、眼动、220ms 回弹、450ms 等待或模式语义。

依据：[Microsoft 分层窗口的透明命中](https://learn.microsoft.com/en-us/windows/win32/winmsg/window-features#layered-windows)说明 alpha 为零的区域允许鼠标穿透；[Qt setMask 文档](https://doc.qt.io/qt-6/qwidget.html#setMask)说明原生 mask 会进行粗粒度视觉裁剪，平滑边缘应使用透明背景绘制。原生像素及命中实测另见下文。

## 能捕捉本问题的回归

新增 `tools/verify_ghosting_native.py`。一个进程运行正式 `PetWindow`，通过公开 Qt 单击和真实时间播放；独立进程采集 Windows 桌面，避免采集阻塞动画事件循环。逐张检查桌面画面能否匹配某一张完整绘制帧在验证背景上的合成结果，允许显示上一张完整帧，但不允许混合轮廓。包含半透明边缘，不仅比较不透明像素。

修复前实际运行：390 次捕获、121 张不同桌面画面、37 张完整绘制帧，其中 **84 张异常画面**，命令返回失败。见 [red.json](red.json)。单次点击的最小复现也能捕捉异常，连续点击将其反复触发。第一轮固定时间停稳采样 36 帧则全部匹配，说明它不足以作为此问题的反馈环。

相同命令在修复后：389 次捕获、58 张不同画面，**0 张异常画面**；可见处原生命中桌宠、透明处命中下层验证窗口。见 [green.json](green.json)。

```powershell
.\.venv\Scripts\python.exe tools/verify_ghosting_native.py --output .scratch/ghosting-repeat --height 320 --background dark
```

必须使用新的输出目录。需要真实 Windows 主屏 DPR 1；窗口不能被其他置顶应用遮挡。每次默认采集 4 秒，60ms 间隔尝试单击，实际输入次数受事件循环与绘制耗时影响，结果中如实记录。测试输入是公开 Qt 事件，不冒充真实鼠标；截图来自 Windows 桌面。

## 验证结果

- 188/271/320px × 浅色/深色/纹理背景，共 9 组连续采样：**3,582 次捕获、577 张不同桌面画面、367 次点击，异常为 0**。各组均通过可见处及透明处的 `WindowFromPoint` 检查，见 [matrix.json](matrix.json)。
- 原生阶段推进、三档大小、运动后改变轮廓处的透明命中及动画中 Qt 拖动通过，见 [native-alpha-routing.json](native-alpha-routing.json)。
- 三档 × 八种边/角 × 四阶段 × 峰值/停留，共 **192 张**真实桌面像素与最终帧合成及贴边几何一致，见 [native-edges.json](native-edges.json)。首次采集遇到其他置顶提示覆盖，未计通过；诊断工具在每次像素检查前抬高自己的背景与窗口后重采，全部通过。失败原图仍保留在本地 `.scratch/ghosting/native-edges/`。
- 完整自动化：**191 passed in 109.67s**。修改后的测试沿用 Qt 公开图像、几何及输入边界；逻辑可见区域检查继续逐像素匹配最终帧 alpha。原先用 `setMask` 伪造透明留白的两例改为使用实际角色，检查四边接触及透明留白可以越界。
- `mypy src tools/build_release.py tools/measure_runtime.py tools/verify_ghosting_native.py`：**9 个文件通过**。完整套件使用 offscreen；真实桌面证据单独列出。辅助测试命名更新后，191 项均可成功收集。

## 交付与限制

修复版本 0.2.1，保持冻结素材哈希和依赖版本。安装器、源码归档与哈希清单由锁定构建环境生成；最终文件见 `dist/release/`。构建和安装结果另见 [delivery.json](delivery.json)。

已在当前用户的既有安装目录升级，安装器返回 0，注册版本为 0.2.1；161 个已安装文件逐个哈希匹配构建报告。原配置 `click/320` 保持不变，旧版安装器及清单在本地 `.scratch/ghosting/previous-release/` 备份。当前正在运行的是升级后的安装程序。

使用 computer-use 对实际安装窗口完成五连点、右键菜单、选择持续模式、持续时三连点、恢复点击模式及短距离往返拖动。两种模式的菜单勾选与运动表现正确，拖动后姿态保持并放回原位。最后重新核对偏好为原 `click/320`。这些实际 OS 操作补充了源码像素回归，静态截图没有被当成连续帧无残影的证明。

安装器 SHA-256 为 `35b37f84dfd86df7f020b3fe2de6238f1d6d30eef14e30a1f4b83370953d9ba9`。完成安装证据后仅刷新源码归档及其清单，保持已验证安装器和构建报告字节不变。

本机环境为 Windows 11、G24H1 单屏 1920×1080，工作区 1920×1032，DPR 1。有限连续采样不是所有机器/显示器的保证；没有据此新增真实多屏、混合 DPI 或干净 Windows 验收声明。当前修复针对软件产生的混合轮廓，最终观感仍可由用户在实际显示器上复核。

原始截图、实验脚本与完整本地运行产物位于 `.scratch/ghosting/`，不随源码归档收集用户桌面内容。本文及各摘要 JSON 随源码交付，复现工具不依赖 `.scratch`。
