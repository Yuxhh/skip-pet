# dsh-pet 普通点击 Q 弹 · 聚焦结论

**静态字节码事实，未观测实际运行。** 未执行提取代码、未修改参考目录。来源 exe SHA-256：`687255faea034bd0e672a870da732650dbbd5b9aae050586e143ac1e55c50407`。

| 项目 | 普通 PetWindow 与 Overlay PetSprite 的共同结论 |
|---|---|
| 时长 | 220ms |
| 进度 | `p=clamp(elapsed/220,0,1)`（sprite 用秒 dt 等价累加） |
| 曲线 | `pulse=sin(pi*p)` |
| 水平比例 | `sx=1+0.10*pulse`，中点 110% |
| 垂直比例 | `sy=1-0.15*pulse`，中点 85% |
| 几何 | 绘制整帧，水平居中、底边锚定；w/h/x 作整数 round |
| 开始/结束 | 原比例 → 压扁加宽 → 原比例；Q 弹本身无上跳、旋转、超调、单独头部伸缩 |
| 单击触发 | 普通非拖动路径在 mouse release 后触发 |
| 连点 | 进度归 0、重启同一脉冲，不累加、不平滑追赶 |
| 结束状态 | 普通窗口 active=False，返回原 content rect；sprite progress=None，恢复原 rect |

整帧包括素材的透明留白。将同一曲线作用到宿傩全帧，比按可见人体包围盒重新定锚更忠于这个几何算法。

关键定位（原文件/行号来自代码对象，非恢复出的原始源码）：

- `pet.window._squash_geometry`：`pet\window.py:200–216`，完整公式。
- `PetWindow.__init__`：`pet\window.py:677`，duration=220。
- `PetWindow._start_squash`：`pet\window.py:2388–2395`，重置/重启。
- `PetWindow._on_squash_tick`：`pet\window.py:2397–2413`，到 1 后停止。
- `PetWindow._frame_draw_rect`：`pet\window.py:2143–2157`，整帧绘制矩形。
- `PetWindow._on_click`：`pet\window.py:3376`，原行 3400 squash，3401 切点击视频。
- `ShellOverlayWindow.mouseReleaseEvent`：`pet\overlay_shell.py:836–839`，on_sprite_clicked 后调用 squash。
- `pet.pet_sprite` 模块：`pet\pet_sprite.py:44`，SQUASH_DURATION_MS=220。
- `PetSprite._squashed_rect`：`pet\pet_sprite.py:1126–1136`，与普通窗口完全相同强度和锚定。
- `PetSprite.squash`：`pet\pet_sprite.py:1120–1124`，progress=0。
- `PetSprite.advance`：`pet\pet_sprite.py:1034–1037`，结束后 progress=None。

定位证据：同目录 `click-evidence.txt`（过滤 CACHE 的 13 方法/关键片段反汇编）、`click-evidence.json`（归档位置、模块 marshal SHA、方法 bytecode SHA）。复现脚本 `extract_click_evidence.py` 采用自编只读 CArchive/PYZ 解析及 xdis 6.3.0；未执行 pet 模块。详细解释见 `README.md`。

边界：探头/旋转特效可能提前消费点击，正常路径也同时切换角色点击视频。故此结论只证明发行物中普通点击 Q 弹算法，不能证明当前启用哪个路径，也不能把它冒称用户实机完整点击效果已观测或已认可。
