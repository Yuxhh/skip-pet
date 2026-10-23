# 透明半身素材原型（一次性）

回答的问题：[怎样的透明半身角色素材可以用于第一版](https://github.com/xyd-0811/skip-pet/issues/4)。

本目录是供真人反应的低成本素材原型，不是桌宠程序、最终素材或动画验收。双击 `index.html` 即可打开；也可在本目录运行 `python -m http.server 8767 --bind 127.0.0.1`。

## 本次可判断的内容

- 三张源帧（零起算）：f000 / 0.000s 是原片静止候选，f036 / 1.500s 是较清晰的倾斜姿态，f064 / 2.667s 是模糊与上缘裁切的压力帧。
- 每帧在浅色、深色及棋盘纹理背景上查看；滑块调整显示大小，局部放大图用于检查头发和衣领。
- `?variant=A` 保留原下沿；`?variant=B` 最后 28 源像素渐隐；`?variant=C` 在裁片 y380 上移截断。底部箭头和键盘左右键切换；`?frame=0|36|64` 可指定帧。
- 水印和 `XEN` 已在原视频像素中。A、B 保留对应区域；C 通过舍弃整个下胸区域减少可见内容，没有抹字或补画。

## 方法和限制

来自 [video-material 研究分支](https://github.com/xyd-0811/skip-pet/tree/research/video-material) 的 `research/diagnostics/spot-000.png`、`spot-036.png`、`spot-064.png`，均为原视频 `(0,415)-(576,865)` 裁片，大小 576 × 450。原视频不写入 Git、不改动。

人工轮廓多边形生成蒙版，按明度阈值 68 细化暗色边缘：y160 上方沿轮廓内外各 3 像素细化，其下仅向轮廓内部收紧；脸部保留手工蒙版，y260 以下用 3px 开运算抑制衣服旁的细背景毛刺。保留与胸部相连的区域，再做 0.45px alpha 软化。这种低成本方法无法可靠区分相邻的黑发与黑栏杆。源裁片最后 3 行视为源画面下界，透明化。RGBA 的 RGB 三通道逐像素保持源裁片原样；仅 alpha 改动。脚本内包含 RGB 相等断言，`manifest.json` 保存源 PNG 哈希、种子和参数。

源图既有模糊、亮边污染、上缘出画和下沿缺失不会被这套方法恢复。人工种子也可能漏掉细发丝，不能据此宣称已获得成品。当前只提取三张静帧，没有逐帧抠完整动作、同步锚点或验证循环；这些不属于本票的质量结论。

`transparency-contact-sheet.jpg` 是 A 方案三帧 × 三背景总览；`lower-edge-options.jpg` 是 f036 的下沿对照；PNG 文件含透明通道。JPG 只供看图，不能作为透明资源使用。

## 重新生成

依赖：Python、Pillow、numpy。读取已保存的研究裁片，不需重解码原视频。

```powershell
python build_preview.py --source-dir <研究分支的diagnostics目录>
```

## 真人验收记录

2026-10-24 已收到真人反馈，本素材方向决策票已完成。选定外观、接受范围及后续动画验收约束以[决策票的 resolution comment](https://github.com/xyd-0811/skip-pet/issues/4#issuecomment-6369881312)为准。本目录保留所有备选方案作为原始讨论证据。
