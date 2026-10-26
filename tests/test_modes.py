"""Agreed application seam: mode selection, clicks, time and fresh launches."""

import json
from pathlib import Path

import pytest

from sukuna_pet.playback import PetApplication


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


@pytest.mark.parametrize("saved", ["not json", "[]", '{"mode":"unsupported"}', '{"mode":null}', "\ud800"])
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
