# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: onedir，排除一切非必需模块控制体积
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # tkinter 保留（UI 必需），其余大块头全裁掉
        'unittest', 'pydoc', 'doctest', 'argparse', 'xml', 'pydoc',
        'multiprocessing', 'concurrent', 'asyncio', 'sqlite3',
        'email', 'http.server', 'xmlrpc', 'logging.handlers',
        'distutils', 'setuptools', 'py_compile', 'compileall',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Shanyi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX 会显著提高杀软误报率，不用
    console=False,        # 无控制台黑窗
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Shanyi',
)
