"""Check moving Windows pixels against whole painted frames in two processes.

Uses public Qt clicks at real time, not OS mouse injection. The observer captures
independently so it can see intermediate native window states without delaying
the pet event loop. Requires an unobscured primary Windows screen at DPR 1.
Each run owns an isolated output directory and never reads user preferences.
"""

import argparse
import ctypes
from ctypes import wintypes
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPaintEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.rendering import SOURCE_BOUNDS
from sukuna_pet.settings import save_size


class Background(QWidget):
    def __init__(self, background: str) -> None:
        super().__init__()
        self.background = background

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#263347" if self.background == "dark" else "#f3f2ee"))
        if self.background == "texture":
            for x in range(0, self.width(), 18):
                for y in range(0, self.height(), 18):
                    colour = "#c7c7c7" if (x // 18 + y // 18) % 2 else "#eeeeee"
                    painter.fillRect(x, y, 18, 18, QColor(colour))


def digest(image: QImage) -> str:
    # Keep the QImage alive until the constBits view has been copied.
    converted = image.convertToFormat(QImage.Format.Format_RGB32)
    return sha256(bytes(converted.constBits())).hexdigest()


def observe(app: QApplication, output: Path, rect: QRect, seconds: float) -> int:
    screen = app.primaryScreen()
    assert screen is not None
    samples: dict[str, QImage] = {}
    count = 0
    (output / "ready").touch()
    started = perf_counter()
    while perf_counter() - started < seconds:
        # Synchronize only the independent capture process with the compositor.
        ctypes.windll.dwmapi.DwmFlush()
        image = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height()).toImage()
        samples[digest(image)] = image
        count += 1
    for key, image in samples.items():
        image.save(str(output / f"capture-{key}.png"))
    (output / "observer.json").write_text(json.dumps({
        "captures": count, "unique_frames": len(samples),
    }, indent=2), encoding="utf-8")
    return 0


def verify(args: argparse.Namespace, app: QApplication, output: Path, rect: QRect) -> int:
    receiver = Background(args.background)
    receiver.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    screen = app.primaryScreen()
    assert screen is not None
    receiver.setGeometry(screen.availableGeometry())
    receiver.show()
    QTest.qWait(60)
    backdrop = receiver.grab().toImage().copy(rect.translated(-receiver.pos()))
    expected: dict[str, QImage] = {}

    class ObservedWindow(PetWindow):
        def paintEvent(self, event: QPaintEvent) -> None:
            super().paintEvent(event)
            image = backdrop.copy()
            painter = QPainter(image)
            painter.drawImage(0, 0, self.frame)
            painter.end()
            expected[digest(image)] = image

    preferences = output / "preferences.json"
    save_size(preferences, args.height)
    pet = PetApplication()
    window = ObservedWindow(pet, settings_path=preferences)
    observer: subprocess.Popen[bytes] | None = None
    timer = QTimer()
    hits: list[tuple[int, int]] = []
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    try:
        window.move(rect.topLeft())
        window.show()
        QTest.qWait(100)
        observer = subprocess.Popen([
            sys.executable, str(Path(__file__).resolve()), "--observe",
            "--output", str(output), "--height", str(args.height),
            "--duration", str(args.duration),
        ])
        started: float | None = None
        clicks = 0

        def click() -> None:
            nonlocal started, clicks
            if not (output / "ready").exists():
                return
            if started is None:
                started = perf_counter()
            if perf_counter() - started < args.duration - 1 and (not args.single or clicks == 0):
                # The centre is inside the character in every approved pose.
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.rect().center())
                clicks += 1
            if observer is not None and observer.poll() is not None:
                for point, target in ((window.rect().center(), window), (QPoint(2, 2), receiver)):
                    global_point = window.mapToGlobal(point)
                    actual = int(user32.WindowFromPoint(wintypes.POINT(global_point.x(), global_point.y())) or 0)
                    hits.append((actual, int(target.winId())))
                app.quit()

        timer.timeout.connect(click)
        timer.start(args.interval)
        QTimer.singleShot(round((args.duration + 15) * 1000), app, app.quit)
        app.exec()
        timer.stop()
        assert observer.wait(timeout=10) == 0
        captures = list(output.glob("capture-*.png"))
        unmatched = [path for path in captures if path.stem.removeprefix("capture-") not in expected]
        for key, image in expected.items():
            image.save(str(output / f"expected-{key}.png"))

        # These native hit checks are intentionally taken after the motion.
        # The independent frame test above covers continuous composition.
        assert len(hits) == 2 and all(actual == target for actual, target in hits), hits
        observer_result = json.loads((output / "observer.json").read_text(encoding="utf-8"))
        result = {
            "height": args.height, "background": args.background,
            "input": "public Qt clicks, real time; separate Windows desktop capture process",
            "interval_ms": args.interval, "clicks": clicks, "duration_seconds": args.duration,
            "screen": {"name": screen.name(), "geometry": screen.geometry().getRect(),
                       "work_area": screen.availableGeometry().getRect(), "dpr": screen.devicePixelRatio()},
            **observer_result, "painted_frames": len(expected),
            "incomplete_frames": len(unmatched), "failures": [p.name for p in unmatched],
            "visible_hit": "pet", "transparent_hit": "receiver",
            "limitations": "Single primary screen DPR 1, finite sampling, public Qt input; not physical mouse or mixed-DPI acceptance",
        }
        (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "failures"}))
        assert clicks >= (1 if args.single else 8) and len(expected) >= 3, "Insufficient movement coverage"
        assert len(captures) >= 3, "Insufficient distinct desktop frames captured"
        assert not unmatched, f"{len(unmatched)} displayed images do not match any complete painted frame"
        return 0
    finally:
        timer.stop()
        if observer is not None and observer.poll() is None:
            observer.terminate()
            observer.wait(timeout=10)
        window.close()
        receiver.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--height", type=int, choices=(188, 271, 320), default=320)
    parser.add_argument("--background", choices=("light", "dark", "texture"), default="dark")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--duration", type=float, default=4)
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--observe", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.duration < 2 or args.interval < 1:
        parser.error("Use duration >= 2 seconds and interval >= 1ms")
    output = args.output.resolve()
    if not args.observe and output.exists() and any(output.iterdir()):
        parser.error("Use a new or empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    assert app.platformName() == "windows", "Requires a real Windows desktop"
    screen = app.primaryScreen()
    assert screen is not None and screen.devicePixelRatio() == 1, "This probe requires primary DPR 1"
    width = math.ceil(args.height * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height())
    rect = QRect(0, 0, width, args.height)
    rect.moveCenter(screen.availableGeometry().center())
    if args.observe:
        return observe(app, output, rect, args.duration)
    return verify(args, app, output, rect)


if __name__ == "__main__":
    raise SystemExit(main())
