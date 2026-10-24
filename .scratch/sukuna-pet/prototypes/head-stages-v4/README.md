# Fixed neck center prototype V4 (awaiting feedback)

User request: optimize neck direction and placement so that its center
remains unchanged when leaning left and right.

The previous prototype fixed only the lower neck attachment, while the
middle still followed independent head translation. This version removes
that reference-image translation and rotates the head and upper neck around
the same fixed neck-middle point `(720,735)` in the original sprite space.
The lower neck still blends into its rest attachment at y780. The head/neck
join follows the same transform and does not separate.

Head angles and uniform scales remain 0 / -6.44 / +1.17 / -9 degrees and
1 / 1.08 / 1.025 / 1.065. Eye phases, 3x timing and the stage-3 240ms blink
remain. Complete chin, neck and rear collar assets are reused unchanged.

Open `index.html` directly. Use 下一阶段 for normal stage playback.
显示固定中心 draws a diagnostic crosshair over the fixed center. 左偏 9°
检查 and 右偏 9° 检查 show the complete head/neck without the collar so
the same center can be inspected from both sides. 恢复阶段预览 returns
to the normal dressed character. Diagnostic markers are not character art.

`rig.js` contains the pure geometry. `observe_geometry.cjs` records center,
lower-attachment, join-continuity and face-ratio observations across a full
phase cycle. Browser screenshots establish visible operation, not approval.

This is a standalone prototype. No production or installed files changed.
