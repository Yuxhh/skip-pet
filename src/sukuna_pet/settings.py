"""Persist playback mode and display size independently of the desktop UI."""

import json
import os
from pathlib import Path
import tempfile
from typing import Literal


Mode = Literal["click", "always", "task"]
DISPLAY_SIZES = (188, 271, 320)
DEFAULT_SIZE = 320


def _load_settings(path: Path) -> dict[str, object]:
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}
    return saved if isinstance(saved, dict) else {}


def load_mode(path: Path) -> Mode:
    value = _load_settings(path).get("mode")
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
