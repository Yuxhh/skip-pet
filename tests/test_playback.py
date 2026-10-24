"""Agreed seam: user clicks + virtual elapsed time -> drawable application view."""

import json
from pathlib import Path

import pytest

from sukuna_pet.playback import PetApplication


def test_first_launch_is_stationary_until_one_click_then_holds() -> None:
    pet = PetApplication()
    initial = pet.view
    pet.advance(60_000)
    assert pet.view == initial
    assert initial.stage == 0
    assert initial.holding
    assert initial.right_eye == (652, 476)  # Anatomical right = screen left.
    assert initial.left_eye == (818, 465)

    pet.click()
    pet.advance(100)
    assert pet.view.right_eye[0] < initial.right_eye[0]
    assert not pet.view.holding
    pet.advance(81)  # Approved first stage is ~181ms at 3x.
    end = pet.view
    assert end.stage == 1
    assert end.holding
    assert end.right_eye == (639, 467)
    assert end.left_eye == (798, 456)
    pet.advance(60_000)
    assert pet.view == end


_TRACES = json.loads(
    (Path(__file__).parent / "fixtures/prototype-traces.json").read_text(encoding="utf-8")
)["traces"]


@pytest.mark.parametrize("trace", _TRACES, ids=[trace["name"] for trace in _TRACES])
def test_user_sequences_match_approved_prototype(trace: dict) -> None:
    pet = PetApplication()
    time = 0
    clicks = trace["clicks_ms"]
    observations = {item["at_ms"]: item for item in trace["observations"]}
    for at_ms in sorted(set(clicks) | observations.keys()):
        pet.advance(at_ms - time)
        time = at_ms
        if at_ms in clicks:
            pet.click()
        if at_ms in observations:
            expected = observations[at_ms]
            view = pet.view
            assert view.stage == expected["stage"]
            assert view.holding == expected["holding"]
            assert view.right_eye == pytest.approx(expected["right_eye"], abs=0.2)
            assert view.left_eye == pytest.approx(expected["left_eye"], abs=0.2)
            assert view.eyelid_closure == pytest.approx(expected["eyelid_closure"], abs=0.001)


def test_clock_chunk_size_does_not_change_blink_or_hold() -> None:
    one_step, small_steps = PetApplication(), PetApplication()
    for pet in (one_step, small_steps):
        pet.click()
        pet.advance(181)
        pet.click()
        pet.advance(153)
        pet.click()
    one_step.advance(10_000)
    for _ in range(10_000):
        small_steps.advance(1)
    assert one_step.view == small_steps.view
    assert one_step.view.stage == 3
    assert one_step.view.holding


def test_stage_two_holds_until_separate_click_blinks_and_jumps_while_closed() -> None:
    pet = PetApplication()
    pet.click()
    pet.advance(181)
    pet.click()
    pet.advance(153)
    stage_two = pet.view
    assert stage_two.stage == 2
    assert stage_two.holding
    assert stage_two.right_eye == (621.15, 469)  # Includes the approved -12px.
    assert stage_two.left_eye == (789, 458)  # No extra correction on this eye.
    pet.advance(10_000)
    assert pet.view == stage_two

    pet.click()
    pet.advance(60)
    assert 0 < pet.view.eyelid_closure < 1
    assert pet.view.right_eye == stage_two.right_eye
    pet.advance(59)
    assert pet.view.right_eye == stage_two.right_eye
    pet.advance(1)
    assert pet.view.eyelid_closure == 1
    assert pet.view.right_eye == (642.25, 483)
    assert pet.view.left_eye == (803, 472)
    pet.advance(60)
    assert 0 < pet.view.eyelid_closure < 1
    pet.advance(60)
    end = pet.view
    assert end.stage == 3
    assert end.holding
    assert end.eyelid_closure == 0
    pet.advance(60_000)
    assert pet.view == end

    pet.click()
    pet.advance(98)
    assert pet.view.stage == 0
    assert pet.view.right_eye == (652, 476)
    assert pet.view.holding
    initial = pet.view
    pet.advance(10_000)
    assert pet.view == initial
