from pathlib import Path

root = Path(SPECPATH).parent
analysis = Analysis(
    [str(root / "packaging" / "run_pet.py")],
    pathex=[str(root / "src")],
    # Read this checkout, even when the build environment has an older editable
    # installation. Runtime modules are resolved from pathex in the same tree.
    datas=[(str(root / "pyproject.toml"), "sukuna_pet"),
           (str(root / "src" / "sukuna_pet" / "assets"), "sukuna_pet/assets"),
           (str(root / "src" / "sukuna_pet" / "integrations" / "dsh-bridge"),
            "sukuna_pet/integrations/dsh-bridge")],
    # Only these three Python Qt modules are used.
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtPdf",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtNetwork", "tkinter"],
)
# Optional image plugins pull in PDF/QML engines; all character images are PNGs,
# decoded by QtGui itself. Keep the native Windows platform/style plugins.
analysis.binaries = [entry for entry in analysis.binaries
                     if "plugins\\imageformats\\" not in entry[0].lower()
                     and not Path(entry[0]).name.lower().startswith(("qt6pdf", "qt6qml", "qt6quick"))]
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [],
    exclude_binaries=True,
    name="SukunaPet",
    console=False,
    icon="NONE",
    # Qt 6 configures per-monitor DPI awareness; do not override its policy.
)
collection = COLLECT(exe, analysis.binaries, analysis.datas, name="SukunaPet")
