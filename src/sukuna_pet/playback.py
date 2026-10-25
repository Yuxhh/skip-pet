"""Application interaction boundary, independent of Qt and wall-clock time.

Eye rules originate in 9eef9e2; independent head progress follows frozen V5
32c9f985. Rendering never controls playback or blink timing.
All coordinates are in the original 1419 x 1108 redraw, before display scaling.
"""

from dataclasses import dataclass
import math
from pathlib import Path

from .settings import Mode, load_mode, save_mode


_BOUNDS = (0, 13, 24, 34)
_KEYS = (
    (0, 0, 0), (8, -10, -5), (13, -20, -9), (20, -28, -8),
    (24, -29, -7), (27, -27, -6), (31, -20, 3), (34, -15, 7),
    (38, -5, 6), (41, 0, 0),
)


@dataclass(frozen=True)
class PetView:
    """Source-space eyes, uniform head pose, eyelid closure and visible status."""

    stage: int
    holding: bool
    right_eye: tuple[float, float]
    left_eye: tuple[float, float]
    eyelid_closure: float = 0
    head_phase: float = 0
    head_angle: float = 0
    head_scale: float = 1


def _head_pose(position: float) -> tuple[float, float]:
    poses = ((0.0, 1.0), (-6.44, 1.08), (1.17, 1.025), (-9.0, 1.065), (0.0, 1.0))
    phase = position % 41
    bounds = (*_BOUNDS, 41)
    i = next(i for i in range(4) if phase < bounds[i + 1])
    u = (phase - bounds[i]) / (bounds[i + 1] - bounds[i])
    t = u * u * (3 - 2 * u)
    return (poses[i][0] + (poses[i + 1][0] - poses[i][0]) * t,
            poses[i][1] + (poses[i + 1][1] - poses[i][1]) * t)


def _eyes(position: float) -> tuple[tuple[float, float], tuple[float, float]]:
    phase = position % 41
    for a, b in zip(_KEYS, _KEYS[1:]):
        if a[0] <= phase <= b[0]:
            fraction = (phase - a[0]) / (b[0] - a[0])
            dx = a[1] + (b[1] - a[1]) * fraction
            dy = a[2] + (b[2] - a[2]) * fraction
            break
    correction = 0.0
    if 13 <= phase <= 24:
        correction = -12 * (phase - 13) / 11
    elif 24 < phase < 34:
        correction = -12 * (34 - phase) / 10
    return (652 + dx * 0.65 + correction, 476 + dy), (818 + dx, 465 + dy)


