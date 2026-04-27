# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import os
import sys

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
# Ensure PySide6 Qt plugins are strictly packaged to prevent 'Missing qwindows.dll'
try:
    import PySide6
    pyside_dir = os.path.dirname(PySide6.__file__)
    # Common paths for Qt plugins
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

# Onedir mode (directory) is significantly faster and more reliable than onefile 
# for PySide6 apps because it avoids unpacking large DLLs to Temp at runtime
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Examly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Hides the terminal window
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
    name='Examly',
)
