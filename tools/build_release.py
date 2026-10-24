"""Build an onedir Windows app, Setup.exe and a self-contained source archive.

Run from the locked build environment; see docs/build.md. No reference media or
installed reference application is accessed. Outputs remain inside dist/.
"""

import argparse
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def run(arguments: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(arguments, cwd=ROOT, env=env, check=True)


def source_archive(destination: Path) -> None:
    """Explicit inclusion keeps local media, venvs and credentials out of delivery."""
    paths = [ROOT / name for name in (
        "README.md", "GLOSSARY.md", "pyproject.toml", "requirements.txt",
        "requirements-dev.txt", "requirements-build.txt", ".gitignore",
    )]
    for directory in ("src", "tests", "tools", "packaging", "docs"):
        paths.extend(path for path in (ROOT / directory).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, Path("sukuna-pet-source") / path.relative_to(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, required=True, help="Inno Setup 6.7.3 ISCC.exe")
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().upper() not in ("AMD64", "X86_64"):
        parser.error("Build on Windows x64 with x64 CPython")
    iscc = args.iscc.resolve(strict=True)
    with (ROOT / "pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["project"]["version"]
    release = ROOT / "dist" / "release"
    release.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "-m", "pip", "check"])
    # Dependency discovery must not collect unrelated DLLs from developer tools
    # on PATH (e.g. Poppler's ICU has a different ABI from Windows' system ICU).
    build_env = dict(os.environ)
    build_env["PATH"] = os.pathsep.join((str(Path(sys.executable).parent),
                                       sys.base_prefix, str(Path(os.environ["SystemRoot"]) / "System32")))
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--distpath", str(ROOT / "dist" / "app"),
         "--workpath", str(ROOT / "build" / "pyinstaller"),
         str(ROOT / "packaging" / "sukuna-pet.spec")], env=build_env)
    bundle = ROOT / "dist" / "app" / "SukunaPet"
    shutil.copyfile(ROOT / "docs" / "user-guide.md", bundle / "使用说明.md")
    # Include upstream license texts next to the replaceable Qt runtime DLLs.
    licenses = bundle / "THIRD-PARTY-LICENSES"
    shutil.copytree(ROOT / "packaging" / "licenses", licenses / "Qt", dirs_exist_ok=True)
    for name in ("PySide6", "PySide6_Essentials", "shiboken6", "pyinstaller"):
        distribution = metadata.distribution(name)
        for item in distribution.files or ():
            source_path = Path(str(distribution.locate_file(item)))
            if "license" in str(item).lower() and source_path.is_file():
                target = licenses / name / Path(str(item))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_path, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise FileNotFoundError("CPython LICENSE.txt is required for redistribution")
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(python_license, licenses / "Python-LICENSE.txt")
    run([str(iscc), f"/DBundleDir={bundle}", f"/DReleaseDir={release}",
         f"/DAppVersion={version}", str(ROOT / "packaging" / "installer.iss")])
    archive = release / f"sukuna-pet-{version}-source.zip"
    source_archive(archive)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() if (ROOT / ".git").exists() else None
    report = {
        "version": version, "python": sys.version, "platform": platform.platform(),
        "source_base_commit": commit,
        "source_snapshot": "working tree; source ZIP is authoritative, not an exact commit export",
        "compiler": "Inno Setup 6.7.3", "compiler_sha256": sha256(iscc.read_bytes()).hexdigest(),
        "packages": sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions()),
        "bundled_files": {p.relative_to(bundle).as_posix(): sha256(p.read_bytes()).hexdigest()
                          for p in sorted(bundle.rglob("*")) if p.is_file()},
    }
    (release / "build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    outputs = [release / "Setup.exe", archive, release / "build-report.json"]
    (release / "SHA256SUMS.txt").write_text("".join(
        f"{sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in outputs), encoding="ascii")
    print(f"Delivery: {release}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
