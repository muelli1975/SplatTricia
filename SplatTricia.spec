# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import shutil

import customtkinter
import torch

ROOT = Path(SPECPATH).resolve()
DATA_ITEMS = []
BINARY_ITEMS = []

# Runtime assets.
for rel_src, rel_dst in [
    ("assets", "assets"),
    ("tools", "tools"),
]:
    src = ROOT / rel_src
    if src.exists():
        DATA_ITEMS.append((str(src), rel_dst))

# Keep the model directory visible in the portable package.  The model itself is
# intentionally not part of SplatTricia and is supplied by the user.
model_dir = ROOT / "models"
if model_dir.exists():
    DATA_ITEMS.append((str(model_dir), "models"))

# Source snapshot and documentation for the exact release source state.
source_dir = ROOT / "source"
if source_dir.exists():
    DATA_ITEMS.append((str(source_dir), "source"))

for filename in ["README_DE.txt", "README_EN.txt", "LICENSE.txt", "LICENSES.txt"]:
    src = ROOT / filename
    if src.exists():
        DATA_ITEMS.append((str(src), "."))

# Force the installed CustomTkinter package data into the bundle.  This keeps
# theme files available even when PyInstaller's automatic hook behaviour changes.
ctk_dir = Path(customtkinter.__file__).resolve().parent
DATA_ITEMS.append((str(ctk_dir), "customtkinter"))

# Torch runtime DLLs are required by the CUDA build.  PyInstaller usually finds
# them, but adding them explicitly makes the release process less fragile.
torch_lib = Path(torch.__file__).resolve().parent / "lib"
if torch_lib.is_dir():
    for dll in torch_lib.glob("*.dll"):
        BINARY_ITEMS.append((str(dll), "torch/lib"))

# The multi-architecture gsplat extension is prepared before PyInstaller.  Add
# the native extension explicitly when present so target systems never compile.
gsplat_cuda = ROOT / "venv" / "Lib" / "site-packages" / "gsplat" / "cuda"
if gsplat_cuda.is_dir():
    for pyd in gsplat_cuda.glob("*.pyd"):
        BINARY_ITEMS.append((str(pyd), "gsplat/cuda"))

hiddenimports = [
    "customtkinter",
    "PIL._tkinter_finder",
    "torch",
    "torchvision",
    "numpy",
    "plyfile",
    "gsplat",
    "gsplat.rendering",
]

analysis = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=BINARY_ITEMS,
    datas=DATA_ITEMS,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["ninja"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="SplatTricia",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "splattricia.ico"),
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SplatTricia",
)
