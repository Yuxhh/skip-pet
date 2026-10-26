"""Windows/NTFS + real Node plugin + native Qt verification, isolated from user data.

The event source is controlled, so this proves transport and rendering, not host
coverage. Suspend/resume applies only to the child created by this script.
"""
from collections.abc import Callable
import ctypes
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.task_bridge import TaskMonitor
from sukuna_pet.task_bubble import TaskBubble


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    bridge = root / "bridge"
    env = dict(os.environ, SUKUNA_PET_BRIDGE_DIR=str(bridge))
    app = QApplication.instance() or QApplication([])
    output = (root / "writer.log").open("w", encoding="utf-8")
    child = subprocess.Popen(["node", "tests/bridge_process.mjs"], stdin=subprocess.PIPE,
                             stdout=output, stderr=subprocess.STDOUT, text=True, env=env,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    monitor = TaskMonitor(bridge)
    pet = PetApplication(settings_path=root / "preferences.json")
    pet.select_mode("task")
    window = PetWindow(pet, task_monitor=monitor)
    window.move(600, 400)
    window.show()
    bubble = window.findChild(TaskBubble)
    assert bubble is not None
    gaps: list[float] = []
    last = [monotonic()]
    def tick() -> None:
        current = monotonic()
        gaps.append(current - last[0])
        last[0] = current
    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(16)
    stages: list[dict] = []
    def record(name: str) -> None:
        stages.append(dict(name=name, summary=asdict(monitor.summary),
                           bubble_visible=bubble.isVisible(), bubble_text=bubble.text(),
                           stage=pet.view.stage, holding=pet.view.holding))
        window.grab().save(str(root / f"{name}.png"))
        if bubble.isVisible():
            bubble.grab().save(str(root / f"{name}-bubble.png"))
    def wait_for(predicate: Callable[[], bool], seconds: float = 5) -> None:
        until = monotonic() + seconds
        while monotonic() < until:
            if predicate():
                QTest.qWait(40)
                return
            QTest.qWait(20)
        raise AssertionError(f"timed out: {monitor.summary}")
    def send(command: str) -> None:
        assert child.stdin is not None
        child.stdin.write(command + "\n")
        child.stdin.flush()
    ntdll = ctypes.WinDLL("ntdll")
    suspend = ntdll.NtSuspendProcess
    resume = ntdll.NtResumeProcess
    suspend.argtypes = resume.argtypes = [ctypes.c_void_p]
    suspended = False
    try:
        QTest.qWait(300)
        send("start")
        wait_for(lambda: monitor.summary.running == 1)
        assert bubble.isVisible()
        record("running")
        send("load")
        QTest.qWait(1600)
        wait_for(lambda: monitor.summary.running == 1)
        record("after-load")
        # Native mouse input remains responsive while transport I/O is active.
        pet.select_mode("click")
        QTest.qWait(600)
        image = window.grab().toImage()
        point = next(QPoint(x, y) for y in range(image.height() // 3, image.height())
                     for x in range(image.width() // 3, image.width() * 2 // 3)
                     if image.pixelColor(x, y).alpha() > 200)
        before = pet.view.stage
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
        QTest.qWait(600)
        assert pet.view.stage != before
        original = window.pos()
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(window, point + QPoint(70, 30), 80)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=point + QPoint(70, 30))
        QTest.qWait(100)
        assert window.pos() != original
        pet.select_mode("task")
        assert suspend(int(child._handle)) == 0
        suspended = True
        wait_for(lambda: not monitor.summary.text, 4)
        assert monitor.summary.jump and not bubble.isVisible()
        record("suspended-hidden-grace")
        wait_for(lambda: not monitor.summary.jump, 6)
        record("suspended-expired")
        assert resume(int(child._handle)) == 0
        suspended = False
        wait_for(lambda: monitor.summary.running == 1)
        assert monitor.summary.completed == 0
        record("resumed")
        send("close")
        wait_for(lambda: not monitor.summary.text, 2)
        assert monitor.summary.jump
        record("closed-hidden-grace")
        wait_for(lambda: not monitor.summary.jump, 6)
        record("closed-expired")
        child.wait(timeout=3)
        assert child.returncode == 0
        assert max(gaps) < .5, max(gaps)
        report = dict(platform=sys.platform, filesystem="Windows local NTFS workspace",
                      source="actual plugin with controlled host event source", stages=stages,
                      qt_timer_samples=len(gaps), max_qt_gap_ms=round(max(gaps) * 1000, 2),
                      mouse_click=True, mouse_drag=True,
                      writer_pid=child.pid, protocol_version=1, plugin_version="0.2.0")
        (root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True))
    finally:
        if suspended:
            resume(int(child._handle))
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=3)
        window.close()
        timer.stop()
        app.processEvents()
        output.close()


if __name__ == "__main__":
    main()
