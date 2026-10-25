"""Regenerate immutable native V5 raster oracles; never import the Python port.

Requires historical Git objects and Qt. Ordinary tests only read the PNGs.
"""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

from PySide6.QtWidgets import QApplication


COMMIT = "4ecb85c8a087ca89fb99a3a2125c826801b53e1c"
ROOT = ".scratch/sukuna-pet/prototypes/native-v5/"
OUTPUT = Path("tests/fixtures/bounce-native")
SCENARIOS = [
    ("first_peak", [0], 110),
    ("first_recovered", [0], 220),
    ("second_peak", [0, 300], 410),
    ("blink_peak", [0, 300, 600], 710),
    ("closing_retarget_peak", [0, 300, 600, 660], 770),
    ("opening_retarget_peak", [0, 300, 600, 760], 870),
    ("rapid_peak", [0, 45, 90, 135, 180], 290),
    ("rapid_recovered", [0, 45, 90, 135, 180], 1500),
]


def main() -> None:
    app = QApplication.instance() or QApplication([])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scratch = Path(".scratch").resolve()
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix="issue24-oracle-") as temporary:
        root = Path(temporary)
        assert root.resolve().is_relative_to(scratch)
        names = ["preview.py", *["frozen/" + name for name in (
            "character.png", "head-neck-repair.png", "rear-collar-complete.png",
            "eyes.js", "rig.js", "motion-parameters.json",
        )]]
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(["git", "show", f"{COMMIT}:{ROOT}{name}"]))
        spec = importlib.util.spec_from_file_location("frozen_native_v5", root / "preview.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        renderer = module.Renderer()
        records = []
        for name, clicks, at in SCENARIOS:
            model = module.Model()
            time = 0
            for click in clicks:
                model.tick(click - time)
                model.next()
                time = click
            model.tick(at - time)
            for height, dpr in ((188, 1), (271, 1), (320, 1), (320, 1.5)):
                filename = f"{name}-{height}-{dpr}.png"
                renderer.render(model, model.state(), at - time, height, dpr).save(str(OUTPUT / filename))
                records.append({"file": filename, "clicks_ms": clicks, "at_ms": at,
                                "height": height, "dpr": dpr})
        (OUTPUT / "manifest.json").write_text(json.dumps({
            "source_commit": COMMIT, "source_files": names,
            "note": "Executed frozen native Model and Renderer, <=4ms model substeps. "
                    "Compare whole final Qt images; <=1 channel raster rounding tolerance. "
                    "DPR 1.5 is synthetic, not hardware evidence.",
            "samples": records,
        }, indent=2) + "\n", encoding="utf-8")
    print(f"Captured {len(records)} frozen native frames ({app.platformName()})")


if __name__ == "__main__":
    main()
