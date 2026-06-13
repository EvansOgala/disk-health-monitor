# -*- mode: python ; coding: utf-8 -*-

import os
import sys
project_file = globals().get('__file__', None) or (sys.argv[0] if len(sys.argv) > 0 else None)
if project_file:
    project_path = os.path.abspath(os.path.dirname(project_file))
else:
    project_path = os.path.abspath(os.getcwd())

a = Analysis(
    ['main.py'],
    pathex=[project_path],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DiskHealthMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DiskHealthMonitor',
)
