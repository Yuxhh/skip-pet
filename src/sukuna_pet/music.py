"""Local PCM playback with a sample clock and bounded manual sessions."""

from array import array
from pathlib import Path
import wave

from PySide6.QtCore import QBuffer, QElapsedTimer, QIODevice, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSink, QMediaDevices, QtAudio


SESSION_MS = 15_000
CLIP = Path(__file__).parent / "assets/diamond-cut-diamond.wav"


class MusicPlayer(QObject):
    stopped = Signal()
    failed = Signal()

    def __init__(self, parent: QObject | None = None, *, source: Path = CLIP) -> None:
        super().__init__(parent)
        self._source = source
        self._active = False
        self._clock = QElapsedTimer()
        self._loop_ms = 0.0
        self._buffer = QBuffer(self)
        self._sink: QAudioSink | None = None
        self._format = QAudioFormat()
        self._device_id: bytes | None = None
        self._offset_frames = 0
        self._devices = QMediaDevices(self)
        self._devices.audioOutputsChanged.connect(
            self._output_changed, Qt.ConnectionType.QueuedConnection)
        self._deadline = QTimer(self)
        self._deadline.setSingleShot(True)
        self._deadline.setTimerType(Qt.TimerType.PreciseTimer)
        self._deadline.timeout.connect(self.stop)
        self._load_timeout = QTimer(self)
        self._load_timeout.setSingleShot(True)
        self._load_timeout.setInterval(5000)
        self._load_timeout.timeout.connect(self._error)

    @property
    def active(self) -> bool:
        """Include startup so render ticks cannot queue additional sessions."""
        return self._active

    @property
    def position_ms(self) -> float | None:
        if not self._active or self._sink is None or not self._clock.isValid():
            return None
        if self._clock.elapsed() >= SESSION_MS:
            self.stop()
            return None
        # Hardware-processed PCM time stays smooth across loop boundaries.
        return (self._offset_frames * 1000 / self._format.sampleRate()
                + self._sink.processedUSecs() / 1000) % self._loop_ms

    def play(self) -> None:
        if self._active:
            return
        self._active = True
        self._clock.invalidate()
        try:
            with wave.open(str(self._source), "rb") as source:
                rate, channels = source.getframerate(), source.getnchannels()
                if source.getsampwidth() != 2 or source.getnframes() == 0:
                    raise ValueError("Expected nonempty PCM16 soundtrack")
                pcm = source.readframes(source.getnframes())
            self._loop_ms = len(pcm) * 1000 / (rate * channels * 2)
            total_bytes = round(rate * SESSION_MS / 1000) * channels * 2
            session = array("h")
            session.frombytes((pcm * ((total_bytes + len(pcm) - 1) // len(pcm)))[:total_bytes])
            # Fade the bounded session's end to avoid a hard-cut click.
            fade_frames = min(round(rate * .010), len(session) // channels)
            for frame in range(fade_frames):
                for channel in range(channels):
                    index = len(session) - (fade_frames - frame) * channels + channel
                    session[index] = round(session[index] * (fade_frames - frame - 1) / fade_frames)
            fmt = QAudioFormat()
            fmt.setSampleRate(rate)
            fmt.setChannelCount(channels)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            device = QMediaDevices.defaultAudioOutput()
            if device.isNull() or not device.isFormatSupported(fmt):
                raise ValueError("No compatible audio output")
            self._format = fmt
            self._offset_frames = 0
            self._buffer.setData(session.tobytes())
            self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            self._start_output(device)
        except (OSError, EOFError, wave.Error, ValueError):
            self._error()

    def stop(self) -> None:
        was_active = self._active
        self._active = False
        self._deadline.stop()
        self._load_timeout.stop()
        self._clock.invalidate()
        self._release_output()
        self._buffer.close()
        if was_active:
            self.stopped.emit()

    def _release_output(self) -> None:
        sink, self._sink = self._sink, None
        self._device_id = None
        if sink is not None:
            sink.stateChanged.disconnect(self._state_changed)
            sink.reset()
            sink.deleteLater()

    def _start_output(self, device: QAudioDevice) -> None:
        # QAudioSink binds its device at construction. Never reuse a sink from
        # an earlier session: the default may now be Bluetooth/USB headphones.
        self._release_output()
        self._device_id = bytes(device.id().data())
        self._sink = QAudioSink(device, self._format, self)
        self._sink.setBufferSize(4096)
        self._sink.setVolume(.65)
        self._sink.stateChanged.connect(self._state_changed, Qt.ConnectionType.QueuedConnection)
        self._load_timeout.start()
        self._sink.start(self._buffer)

    @Slot()
    def _output_changed(self) -> None:
        if not self._active or self._sink is None:
            return
        device = QMediaDevices.defaultAudioOutput()
        if device.id().data() == self._device_id:
            return
        if device.isNull() or not device.isFormatSupported(self._format):
            self._error()
            return
        if self._clock.isValid() and self._clock.elapsed() >= SESSION_MS:
            self.stop()
            return
        # Resume at the samples actually heard, not at the buffer's read-ahead
        # position. Preserve the original deadline and beat phase when routing.
        self._offset_frames += (self._sink.processedUSecs()
                                * self._format.sampleRate() // 1_000_000)
        offset_bytes = self._offset_frames * self._format.bytesPerFrame()
        self._release_output()
        if not self._buffer.seek(offset_bytes):
            self._error()
            return
        self._start_output(device)

    @Slot()
    def _state_changed(self) -> None:
        if not self._active or self._sink is None or self.sender() is not self._sink:
            return
        # Device removal can queue an engine error before the device-list
        # notification. Route to the new default before handling that old error.
        if QMediaDevices.defaultAudioOutput().id().data() != self._device_id:
            self._output_changed()
            return
        state = self._sink.state()
        if state == QtAudio.State.ActiveState:
            self._load_timeout.stop()
            if not self._clock.isValid():
                self._clock.start()
                self._deadline.start(SESSION_MS)
        elif state == QtAudio.State.IdleState:
            self.stop()
        elif state == QtAudio.State.StoppedState:
            if self._sink.error() != QtAudio.Error.NoError:
                self._error()
            else:
                self.stop()

    def _error(self) -> None:
        if self._active:
            self.stop()
            self.failed.emit()
