"""Build an onedir Windows app, Setup.exe and a self-contained source archive.

Run from the locked build environment; see docs/build.md. No reference media or
installed reference application is accessed. Outputs default to dist/.
"""

import argparse
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def check_inputs() -> dict[str, str]:
    """Fail before freezing if the declared toolchain or frozen layers drift."""
    if platform.python_version() != "3.14.4":
        raise RuntimeError("Release builds require x64 CPython 3.14.4")
    locks: dict[str, str] = {}
    for name in ("requirements.txt", "requirements-dev.txt", "requirements-build.txt"):
        path = ROOT / name
        locks[name] = sha256(path.read_bytes()).hexdigest()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-r ")):
                continue
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", line)
            if match is None:
                raise ValueError(f"Unpinned build requirement: {line}")
            package, expected = match.groups()
            actual = metadata.version(package)
            if actual != expected:
                raise RuntimeError(f"{package}: expected {expected}, installed {actual}")
    check_assets(ROOT / "src" / "sukuna_pet" / "assets")
    return locks


def check_assets(directory: Path) -> None:
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    for asset in provenance["assets"]:
        path = directory / asset["asset"]
        if sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise RuntimeError(f"Frozen asset hash mismatch: {path}")


def check_bundle(bundle: Path) -> dict[str, object]:
    """Do not compile an installer that silently omits or ships an old bridge."""
    package = bundle / "_internal" / "sukuna_pet"
    check_assets(package / "assets")
    source = ROOT / "src" / "sukuna_pet" / "integrations" / "dsh-bridge"
    manifest = json.loads((source / "package.json").read_text(encoding="utf-8"))
    hashes: dict[str, str] = {}
    for name in ("package.json", *manifest["files"]):
        path = package / "integrations" / "dsh-bridge" / name
        expected = sha256((source / name).read_bytes()).hexdigest()
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Bundled bridge missing or different from source: {name}")
        hashes[name] = expected
    with (ROOT / "pyproject.toml").open("rb") as stream:
        expected_version = tomllib.load(stream)["project"]["version"]
    metadata_path = package / "pyproject.toml"
    if not metadata_path.is_file():
        raise RuntimeError("Bundled application version metadata missing")
    with metadata_path.open("rb") as stream:
        bundled_version = tomllib.load(stream)["project"]["version"]
    if bundled_version != expected_version:
        raise RuntimeError("Bundled application version differs from installer")
    return {"name": manifest["name"], "version": manifest["version"], "sha256": hashes}


def run(arguments: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(arguments, cwd=ROOT, env=env, check=True)


def check_frozen_code(bundle: Path) -> dict[str, str]:
    """Check every runtime module against this source, including chat and persona."""
    from PyInstaller.archive.readers import CArchiveReader  # type: ignore[import-untyped]

    archive = CArchiveReader(str(bundle / "SukunaPet.exe")).open_embedded_archive("PYZ.pyz")
    hashes: dict[str, str] = {}
    source = ROOT / "src" / "sukuna_pet"
    for path in sorted(source.glob("*.py")):
        if path.name == "__main__.py":  # The freezer uses packaging/run_pet.py.
            continue
        name = "sukuna_pet" + ("" if path.stem == "__init__" else "." + path.stem)
        if name not in archive.toc:
            raise RuntimeError(f"Runtime module missing from frozen application: {name}")
        code = archive.extract(name)
        if code != compile(path.read_bytes(), code.co_filename, "exec", dont_inherit=True, optimize=0):
            raise RuntimeError(f"Frozen application differs from source: {name}")
        hashes[name] = sha256(path.read_bytes()).hexdigest()
    return hashes


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
    parser.add_argument("--output-root", type=Path, default=ROOT / "dist",
                        help="Separate app, release and build directories (default: dist)")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "src"))
    from sukuna_pet.chat_session import AUTHOR_PROMPT

    if sys.platform != "win32" or platform.machine().upper() not in ("AMD64", "X86_64"):
        parser.error("Build on Windows x64 with x64 CPython")
    iscc = args.iscc.resolve(strict=True)
    with (ROOT / "pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["project"]["version"]
    output = args.output_root.resolve()
    release = output / "release"
    release.mkdir(parents=True, exist_ok=True)
    locks = check_inputs()
    run([sys.executable, "-m", "pip", "check"])
    # Dependency discovery must not collect unrelated DLLs from developer tools
    # on PATH (e.g. Poppler's ICU has a different ABI from Windows' system ICU).
    build_env = dict(os.environ)
    build_env["PATH"] = os.pathsep.join((str(Path(sys.executable).parent),
                                       sys.base_prefix, str(Path(os.environ["SystemRoot"]) / "System32")))
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--distpath", str(output / "app"),
         "--workpath", str(output / "build" / "pyinstaller"),
         str(ROOT / "packaging" / "sukuna-pet.spec")], env=build_env)
    bundle = output / "app" / "SukunaPet"
    bridge = check_bundle(bundle)
    modules = check_frozen_code(bundle)
    shutil.copyfile(ROOT / "docs" / "user-guide.md", bundle / "使用说明.md")
    shutil.copyfile(ROOT / "docs" / "release-status.md", bundle / "验收说明.md")
    shutil.copyfile(ROOT / "docs" / "chat-acceptance.md", bundle / "试聊验收.md")
    # Include upstream license texts next to the replaceable Qt runtime DLLs.
    licenses = bundle / "THIRD-PARTY-LICENSES"
    shutil.copytree(ROOT / "packaging" / "licenses", licenses / "Qt", dirs_exist_ok=True)
    shutil.copyfile(ROOT / "packaging" / "licenses" / "dsh-pet-MIT.txt",
                    licenses / "dsh-pet-MIT.txt")
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
        "requirements_sha256": locks,
        "bridge": bridge,
        "application_modules_sha256": modules,
        "prompt_version": AUTHOR_PROMPT.version,
        "acceptance": "candidate; author installed-app conversation acceptance pending (#53)",
        "assets": json.loads((bundle / "_internal" / "sukuna_pet" / "assets" / "provenance.json").read_text(encoding="utf-8")),
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
