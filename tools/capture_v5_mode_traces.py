"""Execute the immutable native V5 scheduler and JS model to capture an oracle.

Only drawing and wall-clock flushing are omitted. Each input frame is capped by
the original driver; its <=4ms model steps and whole-frame wait accounting run
unchanged. No production playback code is imported.
"""

import ast
import json
from pathlib import Path
import re
import subprocess
import tempfile

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine


COMMIT = "4ecb85c8a087ca89fb99a3a2125c826801b53e1c"
ROOT = ".scratch/sukuna-pet/prototypes/native-v5/"


def read(name: str) -> str:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{ROOT}{name}"], encoding="utf-8")


def capture() -> dict:
    source = read("preview.py")
    tree = ast.parse(source)
    model = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Model")
    pet = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Pet")
    methods = [n for n in pet.body if isinstance(n, ast.FunctionDef)
               and n.name in ("advance_elapsed", "click_stage", "select_mode")]
    scenarios = [
        ("cycles_16ms", 16, 420, {}),
        ("cycles_33ms", 33, 200, {}),
        ("delayed_frames_240ms", 240, 35, {}),
        ("manual_regular", 16, 260, {4: "click"}),
        ("manual_wait", 16, 260, {24: "click"}),
        ("manual_closing", 16, 300, {87: "click"}),
        ("manual_opening", 16, 300, {94: "click"}),
        ("rapid_replacements", 16, 300, {i: "click" for i in (3, 6, 9, 12, 15)}),
        ("stop_regular", 16, 100, {4: "click_mode"}),
        ("stop_bounce_after_head", 16, 100, {12: "click_mode"}),
        ("stop_wait", 16, 100, {24: "click_mode"}),
        ("stop_closing", 16, 160, {87: "click_mode"}),
        ("stop_opening", 16, 160, {94: "click_mode"}),
        ("resume_during_motion", 16, 260, {4: "click_mode", 6: "always"}),
        ("resume_from_wait", 16, 260, {24: "click_mode", 26: "always"}),
    ]
    with tempfile.TemporaryDirectory(dir=Path(".scratch").resolve()) as temporary:
        frozen = Path(temporary)
        for name in ("eyes.js", "rig.js", "bounce.js"):
            (frozen / name).write_text(read("frozen/" + name), encoding="utf-8")
        namespace = {"FROZEN": frozen, "QJSEngine": QJSEngine, "json": json,
                     "math": __import__("math"), "perf_counter": lambda: 0.0,
                     "PARAMS": json.loads(read("frozen/motion-parameters.json"))}
        exec(ast.get_source_segment(source, model), namespace)
        driver = "class Driver:\n" + "\n".join(
            "\n".join("    " + line for line in ast.get_source_segment(source, n).splitlines())
            for n in methods)
        exec(driver, namespace)
        traces = []
        template = read("frozen/preview.template.html")
        eye_setup = re.search(r"const keys=.*?\n.*?return l.slice.*?\}", template, re.S)[0]
        eye_setup = eye_setup.replace("const keys=", "var keys=")
        for name, frame_ms, frames, events in scenarios:
            d = namespace["Driver"]()
            d.model = namespace["Model"]()
            d.age, d.wait, d.frozen, d.demo = 10000, 0, False, False
            d.tick = lambda: None  # Inputs already flushed to the event's frame.
            d.render_frame = lambda: None
            d.model.run((frozen / "bounce.js").read_text() + "\n" + eye_setup + """
                var centers=[];var base={},sprite={};
                var noop=function(){};
                var sc={clearRect:noop,drawImage:noop,save:noop,restore:noop,
                  beginPath:noop,moveTo:noop,bezierCurveTo:noop,lineTo:noop,
                  closePath:noop,clip:noop,fill:noop,stroke:noop,
                  ellipse:function(x,y){centers.push([x,y])}};
                var tc={clearRect:noop,drawImage:noop};
                function sample(age){centers=[];eyes(s.eye,Motion.closure(s));
                  return JSON.stringify({stage:s.stage,
                    holding:!s.moving&&s.bodyAge>=s.bodyMs&&!(s.blinkAge<240),
                    right_eye:centers[0],left_eye:centers[3],
                    head_phase:Motion.mod(s.body),head_matrix:Rig.sample(s.body,POSES),
                    eyelid_closure:Motion.closure(s),
                    bounce_scale:[Bounce.sample(age).sx,Bounce.sample(age).sy]})}
                var POSES=""" + json.dumps(namespace["PARAMS"]["components"]) + ";")
            mode = "always"
            d.select_mode(mode)
            observations = []
            for frame in range(frames + 1):
                if frame:
                    d.advance_elapsed(frame_ms)
                event = events.get(frame)
                if event == "click":
                    d.click_stage()
                elif event:
                    mode = "click" if event == "click_mode" else "always"
                    d.select_mode(mode)
                sample = json.loads(d.model.run(f"sample({d.age})").toString())
                observations.append({"frame": frame, "mode": mode, **sample})
            traces.append({"name": name, "frame_ms": frame_ms,
                           "events": events, "observations": observations})
    return {"source_commit": COMMIT,
            "source_files": ["preview.py", "frozen/eyes.js", "frozen/rig.js", "frozen/bounce.js"],
            "note": "Original native advance_elapsed/click_stage/select_mode and Model executed. "
                    "Whole-frame wait includes the frame becoming idle; >=450ms triggers at frame end. "
                    "Same capped frame inputs required; tolerance 1e-8 for state/eyes/bounce. "
                    "Drawing omitted; tick flush is a no-op at already advanced event times.",
            "traces": traces}


if __name__ == "__main__":
    app = QCoreApplication([])
    output = Path("tests/fixtures/v5-mode-traces.json")
    output.write_text(json.dumps(capture(), indent=2) + "\n", encoding="utf-8")
    print(f"Captured native V5 scheduling oracle: {output}")
