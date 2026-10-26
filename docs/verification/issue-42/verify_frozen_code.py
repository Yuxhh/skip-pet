"""Verify our frozen Python modules against source with the locked build Python.

Usage: python docs/verification/issue-42/verify_frozen_code.py APP_DIR --output FILE
Requires the pinned PyInstaller build dependency; does not launch the app.
"""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_root = Path(__file__).resolve().parents[3] / "src"
    executable = args.app_dir / "SukunaPet.exe"
    archive = CArchiveReader(str(executable)).open_embedded_archive("PYZ.pyz")
    modules = {}
    for name in sorted(archive.toc):
        if name != "sukuna_pet" and not name.startswith("sukuna_pet."):
            continue
        relative = Path(*name.split("."))
        source = source_root / (relative / "__init__.py" if name == "sukuna_pet"
                                else relative.with_suffix(".py"))
        data = source.read_bytes()
        code = archive.extract(name)
        matches = code == compile(data, code.co_filename, "exec", dont_inherit=True, optimize=0)
        if not matches:
            raise RuntimeError(f"Frozen code differs from source: {name}")
        modules[name] = {"source_sha256": sha256(data).hexdigest(), "code_matches": True}
    if not modules:
        raise RuntimeError("No application modules in frozen archive")
    args.output.write_text(json.dumps({
        "at": datetime.now().astimezone().isoformat(),
        "evidence": "Static comparison of frozen code objects with current source; not runtime QA",
        "executable_sha256": sha256(executable.read_bytes()).hexdigest(),
        "modules": modules,
    }, indent=2), encoding="utf-8")
    print(f"{len(modules)} frozen application modules match current source")


if __name__ == "__main__":
    main()
