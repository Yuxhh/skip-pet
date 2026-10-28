"""Audio-driven poses and the real Qt loop/deadline/manual-replay boundary."""

import json
import math
from pathlib import Path
import time
import wave

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

import sukuna_pet.desktop as desktop
import sukuna_pet.music as music
from sukuna_pet.desktop import PetWindow
from sukuna_pet.music import CLIP, MusicPlayer
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings import load_mode
from test_modes_desktop import choose


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def wait_for(predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert predicate()


def test_clip_has_the_user_confirmed_fourteen_second_boundary() -> None:
    with wave.open(str(CLIP), "rb") as sound:
        assert sound.getframerate() == 44100
        assert sound.getnchannels() == 1 and sound.getsampwidth() == 2
        assert sound.getnframes() == 14 * 44100
    assert music.SESSION_MS == 15_000


def test_music_pose_follows_audio_position_and_repeats_without_render_drift() -> None:
    pet, stalled = PetApplication(), PetApplication()
    rhythm = json.loads((CLIP.parent / "music-rhythm.json").read_text())
    for item in (pet, stalled):
        item.select_mode("music")
        item.click()
    pet.set_music_position(rhythm["first_beat_ms"])
    assert pet.view.bounce_scale == pytest.approx((1.1, .85))
    on_beat = pet.view
    pet.set_music_position(rhythm["first_beat_ms"] + rhythm["beat_ms"] / 2)
    assert pet.view.bounce_scale == (1, 1)
    pet.set_music_position(14_000 + rhythm["first_beat_ms"])
    assert pet.view == on_beat
    # A slow render frame cannot advance the music pose ahead of its audio.
    for item in (pet, stalled):
        item.set_music_position(1523)
    stalled.advance(8000)
    assert stalled.view == pet.view


def test_stop_stays_static_even_with_running_tasks_and_restart_is_manual(tmp_path: Path) -> None:
    path = tmp_path / "mode.json"
    pet = PetApplication(settings_path=path)
    pet.select_mode("always")
    pet.advance(70)
    pet.select_mode("music")
    pet.click()
    pet.set_music_position(2400)
    pet.stop_music()
    neutral = pet.view
    assert pet.mode == "music" and neutral.holding
    pet.set_task_running(True)
    pet.advance(60_000)
    assert pet.view == neutral and not pet.music_requested
    pet.click()
    assert pet.music_requested
    pet.set_music_position(0)
    assert not pet.view.holding
    pet.click()
    assert pet.view == neutral and not pet.music_requested
    assert load_mode(path) == "music"
    fresh = PetApplication(settings_path=path)
    assert fresh.view == neutral and not fresh.music_requested
    pet.select_mode("task")
    assert not pet.view.holding  # Explicit mode selection can resume tasks.


def test_drag_does_not_start_music_but_click_does() -> None:
    pet = PetApplication()
    pet.select_mode("music")
    pet.pointer_press((10, 10), (100, 100), drag_distance=5)
    assert pet.pointer_release((50, 50)) == (140, 140)
    assert not pet.music_requested
    pet.pointer_press((10, 10), (100, 100), drag_distance=5)
    assert pet.pointer_release((10, 10)) is None
    assert pet.music_requested


def test_real_player_loops_then_stops_once_and_can_restart(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A short audible fixture crosses several real backend loop boundaries
    # without making every test suite play the full song for 15 seconds.
    source = tmp_path / "loop.wav"
    from array import array
    with wave.open(str(source), "wb") as stream:
        stream.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        stream.writeframes(array("h", (int(800 * math.sin(i * math.tau * 300 / 16000))
                                      for i in range(1600))).tobytes())
    monkeypatch.setattr(music, "SESSION_MS", 650)
    player = MusicPlayer(source=source)
    stopped: list[bool] = []
    failed: list[bool] = []
    player.stopped.connect(lambda: stopped.append(True))
    player.failed.connect(lambda: failed.append(True))
    try:
        player.play()
        positions: list[int] = []
        deadline = time.monotonic() + 4
        while player.active and time.monotonic() < deadline:
            QTest.qWait(15)
            position = player.position_ms
            if position is not None:
                positions.append(position)
        assert not failed and not player.active
        assert stopped == [True]
        assert len(positions) >= 5
        assert any(b < a for a, b in zip(positions, positions[1:])), "audio must actually loop"
        QTest.qWait(100)
        assert player.position_ms is None and len(stopped) == 1
        player.play()
        wait_for(lambda: player.position_ms is not None)
        assert player.position_ms < 100
        player.stop()
        assert len(stopped) == 2 and not player.active
    finally:
        player.stop()
        player.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_missing_audio_fails_to_silence_instead_of_retrying_forever(
    app: QApplication, tmp_path: Path,
) -> None:
    player = MusicPlayer(source=tmp_path / "missing.wav")
    failed: list[bool] = []
    stopped: list[bool] = []
    player.failed.connect(lambda: failed.append(True))
    player.stopped.connect(lambda: stopped.append(True))
    player.play()
    assert failed == [True] and stopped == [True]
    assert not player.active and player.position_ms is None
    player.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_menu_music_is_below_tasks_and_silences_when_switching_or_closing(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pet = PetApplication()
    window = PetWindow(pet)
    window.show()
    try:
        class InspectMenu(QMenu):
            def exec(self, point: QPoint) -> None:
                labels = [a.text() for a in self.actions()]
                assert labels[labels.index("任务联动") + 1] == "音乐跳动"
                next(a for a in self.actions() if a.text() == "音乐跳动").trigger()

        monkeypatch.setattr(desktop, "QMenu", InspectMenu)
        point = window.visible_region.boundingRect().center()
        QApplication.sendEvent(window, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point)))
        wait_for(lambda: window.music_playing and not pet.view.holding)
        choose(window, "任务联动", monkeypatch, "音乐跳动")
        assert not window.music_playing and pet.mode == "task"
        choose(window, "音乐跳动", monkeypatch, "任务联动")
        wait_for(lambda: window.music_playing)
        # Clicking the same selected item is an explicit stop, then replay.
        choose(window, "音乐跳动", monkeypatch, "音乐跳动")
        assert not window.music_playing and pet.view.holding
        choose(window, "音乐跳动", monkeypatch, "音乐跳动")
        wait_for(lambda: window.music_playing)
        window.close()
        assert not window.music_playing and not pet.music_requested
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
