"""Approved application input/view seam; oracle is executed frozen V5 JS."""

import json
import math
from pathlib import Path

import pytest

from sukuna_pet.playback import PetApplication


def test_head_and_eyes_advance_together_and_hold_the_approved_stage() -> None:
    pet = PetApplication()
    initial = pet.view
    assert initial.head_angle == 0
    assert initial.head_scale == 1
    pet.advance(60_000)
    assert pet.view == initial
    pet.click()
    pet.advance(100)
    assert -6.44 < pet.view.head_angle < 0
    assert 1 < pet.view.head_scale < 1.08
    pet.advance(81)
    assert pet.view.head_angle == pytest.approx(-6.44)
    assert pet.view.head_scale == pytest.approx(1.08)
    assert pet.view.holding
    pet.advance(39)  # Independent whole-character bounce finishes at 220ms.
    end = pet.view
    pet.advance(60_000)
    assert pet.view == end


_TRACES = json.loads(
    (Path(__file__).parent / "fixtures/v5-traces.json").read_text(encoding="utf-8")
)["traces"]


@pytest.mark.parametrize("trace", _TRACES, ids=[trace["name"] for trace in _TRACES])
def test_head_progress_blink_and_hold_match_executed_frozen_v5(trace: dict) -> None:
    pet = PetApplication()
    time = 0
    observations = {sample["at_ms"]: sample for sample in trace["observations"]}
    for at in sorted(set(trace["clicks_ms"]) | observations.keys()):
        pet.advance(at - time)
        time = at
        if at in trace["clicks_ms"]:
            before = pet.view
            pet.click()
            assert pet.view.head_phase == before.head_phase
        if at in observations:
            expected = observations[at]
            view = pet.view
            assert view.stage == expected["stage"]
            assert view.holding == expected["holding"]
            assert view.head_phase == pytest.approx(expected["head_phase"], abs=1e-8)
            a, b = expected["head_matrix"][:2]
            assert view.head_angle == pytest.approx(math.degrees(math.atan2(b, a)), abs=1e-8)
            assert view.head_scale == pytest.approx(math.hypot(a, b), abs=1e-8)
            assert view.eyelid_closure == pytest.approx(expected["eyelid_closure"], abs=1e-8)
            assert view.right_eye == pytest.approx(expected["right_eye"], abs=1e-8)
            assert view.left_eye == pytest.approx(expected["left_eye"], abs=1e-8)
            assert view.bounce_scale == pytest.approx(expected["bounce_scale"], abs=1e-8)
