"""Exercise default-output changes without requiring physical hot-plugging."""

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QByteArray, QEvent, QObject, Signal
from PySide6.QtMultimedia import QtAudio
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import sukuna_pet.music as music


@pytest.fixture
def outputs(monkeypatch: pytest.MonkeyPatch):
    app = QApplication.instance() or QApplication([])
    current = ["speakers"]
    sinks = []

    class Device:
        def __init__(self, name):
            self.name = name

        def id(self):
            return QByteArray((self.name or "").encode())

        def isNull(self):
            return self.name is None

        def isFormatSupported(self, fmt):
            return True

    class Devices(QObject):
        audioOutputsChanged = Signal()

        @staticmethod
        def defaultAudioOutput():
            return Device(current[0])

    class Sink(QObject):
        stateChanged = Signal(object)

        def __init__(self, device, fmt, parent):
            super().__init__(parent)
            self.device = device
            self.processed = 0
            self.status = QtAudio.State.StoppedState
            self.start_position = None
            sinks.append(self)

        def setBufferSize(self, size):
            pass

        def setVolume(self, volume):
            pass

        def start(self, buffer):
            self.start_position = buffer.pos()
            self.status = QtAudio.State.ActiveState
            self.stateChanged.emit(self.status)

        def reset(self):
            self.status = QtAudio.State.StoppedState
            self.stateChanged.emit(self.status)

        def state(self):
            return self.status

        def error(self):
            return QtAudio.Error.NoError

        def processedUSecs(self):
            return self.processed

    monkeypatch.setattr(music, "QMediaDevices", Devices)
    monkeypatch.setattr(music, "QAudioSink", Sink)
    player = music.MusicPlayer()
    stopped, failed = [], []
    player.stopped.connect(lambda: stopped.append(True))
    player.failed.connect(lambda: failed.append(True))

    def select(name):
        current[0] = name
        # Qt notifies existing QMediaDevices instances when defaults change.
        for monitor in player.findChildren(Devices):
            monitor.audioOutputsChanged.emit()
        QTest.qWait(10)

    yield SimpleNamespace(player=player, select=select, sinks=sinks,
                          stopped=stopped, failed=failed, app=app, current=current)
    player.stop()
    player.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_replay_uses_headphones_selected_since_previous_play(outputs):
    outputs.player.play()
    QTest.qWait(10)
    assert outputs.sinks[-1].device.name == "speakers"
    outputs.player.stop()
    outputs.select("headphones")
    assert not outputs.player.active
    outputs.player.play()
    QTest.qWait(10)
    assert outputs.sinks[-1].device.name == "headphones"
    assert outputs.player.position_ms == 0
    assert not outputs.failed


def test_active_audio_moves_to_headphones_without_restarting_session(outputs):
    player = outputs.player
    player.play()
    QTest.qWait(10)
    outputs.sinks[-1].processed = 2_250_000
    remaining = player._deadline.remainingTime()
    # The sink can read ahead; resume from processed audio, not buffer.pos().
    player._buffer.seek(300_000)
    outputs.select("headphones")
    assert outputs.sinks[-1].device.name == "headphones"
    assert player.active and not outputs.stopped and not outputs.failed
    assert player.position_ms == 2250
    assert outputs.sinks[-1].start_position == 198_450
    assert 0 < player._deadline.remainingTime() <= remaining
    outputs.sinks[-1].processed = 500_000
    assert player.position_ms == 2750
    outputs.select("speakers")
    assert outputs.sinks[-1].device.name == "speakers"
    assert player.position_ms == 2750
    player._deadline.timeout.emit()
    assert not player.active and outputs.stopped == [True]


def test_unrelated_device_notification_does_not_interrupt_audio(outputs):
    outputs.player.play()
    QTest.qWait(10)
    outputs.select("speakers")
    assert len(outputs.sinks) == 1
    assert outputs.player.active and not outputs.stopped


def test_losing_all_outputs_stops_once_and_allows_manual_replay(outputs):
    outputs.player.play()
    QTest.qWait(10)
    outputs.select(None)
    assert not outputs.player.active
    assert outputs.failed == [True] and outputs.stopped == [True]
    outputs.select("headphones")
    assert not outputs.player.active
    outputs.player.play()
    QTest.qWait(10)
    assert outputs.player.active and outputs.sinks[-1].device.name == "headphones"


def test_device_loss_callback_before_notification_routes_to_new_default(outputs):
    outputs.player.play()
    QTest.qWait(10)
    old = outputs.sinks[-1]
    old.processed = 1_000_000
    outputs.current[0] = "headphones"
    old.status = QtAudio.State.StoppedState
    old.stateChanged.emit(old.status)
    # Two old queued callbacks must not stop the newly created sink.
    old.stateChanged.emit(old.status)
    QTest.qWait(10)
    assert outputs.player.active and not outputs.stopped and not outputs.failed
    assert outputs.sinks[-1].device.name == "headphones"
    assert outputs.player.position_ms == 1000


def test_connecting_headphones_during_startup_keeps_startup_deadline(outputs):
    outputs.player.play()
    outputs.select("headphones")
    assert outputs.player.active and outputs.player.position_ms == 0
    assert outputs.player._deadline.isActive()
    assert not outputs.player._load_timeout.isActive()
    assert not outputs.failed and not outputs.stopped
