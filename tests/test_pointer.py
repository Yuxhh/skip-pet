"""Agreed application input seam: pointer gestures and observable playback."""

from sukuna_pet.playback import PetApplication
import pytest


def test_drag_moves_window_without_advancing_and_next_click_still_works() -> None:
    pet = PetApplication()
    initial = pet.view
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    assert pet.pointer_move((106, 103)) is None
    assert pet.pointer_move((120, 110)) == (420, 310)
    assert pet.pointer_release((125, 115)) == (425, 315)
    pet.advance(1000)
    assert pet.view == initial
    pet.pointer_press((125, 115), (425, 315), drag_distance=10)
    assert pet.pointer_release((125, 115)) is None
    pet.advance(1000)
    assert pet.view.stage == 1
    assert pet.view.holding


@pytest.mark.parametrize("distance", [4, 10, 20])
def test_platform_threshold_and_return_to_start_still_suppress_drag_click(distance: int) -> None:
    pet = PetApplication()
    pet.pointer_press((-100, 100), (-400, 300), drag_distance=distance)
    assert pet.pointer_move((-100 + distance, 100)) == (-400 + distance, 300)
    assert pet.pointer_release((-100, 100)) == (-400, 300)
    pet.advance(1000)
    assert pet.view.stage == 0
    assert pet.view.holding


def test_release_beyond_threshold_without_move_event_is_a_drag() -> None:
    pet = PetApplication()
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    assert pet.pointer_release((110, 100)) == (410, 300)
    pet.advance(1000)
    assert pet.view.stage == 0
    assert pet.view.holding


def test_small_pointer_jitter_clicks_once_and_orphan_releases_do_nothing() -> None:
    pet = PetApplication()
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    assert pet.pointer_release((104, 103)) is None
    pet.pointer_release((104, 103))
    pet.advance(1000)
    assert pet.view.stage == 1
    assert pet.view.holding


def test_cancelled_gesture_does_not_click_or_affect_next_gesture() -> None:
    pet = PetApplication()
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    pet.cancel_pointer()
    assert pet.pointer_release((100, 100)) is None
    pet.advance(1000)
    assert pet.view.stage == 0
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    pet.pointer_release((100, 100))
    pet.advance(1000)
    assert pet.view.stage == 1


def test_drag_during_stage_motion_does_not_retarget_playback() -> None:
    pet = PetApplication()
    pet.click()
    pet.advance(50)
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    pet.pointer_move((150, 100))
    pet.advance(40)
    pet.pointer_release((150, 100))
    pet.advance(1000)
    assert pet.view.stage == 1
    assert pet.view.holding