class PetApplication:
    """Accept clicks and elapsed milliseconds; expose the complete drawable view."""

    def __init__(self, *, settings_path: Path | None = None) -> None:
        self._settings_path = settings_path
        self._mode: Mode = load_mode(settings_path) if settings_path is not None else "click"
        self._position = 0.0
        self._target = 0.0
        self._stage = 0
        self._moving = False
        self._blink_age: float | None = None
        self._blink_destination: float | None = None
        self._head_position = 0.0
        self._head_from = 0.0
        self._head_to = 0.0
        self._head_age = 0.0
        self._head_duration = 0.0
        self._pointer_start: tuple[int, int] | None = None
        self._window_start = (0, 0)
        self._drag_distance = 0
        self._dragging = False

    def pointer_press(
        self, position: tuple[int, int], window_position: tuple[int, int], *, drag_distance: int,
    ) -> None:
        """Begin a left gesture in Qt's device-independent global coordinates."""
        self._pointer_start = position
        self._window_start = window_position
        self._drag_distance = drag_distance
        self._dragging = False

    def pointer_move(self, position: tuple[int, int]) -> tuple[int, int] | None:
        """Return a window position once the platform drag distance is reached."""
        if self._pointer_start is None:
            return None
        dx = position[0] - self._pointer_start[0]
        dy = position[1] - self._pointer_start[1]
        if abs(dx) + abs(dy) >= self._drag_distance:
            self._dragging = True
        if self._dragging:
            return self._window_start[0] + dx, self._window_start[1] + dy
        return None

    def pointer_release(self, position: tuple[int, int]) -> tuple[int, int] | None:
        """Finish even if the OS coalesced moves; a drag never becomes a click."""
        if self._pointer_start is None:
            return None
        destination = self.pointer_move(position)
        if not self._dragging:
            self.click()
        self.cancel_pointer()
        return destination

    def cancel_pointer(self) -> None:
        """An interrupted mouse grab must not leave an unfinished click."""
        self._pointer_start = None
        self._dragging = False

    @property
    def mode(self) -> Mode:
        return self._mode

    def select_mode(self, mode: Mode) -> None:
        if mode not in ("click", "always"):
            raise ValueError("Unknown playback mode")
        if mode == self._mode:
            return
        if self._settings_path is not None:
            save_mode(self._settings_path, mode)
        if mode == "click" and self._blink_destination is None:
            phase = self._position % 41
            stop_at = next(bound for bound in (13, 24, 34, 41) if bound > phase)
            self._target = self._position + stop_at - phase
            self._stage = (13, 24, 34, 41).index(stop_at) + 1
            self._stage %= 4
            self._moving = True
            self._follow_head(self._target, (self._target - self._head_position) / 0.072)
        self._mode = mode

    @property
    def view(self) -> PetView:
        right, left = _eyes(self._position)
        closure = 0.0
        if self._blink_age is not None:
            closure = 0.5 - 0.5 * math.cos(2 * math.pi * self._blink_age / 240)
        angle, scale = _head_pose(self._head_position)
        return PetView(
            self._stage, self._mode == "click" and not self._moving
            and self._blink_age is None and self._head_age >= self._head_duration,
            right, left, closure,
            self._head_position % 41, angle, scale,
        )

    def click(self) -> None:
        # The prototype commits a pending closed-eye jump before retargeting.
        # Keep the current blink envelope even when a new target replaces it.
        if self._blink_destination is not None:
            self._position = self._blink_destination
            self._moving = False
            self._blink_destination = None
        if self._mode == "always":
            self._stage = self._phase_at_position()
        self._stage = (self._stage + 1) % 4
        distance = (_BOUNDS[self._stage] - self._position % 41) % 41
        if distance < 0.0001:
            distance = 41
        self._target = self._position + distance
        self._moving = True
        self._follow_head(self._target, (self._target - self._head_position) / 0.072)
        if self._stage == 3:
            self._blink_age = 0.0
            self._blink_destination = self._target
            self._moving = False
            self._follow_head(self._target, 240)

    def _follow_head(self, target: float, duration: float) -> None:
        self._head_from = self._head_position
        self._head_to = target
        self._head_age = 0
        self._head_duration = max(duration, 1)

    def _advance_head(self, elapsed_ms: float) -> None:
        if self._head_age < self._head_duration:
            self._head_age = min(self._head_duration, self._head_age + elapsed_ms)
            u = self._head_age / self._head_duration
            self._head_position = self._head_from + (self._head_to - self._head_from) * u

    def advance(self, elapsed_ms: float) -> None:
        if not math.isfinite(elapsed_ms) or elapsed_ms < 0:
            raise ValueError("elapsed_ms must be finite and nonnegative")
        if self._mode == "always":
            self._advance_continuous(elapsed_ms)
            return
        self._advance_head(elapsed_ms)
        if self._blink_destination is not None:
            assert self._blink_age is not None
            closing_ms = min(elapsed_ms, max(0, 120 - self._blink_age))
            self._blink_age += closing_ms
            elapsed_ms -= closing_ms
            if self._blink_age >= 120:
                self._position = self._blink_destination
                self._target = self._position
                self._blink_destination = None
        if self._moving:
            self._position = min(self._target, self._position + elapsed_ms * 0.072)
            if self._position >= self._target - 0.00001:
                self._position = self._target
                self._moving = False
        if self._blink_age is not None:
            self._blink_age += elapsed_ms
            if self._blink_age >= 240:
                self._blink_age = None

    def _advance_continuous(self, elapsed_ms: float) -> None:
        # Consume time at event boundaries, so a delayed Qt frame cannot skip a
        # blink or a cycle. The prototype resumes motion during the opening lid.
        while elapsed_ms > 0:
            if self._blink_destination is not None:
                assert self._blink_age is not None
                step = min(elapsed_ms, 120 - self._blink_age)
                self._blink_age += step
                self._advance_head(step)
                if self._blink_age >= 120:
                    self._position = self._blink_destination
                    self._blink_destination = None
                    self._moving = False
            else:
                next_blink = (math.floor(self._position / 41) * 41) + 24
                if next_blink < self._position:
                    next_blink += 41
                head_remaining = max(0, self._head_duration - self._head_age)
                step = min(elapsed_ms, (next_blink - self._position) / 0.072,
                           head_remaining if head_remaining else math.inf)
                self._position += step * 0.072
                if head_remaining:
                    self._advance_head(step)
                else:
                    self._head_position += max(0, min(self._position - self._head_position, step * .144))
                if self._blink_age is not None:
                    self._blink_age += step
                    if self._blink_age >= 240:
                        self._blink_age = None
                if self._position >= next_blink - 0.00000001:
                    self._position = next_blink
                    self._stage = 3
                    self._blink_age = 0
                    self._blink_destination = next_blink + 10
                    self._follow_head(next_blink + 10, 240)
            elapsed_ms -= step
        if self._blink_age is None:
            self._stage = self._phase_at_position()

    def _phase_at_position(self) -> int:
        phase = self._position % 41
        return next((i for i, bound in enumerate((13, 24, 34)) if phase < bound), 3)
