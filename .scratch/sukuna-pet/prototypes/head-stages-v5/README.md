# Head/neck plus dsh-pet click bounce V5 (awaiting feedback)

User request: add the previously made dsh-pet click effect to the current
prototype. Open index.html directly, or http://127.0.0.1:8780/.

V4's four gaze stages, fixed local neck center, uniform head transforms,
stage-3 -9 degrees, repaired chin/neck, original front collar and completed
rear collar remain. eyes.js and rig.js are unchanged from V4.

Every next-stage click also starts the previously researched ordinary
dsh-pet pulse: 220ms, sin(pi * progress), width 1 + .10 * pulse,
height 1 - .15 * pulse. Repeat clicks restart at zero without accumulating.
The complete composed character receives the same parent transform around
the full sprite's horizontal center and bottom edge (709.5,1108), including
transparent padding. No additional hop or rotation is added. Canvas uses
continuous scaling; unlike Qt's source geometry, it does not round each
scaled sprite dimension to integer source pixels.

The neck center remains fixed relative to the character during head tilt.
During the whole-character pulse, it follows the same parent transform as
the head and collar; it is not a screen-space pin. At rest the face retains
its V4 proportions; the temporary global squash intentionally changes
the whole character's proportions as requested.

点击 Q 弹 toggles the pulse for comparison. 查看回弹最强一帧 freezes both
head/eye playback and the pulse at 110ms (110% width / 85% height).
下一阶段 exits this diagnostic pause and starts a fresh pulse. 恢复正常播放
releases the diagnostic pause without advancing the gaze. Static endpoint
cards and left/right neck checks do not trigger pulses. Continuous demo
uses the same next-stage action; quarter-speed slows both motions equally.

Rebuild: python build_preview.py. observe_geometry.cjs and
observe_bounce.cjs record numerical observations. Browser screenshots and
OBSERVATIONS.md record interaction evidence, not human visual approval.
This is an isolated prototype; production and installed files unchanged.

Reference geometry evidence: ../dsh-click/README.md and the linked
read-only research on the prototype branch. This combines that ordinary
geometry pulse with our character; it does not copy the reference pet's
character-specific click video.
