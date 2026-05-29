# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Lilith Agent

a = Analysis(
    ['lilith_agent.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('LILITH_README.md', '.'),
        ('LILITH_ROADMAP.md', '.'),
        ('LILITH_TOOLS.md', '.'),
    ],
    hiddenimports=[
        'requests',
        'rich',
        'rich.console',
        'rich.markdown',
        'rich.panel',
        'rich.rule',
        'rich.table',
        'rich.theme',
        'sqlite3',
        'json',
        'subprocess',
        'threading',
        'concurrent.futures',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lilith',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
