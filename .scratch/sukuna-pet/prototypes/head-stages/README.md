# Four gaze stages, head motion preview (unapproved)

User direction, 2026-10-25: first change the head, using the four supplied
keyframes as gaze 0, 1, 2, 3 in that exact order. Previous dsh-pet Q-squash is
on hold and is not applied here. This is an independent prototype; production
code and the installed application were not changed.

Open `index.html` directly. Everything required for viewing is embedded.
Click 下一阶段 or the character to advance; click a stage card to inspect
an endpoint. 连续演示 inserts a hold between stages. Four-times slower,
head-only, eye-only and source-video-frame comparisons are available.

## Source and method

New video: `7a2c94ac95a259ef897d54bfcd0cc940.mp4`, 576x1280, 24fps,
80 frames, 3.33 seconds. Only the close-up before the shot change is used.
User images, in order: ad4db390..., aa9e00dd..., f61d5bcc..., 11118587....
Nearest-frame comparison after resizing screenshots to 576x1280 places them
near zero-based f016 / f028 / f039 / f053, or .667 / 1.167 / 1.625 / 2.208s.
Screenshot overlays and compression differ; these are nearest matches.

Manual points on the forehead, eyelid outer corners, nose, mouth and chin
are compared after a similarity alignment of two coat buttons. This removes
an estimate of camera/body translation, scale and roll. A least-squares face
affine fit drives the approved sprite around its chin; the measured chin
displacement sets the translation separately. Face fitting RMSE is about
7.7 / 3.0 / 5.5 reference pixels for stages 1 / 2 / 3. It is an approximate
2D transfer, not reconstructed 3D head rotation or automatic landmark tracking.

| Gaze | Head endpoint | Relative x-axis angle |
|---|---|---|
| 0 | relatively straight, low head | 0 degrees |
| 1 | lean toward screen left, extend/lift | -6.4 degrees |
| 2 | return toward straight, lower head | +1.2 degrees |
| 3 | lean left and lift | -11.3 degrees |

The torso, collar and chest remain fixed. Source and moving head use separate
masks so hidden old-ear pixels do not remain on the body, and collar pixels
are not carried with the head. Front collar is drawn last for occlusion.

Ordinary eye transitions retain the previous fixed 3x phase advancement.
Gaze 2 holds until another click. Entering gaze 3 uses the existing 240ms
blink, eye-position jump at closure, and continuous head motion throughout.
The head interpolates between fitted endpoints with smoothstep in the
existing phase timeline. This is not source-video frame-for-frame retiming.
The stage 3 to 0 closing transition is interpolated; the video cuts to a
different shot rather than providing that return path.

`motion-parameters.json` contains the manually estimated landmarks,
normalization, matrices and boundaries. `eyes.js` preserves the prior eye
model. `build_preview.py` embeds the assets into the standalone page.
Research scripts and annotated comparisons live in
`.scratch/sukuna-pet/research/head-stages-20261025/`.

## Status

Waiting for the user's visual feedback. Browser checks establish page
operation and stage behavior only; they do not establish visual acceptance.
No native integration, packaging or installation replacement has occurred.
