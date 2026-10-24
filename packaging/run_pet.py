"""Windowed entry point used by PyInstaller, independent of the checkout."""

from sukuna_pet.desktop import main


if __name__ == "__main__":
    raise SystemExit(main())
