"""Persist playback mode and display size independently of the desktop UI."""

import json
import os
from pathlib import Path
import tempfile
from dataclasses import dataclass
from typing import Literal


Mode = Literal["click", "always", "task", "music"]
MODE_LABELS: tuple[tuple[Mode, str], ...] = (
    ("click", "点击跳动"), ("always", "持续跳动"), ("task", "任务联动"), ("music", "音乐跳动"),
)
DISPLAY_SIZES = (188, 271, 320)
DEFAULT_SIZE = 320


@dataclass(frozen=True)
class BridgeSettings:
    enabled: bool = False
    profiles: tuple[Path, ...] = ()


def load_bridge(path: Path) -> BridgeSettings:
    value = _load_settings(path).get("dsh_bridge")
    if not isinstance(value, dict):
        return BridgeSettings()
    profiles = value.get("profiles", [])
    if not isinstance(profiles, list) or not all(isinstance(p, str) and p for p in profiles):
        return BridgeSettings()
    return BridgeSettings(value.get("enabled") is True, tuple(Path(p) for p in profiles))


def save_bridge(path: Path, enabled: bool, profiles: tuple[Path, ...]) -> None:
    existing = _load_settings(path).get("dsh_bridge")
    value = dict(existing) if isinstance(existing, dict) else {}
    value.update(enabled=enabled, profiles=[str(p) for p in profiles])
    _save_setting(path, "dsh_bridge", value)


def _load_settings(path: Path) -> dict[str, object]:
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}
    return saved if isinstance(saved, dict) else {}


def load_mode(path: Path) -> Mode:
    value = _load_settings(path).get("mode")
    if value == "music":
        return "music"
    if value in ("always", "task"):
        return "always" if value == "always" else "task"
    return "click"


def save_mode(path: Path, mode: Mode) -> None:
    _save_setting(path, "mode", mode)


def load_size(path: Path) -> int:
    size = _load_settings(path).get("size")
    if type(size) is not int:
        return DEFAULT_SIZE
    # Keep previous medium/large preferences usable after reducing the presets.
    size = {461: 271, 544: 320}.get(size, size)
    return size if size in DISPLAY_SIZES else DEFAULT_SIZE


def save_size(path: Path, size: int) -> None:
    if type(size) is not int or size not in DISPLAY_SIZES:
        raise ValueError("Unsupported display size")
    _save_setting(path, "size", size)


def _save_setting(path: Path, key: str, value: object) -> None:
    saved = _load_settings(path)
    saved[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(saved, stream)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
