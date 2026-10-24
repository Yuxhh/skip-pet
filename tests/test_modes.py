"""Agreed application seam: mode selection, clicks, time and fresh launches."""

import json
from pathlib import Path

import pytest

from sukuna_pet.playback import PetApplication


def test_continuous_mode_moves_across_cycles_without_resetting_or_holding() -> None:
    pet = PetApplication()
    pet.select_mode("always")
    assert pet.mode == "always"
    pet.advance(100)
    assert pet.view.right_eye != (652, 476)
    assert not pet.view.holding
    for _ in range(30):
        before = pet.view
        pet.advance(100)
        assert pet.view != before
        assert not pet.view.holding
    assert pet.mode == "always"


_TRACES = json.loads(
    (Path(__file__).parent / "fixtures/prototype-mode-traces.json").read_text(encoding="utf-8")
)["traces"]


@pytest.mark.parametrize("trace", _TRACES, ids=[trace["name"] for trace in _TRACES])
def test_continuous_clicks_match_the_approved_prototype(trace: dict) -> None:
    pet = PetApplication()
    pet.select_mode("always")
    time = 0
    observations = {item["at_ms"]: item for item in trace["observations"]}
    for at_ms in sorted(set(trace["clicks_ms"]) | observations.keys()):
        pet.advance(at_ms - time)
        time = at_ms
        if at_ms in trace["clicks_ms"]:
            pet.click()
        assert pet.mode == "always"
        if at_ms in observations:
            expected = observations[at_ms]
            assert pet.view.stage == expected["stage"]
            assert not pet.view.holding
            assert pet.view.right_eye == pytest.approx(expected["right_eye"], abs=0.5)
            assert pet.view.left_eye == pytest.approx(expected["left_eye"], abs=0.5)
            assert pet.view.eyelid_closure == pytest.approx(expected["eyelid_closure"], abs=0.03)


@pytest.mark.parametrize("elapsed, stage, right_eye", [
    (100, 1, (639, 467)),
    (250, 2, (621.15, 469)),
    (610, 1, (639, 467)),
    # Continuous playback has resumed during the opening half of the blink.
    (490, 0, (652, 476)),
])
def test_switch_to_click_finishes_only_the_current_stage(
    elapsed: int, stage: int, right_eye: tuple[float, float],
) -> None:
    pet = PetApplication()
    pet.select_mode("always")
    pet.advance(elapsed)
    before = pet.view
    pet.select_mode("click")
    assert pet.view.right_eye == before.right_eye
    assert not pet.view.holding
    pet.advance(1000)
    end = pet.view
    assert end.stage == stage
    assert end.holding
    assert end.right_eye == pytest.approx(right_eye)
    assert end.eyelid_closure == 0
    pet.advance(60_000)
    assert pet.view == end


def test_switch_during_blink_closing_preserves_the_whole_blink_and_holds_stage_three() -> None:
    pet = PetApplication()
    pet.select_mode("always")
    pet.advance(350)  # Blink started at 333 1/3ms, closure is in progress.
    before = pet.view
    pet.select_mode("click")
    assert pet.view == before
    pet.advance(100)
    assert pet.view.right_eye == before.right_eye
    assert pet.view.eyelid_closure > before.eyelid_closure
    pet.advance(4)
    assert pet.view.right_eye == (642.25, 483)
    assert pet.view.eyelid_closure > 0.99
    pet.advance(60)
    assert 0 < pet.view.eyelid_closure < 1
    assert not pet.view.holding
    pet.advance(60)
    assert pet.view.holding
    assert pet.view.stage == 3
    assert pet.view.eyelid_closure == 0
    end = pet.view
    pet.advance(60_000)
    assert pet.view == end


def test_switch_during_opening_finishes_the_blink_even_after_eye_motion_has_stopped() -> None:
    pet = PetApplication()
    pet.select_mode("always")
    pet.advance(490)
    closure = pet.view.eyelid_closure
    pet.select_mode("click")
    assert pet.view.eyelid_closure == closure
    pet.advance(61)
    assert pet.view.right_eye == (652, 476)
    assert 0 < pet.view.eyelid_closure < closure
    assert not pet.view.holding
    pet.advance(23)
    assert pet.view.holding
    assert pet.view.eyelid_closure == 0


def test_mode_selection_is_restored_by_a_fresh_application(tmp_path: Path) -> None:
    settings = tmp_path / "config" / "mode.json"
    first = PetApplication(settings_path=settings)
    assert first.mode == "click"
    assert first.view.holding
    first.select_mode("always")
    second = PetApplication(settings_path=settings)
    assert second.mode == "always"
    second.advance(100)
    assert not second.view.holding
    assert second.view.right_eye != (652, 476)
    second.select_mode("click")
    third = PetApplication(settings_path=settings)
    assert third.mode == "click"
    assert third.view.holding
    assert third.view.right_eye == (652, 476)
    # Position, phase and scale are outside this ticket's settings contract.
    assert json.loads(settings.read_text(encoding="utf-8")) == {"mode": "click"}


@pytest.mark.parametrize("saved", ["not json", "[]", '{"mode":"task"}', '{"mode":null}', "\ud800"])
def test_invalid_settings_fall_back_to_click_mode(tmp_path: Path, saved: str) -> None:
    settings = tmp_path / "mode.json"
    settings.write_bytes(saved.encode("utf-8", errors="surrogatepass"))
    pet = PetApplication(settings_path=settings)
    assert pet.mode == "click"
    initial = pet.view
    pet.advance(1000)
    assert pet.view == initial


def test_failed_save_leaves_the_previous_mode_in_effect(tmp_path: Path) -> None:
    settings = tmp_path / "mode.json"
    pet = PetApplication(settings_path=settings)
    settings.mkdir()  # A directory cannot be replaced by a settings file.
    with pytest.raises(OSError):
        pet.select_mode("always")
    assert pet.mode == "click"
    assert pet.view.holding


def test_same_mode_does_not_extend_a_stage_and_continuous_resumes_in_place() -> None:
    pet = PetApplication()
    pet.select_mode("always")
    pet.advance(250)
    pet.select_mode("click")
    pet.advance(50)
    pet.select_mode("click")
    pet.advance(1000)
    assert pet.view.stage == 2
    assert pet.view.holding
    before = pet.view
    pet.select_mode("always")
    assert pet.view.right_eye == before.right_eye
    pet.advance(120)
    assert pet.view.eyelid_closure == 1
    assert pet.view.right_eye == (642.25, 483)


def test_continuous_timing_is_independent_of_frame_sizes_even_with_clicks() -> None:
    large, small = PetApplication(), PetApplication()
    for pet in (large, small):
        pet.select_mode("always")
    for interval in (350, 30, 180, 1000, 10_000):
        large.advance(interval)
        for _ in range(interval):
            small.advance(1)
        assert large.view.stage == small.view.stage
        assert large.view.right_eye == pytest.approx(small.view.right_eye, abs=1e-8)
        assert large.view.eyelid_closure == pytest.approx(small.view.eyelid_closure, abs=1e-8)
        large.click()
        small.click()
