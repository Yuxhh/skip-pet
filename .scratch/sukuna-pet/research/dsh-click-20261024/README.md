# dsh-pet 点击 Q 弹的静态证据

2026-10-24。本调查没有运行任何提取代码，没有改动 `D:\dsh-pet`。仅从用户指明的发行物读取归档与 Python 3.11 字节码，输出在当前工作区。

## 目标与方法

目标：`D:\dsh-pet\app\dsh-pet-standalone-webm-chat.exe`。

SHA-256：`687255faea034bd0e672a870da732650dbbd5b9aae050586e143ac1e55c50407`。

父代理已用 REA `open_binary` 识别为 x86_64 PE；REA 分类本身不证明点击动画运行行为。本子调查用自编只读 PyInstaller CArchive/PYZ 解析和工作区内安装的 `xdis 6.3.0`，将原 Python 3.11 marshal 解为版本独立代码对象并按 opcode311 反汇编；从未 `exec` 或导入被提取的 pet 模块。xdis 本身作为解析依赖运行。`extract_click_evidence.py` 可复现聚焦分析，生成 `click-evidence.json` 和 `click-evidence.txt`。JSON 留存原归档成员偏移、模块 marshal 摘要、方法原文件名/首行及原始 `co_code` SHA-256。文本反汇编为可逐指令复核的一手派生证据。

## 已由字节码建立的普通点击 Q 弹

这是**整帧压扁后恢复**，没有 Q 弹自身的向上平移、旋转、弹簧超调或单独头部形变：

```text
p = clamp(elapsed_ms / 220, 0, 1)
pulse = sin(pi * p)
sx = 1 + 0.10 * pulse
sy = 1 - 0.15 * pulse
w = max(1, int(round(frame_width * sx)))
h = max(1, int(round(frame_height * sy)))
x = int(round((window_width - w) / 2))
y = window_height - h
```

即 0ms 为原比例，约 110ms 到横向 110%、纵向 85%，220ms 恢复原比例。支点是水平中心、绘制内容帧的底边。这里“整帧”包括该素材帧自身的透明留白，不能直接把 `head_box` 或人体可见包围盒当作同一支点。

### 普通窗口路径

- `pet.window._squash_geometry`，原 `pet\window.py:200–216`：上述公式、整数取整和底边定位。
- `PetWindow.__init__`，原 `pet\window.py:677–678`：`_squash_duration_ms = 220`，初始 progress 1.0；计时用 `QElapsedTimer`，定时器类型 `PreciseTimer`。
- `PetWindow.mouseReleaseEvent`，原 `pet\window.py:3261` 的非拖动点击分支：调用 `_on_click`，而不是普通按下阶段直接 `_start_squash`。
- `PetWindow._on_click`，原 `pet\window.py:3376`：先检查刚拖动/特效消费/旋转路由、点击素材存在性；正常分支在原行 3400 `_start_squash()`，3401 `_switch(click_name)`。也就是说压扁效果与点击视频是两个同时存在的层次。
- `PetWindow._start_squash`，原 `pet\window.py:2388–2395`：active=True、progress=0.0，重新 `clock.start()`、`timer.start()`；没有积累脉冲或增加幅度。因此连点会从原进度 0 重新播放固定幅度，而不是从当前姿态连续追赶，也不是加高。
- `PetWindow._on_squash_tick`，原 `pet\window.py:2397–2413`：progress=min(1,elapsed/duration)，到 1 后 active=False 并停 timer；progress 数值保留 1，但不再走变形分支。
- `PetWindow._frame_draw_rect`，原 `pet\window.py:2143–2157`：active 时用 `_squash_geometry` 的整帧矩形；否则返回原 content 矩形。

### Overlay / sprite 路径

- `pet.pet_sprite` 模块原行 44：`SQUASH_DURATION_MS = 220`。
- `pet.overlay_shell.ShellOverlayWindow.mouseReleaseEvent`，原 `pet\overlay_shell.py:836–839`：普通松开点击先 `behavior.on_sprite_clicked(grab)` 切点击行为，再通过 `getattr(grab, 'squash')` 调 `squash()`。此前探头/旋转路由可能提前消费点击，因此这是普通路径证据。
- `PetSprite.squash`，原 `pet\pet_sprite.py:1120–1124`：直接 `_squash_progress=0.0` 并通知脏区。
- `PetSprite.advance`，原行 1034–1037：进度每次增加 `dt / (220 / 1000.0)`；到 >=1 后将进度设成 `None`。这里 dt 为秒，与普通窗口 elapsed 毫秒的表示不同，时长相同。
- `PetSprite._squashed_rect`，原 `pet\pet_sprite.py:1126–1136`：相同 `sin(pi*p)`、横向 +10%、纵向 -15%，x 居中，y 保持原 rect 底边。
- `PetSprite.paint`，原 `pet\pet_sprite.py:1138`：整帧绘入 `_squashed_rect()`；另有独立探头旋转 helper，但 Q 弹公式本身没有按 `head_box` 分开画头部。

## 不能冒充的运行结论

以上是特定发行物中普通点击路径的静态事实，**不是实机点击录像或当前设置状态的观测**。不能据此证明用户当前启用普通模式、显示哪一个角色、是否由探头/旋转特效消费了点击，或用户说的“点击后的效果”仅指 Q 弹而不包括点击视频。

点击视频与几何 Q 弹要分开：正常点击同时切换点击动画资源。已有历史调查表明 shenshen 的点击 WebM 有 241 帧、24fps；那约 10 秒的角色素材并不等于 220ms 几何 Q 弹。若需要完整复刻用户实机观感，还应以用户当前显示的角色进行点击观察。

`head_box` 是否参与其他命中或特殊效果不在此处作全局否定；本报告仅确认上述 Q 弹绘制路径使用整帧矩形，未作单独头部变换。无需复制任何 dsh-pet 角色图像即可将该几何曲线应用到本项目自有角色上供用户判断。
