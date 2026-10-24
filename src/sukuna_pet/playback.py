"""Application interaction boundary, independent of Qt and wall-clock time.

Geometry and forward-target rules originate in the approved prototype 9eef9e2.
All coordinates are in the original 1419 x 1108 redraw, before display scaling.
"""

from dataclasses import dataclass
import math


_BOUNDS = (0, 13, 24, 34)
_KEYS = (
    (0, 0, 0), (8, -10, -5), (13, -20, -9), (20, -28, -8),
    (24, -29, -7), (27, -27, -6), (31, -20, 3), (34, -15, 7),
    (38, -5, 6), (41, 0, 0),
)


@dataclass(frozen=True)
class PetView:
    """Drawable eye centres, eyelid closure (0..1), and user-visible status."""

    stage: int
    holding: bool
    right_eye: tuple[float, float]
    left_eye: tuple[float, float]
    eyelid_closure: float = 0


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

    def __init__(self) -> None:
        self._position = 0.0
        self._target = 0.0
        self._stage = 0
        self._moving = False
        self._blink_age: float | None = None
        self._blink_destination: float | None = None

    @property
    def view(self) -> PetView:
        right, left = _eyes(self._position)
        closure = 0.0
        if self._blink_age is not None:
            closure = 0.5 - 0.5 * math.cos(2 * math.pi * self._blink_age / 240)
        return PetView(
            self._stage, not self._moving and self._blink_age is None,
            right, left, closure,
        )

    def click(self) -> None:
        # The prototype commits a pending closed-eye jump before retargeting.
        # Keep the current blink envelope even when a new target replaces it.
        if self._blink_destination is not None:
            self._position = self._blink_destination
            self._moving = False
            self._blink_destination = None
        self._stage = (self._stage + 1) % 4
        distance = (_BOUNDS[self._stage] - self._position % 41) % 41
        if distance < 0.0001:
            distance = 41
        self._target = self._position + distance
        self._moving = True
        if self._stage == 3:
            self._blink_age = 0.0
            self._blink_destination = self._target
            self._moving = False

    def advance(self, elapsed_ms: float) -> None:
        if not math.isfinite(elapsed_ms) or elapsed_ms < 0:
            raise ValueError("elapsed_ms must be finite and nonnegative")
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
