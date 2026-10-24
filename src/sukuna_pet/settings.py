"""Persist only the selected playback mode, independently of the desktop UI."""

import json
import os
from pathlib import Path
import tempfile
from typing import Literal


Mode = Literal["click", "always"]


def load_mode(path: Path) -> Mode:
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return "click"
    if isinstance(saved, dict) and saved.get("mode") == "always":
        return "always"
    return "click"


def save_mode(path: Path, mode: Mode) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump({"mode": mode}, stream)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
