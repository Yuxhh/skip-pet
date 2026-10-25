"""Approved application seam against the executed frozen native scheduler."""

import json
import math
from pathlib import Path

import pytest

from sukuna_pet.playback import PetApplication


TRACES = json.loads((Path(__file__).parent / "fixtures/v5-mode-traces.json").read_text())["traces"]


@pytest.mark.parametrize("trace", TRACES, ids=lambda trace: trace["name"])
def test_frames_match_frozen_native_v5(trace: dict) -> None:
    pet = PetApplication()
    pet.select_mode("always")
    for expected in trace["observations"]:
        if expected["frame"]:
            # The native driver caps real time. The application consumes the
            # same virtual frame, without independently dropping elapsed time.
            pet.advance(min(150, trace["frame_ms"]))
        event = trace["events"].get(str(expected["frame"]))
        if event == "click":
            pet.click()
        elif event:
            pet.select_mode("click" if event == "click_mode" else "always")
        view = pet.view
        assert pet.mode == expected["mode"]
        assert view.stage == expected["stage"], expected["frame"]
        assert view.holding == expected["holding"]
        for key in ("right_eye", "left_eye", "head_phase", "eyelid_closure", "bounce_scale"):
            assert getattr(view, key) == pytest.approx(expected[key], abs=1e-8), (expected["frame"], key)
        a, b = expected["head_matrix"][:2]
        assert view.head_angle == pytest.approx(math.degrees(math.atan2(b, a)), abs=1e-8)
        assert view.head_scale == pytest.approx(math.hypot(a, b), abs=1e-8)


def test_virtual_frame_is_not_capped_or_replayed_as_queued_actions() -> None:
    pet = PetApplication()
    pet.select_mode("always")
    # A virtual frame consumes all elapsed time, scheduling once at frame end.
    pet.advance(60_000)
    assert pet.view.stage == 2
    assert pet.view.head_phase == 13
    assert pet.view.right_eye == (639, 467)
    assert pet.view.bounce_scale == (1, 1)
    pet.select_mode("click")
    pet.advance(60_000)
    assert pet.view.stage == 2 and pet.view.holding
    assert pet.view.head_phase == 24
    end = pet.view
    pet.advance(60_000)
    assert pet.view == end


def test_same_mode_selection_does_not_restart_motion_or_wait() -> None:
    pet, control = PetApplication(), PetApplication()
    for model in (pet, control):
        model.select_mode("always")
    for elapsed in (100, 120, 100, 100, 150, 100):
        pet.select_mode("always")
        pet.advance(elapsed)
        control.advance(elapsed)
        assert pet.view == control.view
