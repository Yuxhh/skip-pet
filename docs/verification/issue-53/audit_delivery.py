"""Audit the delivered source, report, checksums, licenses and installed files."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("installed", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    release, installed = args.release, args.installed
    for line in (release / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        assert sha256((release / name).read_bytes()).hexdigest() == expected
    report = json.loads((release / "build-report.json").read_text(encoding="utf-8"))
    for name, expected in report["bundled_files"].items():
        assert sha256((installed / name).read_bytes()).hexdigest() == expected, name
    modules = report["application_modules_sha256"]
    with ZipFile(release / "sukuna-pet-0.4.0-source.zip") as archive:
        names = archive.namelist()
        for name in names:
            assert not any(part in name.split("/") for part in
                           (".scratch", ".git", ".venv", "references", ".env", "mode.json"))
            assert "/chat/sessions/" not in name
            if name.endswith((".py", ".json", ".md", ".txt", ".toml", ".yml", ".js")):
                assert not re.search(rb"sk-[A-Za-z0-9]{24,}", archive.read(name)), name
        for module, expected in modules.items():
            relative = module.replace(".", "/")
            relative += "/__init__.py" if module == "sukuna_pet" else ".py"
            data = archive.read("sukuna-pet-source/src/" + relative)
            assert sha256(data).hexdigest() == expected, module
        license_text = archive.read("sukuna-pet-source/packaging/licenses/dsh-pet-MIT.txt")
        assert (installed / "THIRD-PARTY-LICENSES/dsh-pet-MIT.txt").read_bytes() == license_text
        assert b"Copyright (c) 2026 Merzlin" in license_text
    assert any(name.endswith("_ssl.pyd") for name in report["bundled_files"])
    args.output.write_text(json.dumps({
        "version": report["version"], "prompt_version": report["prompt_version"],
        "setup_sha256": sha256((release / "Setup.exe").read_bytes()).hexdigest(),
        "manifest_verified": True, "installed_files_verified": len(report["bundled_files"]),
        "source_files": len(names), "source_runtime_modules_verified": len(modules),
        "dsh_mit_text_matches": True, "ssl_extension_bundled": True,
        "source_runtime_data_and_key_pattern_scan": "no forbidden paths or key patterns found",
        "scan_limit": "pattern/path audit, not a proof of absence of every possible secret",
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
