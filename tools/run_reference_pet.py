"""Preview the actual bridge in task mode without saving new preferences."""

from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from sukuna_pet.desktop import PetWindow  # noqa: E402
from sukuna_pet.playback import PetApplication  # noqa: E402
from sukuna_pet.task_bridge import TaskMonitor, bridge_directory  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("skip-pet")
    app.setApplicationName("sukuna-pet-reference-preview")
    pet = PetApplication()
    pet.select_mode("task")
    monitor = TaskMonitor()
    window = PetWindow(pet, task_monitor=monitor)
    window.setWindowTitle("宿傩桌宠 · DeepSeek 接入预览")
    window.show()
    output = ROOT / ".scratch/issue38-live"
    output.mkdir(parents=True, exist_ok=True)
    (output / "launch.json").write_text(json.dumps({"mode": "task", "bridge": str(bridge_directory())},
                                                  ensure_ascii=False), encoding="utf-8")
    previous = [""]

    def observe() -> None:
        value = asdict(monitor.summary)
        signature = json.dumps(value, sort_keys=True)
        if signature != previous[0]:
            previous[0] = signature
            with (output / "observations.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"at": monotonic(), **value}, ensure_ascii=False) + "\n")
    timer = QTimer(window)
    timer.timeout.connect(observe)
    timer.start(100)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
