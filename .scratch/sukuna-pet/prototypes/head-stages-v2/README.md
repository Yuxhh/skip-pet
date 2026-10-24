# Head, jaw and neck repair preview V2 (awaiting feedback)

User feedback: gaze 2 looked flattened, the neck appeared disconnected,
gaze 3 must change from -11.3 to -9 degrees, and the missing chin needs
completion using the supplied video and photos.

Open `index.html` directly, or use the current local preview. Original
eye rules and phase boundaries remain: fixed 3x gaze transitions, hold
at gaze 2, a separate click to gaze 3 and one 240ms blink.

## Changes

- Replaced the affine face fit with rotation plus uniform scale. No
  horizontal/vertical scale mismatch or shear is applied to the face,
  including during interpolation. Gaze 2 preserves its face proportions.
- Gaze 3 endpoint angle is exactly -9 degrees.
- The built-in image generator created a complete jaw/chin/neck repair
  plate using the approved illustration and user keyframes as references.
  Original upper-face detail, eyes and hair are retained in the animation;
  the plate supplies the previously hidden chin and neck.
- Neck upper vertices follow the head; the lower end blends into a fixed
  collar attachment. The entire face and jaw remain rigid above the neck.
- User clarified the collar may cover the chin. The original high collar
  and body are retained; complete jaw/neck artwork moves behind it.
  Shoulders remain fixed across stages.

This is an independent preview, not native integration. Old prototypes
remain in the sibling directory. Production assets are not overwritten.

## Assets and generation

`head-neck-repair.png`: generated isolated full head/neck plate on real
transparent background. Asset alignment and jaw/neck geometry are in
`asset-geometry.json`; head poses are in `motion-parameters.json`.
`generation-prompts.md` records the prompts and input roles. Generation
used the built-in image_gen tool, not the API/CLI fallback.

## Limits

This is layered 2D animation, not reconstructed 3D head rotation. Shadow
planes and complete jaw/neck artwork supply depth while head proportions
are preserved. The source video cuts before a complete stage 3 to 0
return, so that return is still interpolated. Visual acceptance belongs
to the user, not the browser checks.
