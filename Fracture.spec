from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path.cwd()
SRC = ROOT / "src"

datas = [
    (str(SRC / "UI"), "UI"),
    (str(SRC / "icons"), "icons"),
]

# PySide6
pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all("PySide6")

datas += pyside_datas
binaries = pyside_binaries
hiddenimports = pyside_hiddenimports

a = Analysis(
    ["src/main.py"],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Fracture",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
