"""Click bounce through the already agreed application input/view seam."""

import pytest

from sukuna_pet.playback import PetApplication


def test_click_bounce_peaks_at_110ms_and_recovers_without_resetting_head_or_eyes() -> None:
    pet = PetApplication()
    assert pet.view.bounce_scale == (1, 1)
    pet.click()
    assert pet.view.bounce_scale == (1, 1)
    pet.advance(110)
    assert pet.view.bounce_scale == pytest.approx((1.1, .85))
    assert 0 < pet.view.head_phase < 13
    pet.advance(71)
    # Head/eyes have arrived; bounce is independently still recovering.
    assert pet.view.holding and pet.view.stage == 1
    assert pet.view.bounce_scale[0] > 1
    eyes, phase = (pet.view.right_eye, pet.view.left_eye), pet.view.head_phase
    pet.advance(39)
    assert pet.view.bounce_scale == (1, 1)
    assert (pet.view.right_eye, pet.view.left_eye) == eyes
    assert pet.view.head_phase == phase == 13
    held = pet.view
    pet.advance(60_000)
    assert pet.view == held


def test_each_rapid_click_restarts_only_the_bounce_and_keeps_current_head_progress() -> None:
    pet = PetApplication()
    for _ in range(5):
        phase = pet.view.head_phase
        pet.click()
        assert pet.view.head_phase == phase
        assert pet.view.bounce_scale == (1, 1)
        pet.advance(45)
    pet.advance(65)
    assert pet.view.bounce_scale == pytest.approx((1.1, .85))
    pet.advance(110)
    assert pet.view.bounce_scale == (1, 1)
    pet.advance(2000)
    assert pet.view.stage == 1 and pet.view.holding


@pytest.mark.parametrize("gesture", ["drag", "return", "coalesced", "cancel"])
def test_gestures_during_combined_motion_never_retarget_or_restart_bounce(gesture: str) -> None:
    pet, control = PetApplication(), PetApplication()
    for model in (pet, control):
        model.click()
        model.advance(55)
    pet.pointer_press((100, 100), (400, 300), drag_distance=10)
    if gesture in ("drag", "return"):
        assert pet.pointer_move((110, 100)) == (410, 300)
    elif gesture == "cancel":
        pet.cancel_pointer()
    pet.advance(55)
    control.advance(55)
    pet.pointer_release((100, 100) if gesture in ("return", "cancel") else (110, 100))
    assert pet.view == control.view
    pet.advance(110)
    control.advance(110)
    assert pet.view == control.view
    assert pet.view.bounce_scale == (1, 1)
