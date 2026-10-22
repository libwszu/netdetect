# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['net_monitor_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/szu_logo_64.png', 'assets'), ('assets/szu_logo.ico', 'assets'), ('LICENSE', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='深大校园网自动重连',
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
    icon=['assets/szu_logo.ico'],
)
