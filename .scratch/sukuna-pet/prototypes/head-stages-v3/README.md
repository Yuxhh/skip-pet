# Rear collar completion preview V3 (awaiting feedback)

User request: complete the back half of the collar. The original high front
collar may cover the chin; the previous face, jaw/neck and gaze-3 -9 degree
corrections remain the baseline for this prototype.

Open `index.html` directly. The standalone file embeds all required assets.
The rear rim and dark inner lining form a fixed layer behind the moving
head and neck. The original body and front collar remain above/below their
existing occlusion boundaries, so only the previously hidden rear region
is filled. Head/eye parameters and source-stage correspondence are retained.

Use the checkbox 后衣领补全 to compare with the previous missing region.
The 完整衣领层 option shows the empty completed collar without the head.
Stage cards and 下一阶段 let the user inspect the collar at each head pose.

`rear-collar-complete.png` is the generated headless garment asset. The
preview consumes only its rear-collar region, preserving original shoulders,
front rim and silver buttons. `asset-geometry.json` records alignment and
`generation-prompts.md` records the built-in image_gen edit prompt.

This remains an independent 2D preview. No production asset, native runtime,
installer or installed application has been replaced. Visual acceptance is
still the user's decision.
