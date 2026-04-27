# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import os
import sys
import glob

hiddenimports = []
hiddenimports += collect_submodules('PySide6')
hiddenimports += collect_submodules('qasync')
hiddenimports += collect_submodules('pynput')
hiddenimports += [
    'keyring.backends.Windows',
    'keyring.backends.macOS',
    'win32ctypes.pywin32.pywintypes',
    'win32cred'
]

datas = [
    ('config.json', '.'),
]

# ── Bundle Tesseract OCR (Windows) ──
# Chocolatey installs to C:\Program Files\Tesseract-OCR
tesseract_dirs = [
    r'C:\Program Files\Tesseract-OCR',
    r'C:\Program Files (x86)\Tesseract-OCR',
]
for tess_dir in tesseract_dirs:
    if os.path.isdir(tess_dir):
        # Bundle the entire Tesseract directory (exe + tessdata + DLLs)
        datas.append((tess_dir, 'tesseract'))
        print(f"[Examly.spec] Bundling Tesseract from: {tess_dir}")
        break

# ── Bundle PySide6 Qt plugins ──
try:
    import PySide6
    pyside_dir = os.path.dirname(PySide6.__file__)
    if os.path.exists(os.path.join(pyside_dir, 'Qt', 'plugins')):
        datas.append((os.path.join(pyside_dir, 'Qt', 'plugins'), 'PySide6/Qt/plugins'))
    elif os.path.exists(os.path.join(pyside_dir, 'plugins')):
        datas.append((os.path.join(pyside_dir, 'plugins'), 'PySide6/plugins'))
except ImportError:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
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
    [],
    exclude_binaries=True,
    name='WindowsHelper',
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
    name='WindowsHelper',
)
