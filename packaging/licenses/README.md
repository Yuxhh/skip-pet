# Third-party notices

The application bundles CPython 3.14.4, PySide6 / Qt 6.12.0 and shiboken6 6.12.0.
Their original binaries are dynamically linked and unmodified. The installation
directory retains the Qt libraries separately from SukunaPet.exe so that they
can be replaced with compatible builds. The application source and build
instructions are delivered alongside Setup.exe.

PySide6 / shiboken6 / Qt are Copyright The Qt Company Ltd. and other contributors.
The open-source license option used here is LGPL 3.0 with its accompanying GPL
3.0 text. GPL 2.0 is also included for the alternative license choices stated in
the upstream Python distribution metadata. The wheels' commercial-license
notice is retained verbatim; its presence does not imply a commercial license.

License texts in this folder were copied verbatim from Qt's v6.12.0 sources:
https://github.com/qt/qtbase/tree/v6.12.0/LICENSES

Corresponding unmodified sources, build instructions and copyright notices:

- Qt 6.12.0: https://code.qt.io/cgit/qt/qtbase.git/tree/?h=v6.12.0
- Qt for Python / shiboken 6.12.0: https://code.qt.io/cgit/pyside/pyside-setup.git/tree/?h=v6.12.0
- CPython 3.14.4: https://github.com/python/cpython/tree/v3.14.4
- PyInstaller 6.22.3 bootloader and distribution exception:
  https://github.com/pyinstaller/pyinstaller/tree/v6.22.3

The build copies the installed CPython LICENSE.txt and distribution-provided
license texts to THIRD-PARTY-LICENSES as well. No license for the original
Sukuna character or the reference video is granted by these software licenses;
the asset's actual provenance is recorded in sukuna_pet/assets/provenance.json.
