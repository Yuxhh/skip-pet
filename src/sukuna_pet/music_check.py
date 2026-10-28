"""Opt-in real Windows menu/audio check with isolated preferences."""

import json
from pathlib import Path
import sys
from time import perf_counter

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from .desktop import PetWindow
from .music import SESSION_MS
from .playback import PetApplication, PetView


def main(arguments: list[str]) -> int:
    root = Path(arguments[0]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(app, QApplication)
    app.setQuitOnLastWindowClosed(False)
    pet = PetApplication(settings_path=root / "mode.json")
    pet.select_mode("always")
    window = PetWindow(pet)
    window.show()
    result: dict[str, object] = {"frozen": bool(getattr(sys, "frozen", False))}
    started = 0.0
    stopped = 0.0
    last_position = 0.0
    looped = False
    neutral: PetView | None = None
    phase = "first"
    samples: list[list[float]] = []
    timer = QTimer(window)
    timer.setInterval(16)

    def finish(error: str = "") -> None:
        timer.stop()
        window.close()
        result.update(passed=not error, error=error, audio_clock_samples=samples,
                      close_stops_audio=not window.music_playing)
        (root / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(1 if error else 0)

    def choose_music() -> None:
        clicked: list[bool] = []

        def click() -> None:
            menu = app.activePopupWidget()
            assert isinstance(menu, QMenu)
            labels = [action.text() for action in menu.actions()]
            assert labels[labels.index("任务联动") + 1] == "音乐跳动"
            menu.grab().save(str(root / "music-menu.png"))
            action = next(a for a in menu.actions() if a.text() == "音乐跳动")
            QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
            clicked.append(True)

        QTimer.singleShot(80, click)
        point = window.visible_region.boundingRect().center()
        QApplication.sendEvent(window, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point)))
        assert clicked

    def poll() -> None:
        nonlocal started, stopped, last_position, looped, neutral, phase
        try:
            now = perf_counter()
            if phase == "first":
                player = window._music
                position = player.position_ms if player is not None else None
                if position is not None:
                    if not started:
                        started = now
                        device = QMediaDevices.defaultAudioOutput()
                        assert player is not None
                        assert player._device_id == device.id().data()
                        result.update(default_audio_output=device.description(),
                                      playback_device_id=player._device_id.decode(),
                                      using_current_default_output=True)
                    elapsed = now - started
                    if last_position > 13_000 and position < 1000:
                        looped = True
                    last_position = position
                    if not samples or elapsed * 1000 - samples[-1][0] > 250:
                        samples.append([round(elapsed * 1000, 2), round(position, 2)])
                    if 2 < elapsed < 2.2:
                        window.frame.save(str(root / "music-active.png"))
                elif started and not window.music_playing:
                    stopped = now
                    elapsed = stopped - started
                    assert 14.5 < elapsed < 15.6, f"Unexpected duration: {elapsed}"
                    assert looped, "The 14-second clip did not loop"
                    assert pet.mode == "music" and pet.view.holding
                    neutral = pet.view
                    window.frame.save(str(root / "music-stopped.png"))
                    result.update(duration_seconds=round(elapsed, 3), looped=True,
                                  did_not_resume_previous_always_mode=True, session_ms=SESSION_MS)
                    phase = "idle"
            elif phase == "idle":
                assert not window.music_playing and pet.view == neutral
                if now - stopped > .8:
                    choose_music()
                    phase = "replay"
            elif phase == "replay" and window.music_playing and not pet.view.holding:
                result["manual_replay"] = True
                window.select_mode("click")
                assert not window.music_playing
                result["mode_switch_stops_audio"] = True
                choose_music()
                phase = "close"
            elif phase == "close" and window.music_playing:
                finish()
        except Exception as error:
            finish(repr(error))

    def start() -> None:
        try:
            choose_music()
            timer.timeout.connect(poll)
            timer.start()
        except Exception as error:
            finish(repr(error))

    QTimer.singleShot(100, start)
    QTimer.singleShot(25_000, lambda: finish("Native audio/menu check timed out"))
    return app.exec()
