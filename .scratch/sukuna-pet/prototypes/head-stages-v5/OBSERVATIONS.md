# V5 observations

- Browser loaded the standalone embedded HTML and all four endpoint cards.
- 最强一帧 displayed 110.0% / 85.0%, local neck drift 0.000px,
  gaze 0 and head at rest. Screenshot browser-peak.png shows the complete
  composed garment, head and neck squashed together.
- Next-stage click exited that frozen view, advanced to gaze 1, and started
  a fresh pulse at 0ms. Later state showed pulse recovered, gaze 1 held.
- Next clicks reached gaze 2, then gaze 3 with click/blink count 3 / 1.
- Rapid five clicks from gaze 3 reached cumulative 8 clicks, 2 blinks and
  gaze 0; the pulse recovered to 100% / 100% while head transition finished.
- Reset returned to gaze 0 with no pulse. browser-rest.png captures that
  rest posture from the same browser viewport as the peak screenshot.
- bounce-observations.json records 0/55/110/165/220/500ms pulse values,
  unchanged source eyes/rig, normal phase endpoints, rapid restart snapshots
  and fixed full-sprite anchor. Generated HTML script compiled successfully.
- geometry-observations.json retains V4's 4101-sample local-neck geometry
  observations. Global temporary pulse intentionally affects face ratio
  and screen-space neck position uniformly with the garment.

Browser screenshot API with fullPage was unavailable; screenshots were
captured through getScreenshot at a scrolled viewport containing the full
character. These observations establish operation, not user approval.
