# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

root_dir = Path(SPECPATH)

datas = [
    (str(root_dir / "models" / "best.pt"), "models"),
    (str(root_dir / "resources" / "logo.png"), "resources"),
]

hiddenimports = [
    "torch",
    "torch.nn",
    "torch.nn.modules",
    "torch.nn.functional",
    "cv2",
    "cv2.cv2",
    "onnxruntime",
    "onnxruntime.capi",
    "onnxruntime.capi._pybind_state",
    "PIL",
    "PIL._imaging",
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "ultralytics",
    "ultralytics.nn",
    "ultralytics.nn.tasks",
    "yaml",
    "loguru",
    "reportlab",
    "openpyxl",
    "pydantic",
]

a = Analysis(
    ["src/pcb_ai_inspector/__main__.py"],
    pathex=[str(root_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PCB-AI-Inspector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/logo.png",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PCB-AI-Inspector",
)