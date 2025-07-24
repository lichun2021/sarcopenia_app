# -*- mode: python ; coding: utf-8 -*- 
 
import sys 
import os 
from pathlib import Path 
 
project_root = Path(SPECPATH) 
 
datas = [ 
    (str(project_root / 'sarcneuro-edge'), 'sarcneuro-edge'), 
    (str(project_root / 'templates'), 'templates'), 
    (str(project_root / 'icon.ico'), '.'), 
    (str(project_root / 'config.ini'), '.'),
] 
 
hiddenimports = [ 
    # FastAPI 完整依赖
    'fastapi', 
    'fastapi.staticfiles',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.responses',
    'fastapi.security',
    'fastapi.exceptions',
    'fastapi.params',
    'fastapi.routing',
    'fastapi.applications',
    
    # Uvicorn 依赖
    'uvicorn', 
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.server',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    
    # Starlette 依赖
    'starlette',
    'starlette.applications',
    'starlette.middleware',
    'starlette.responses',
    'starlette.routing',
    'starlette.staticfiles',
    
    # 其他必需依赖
    'multipart',
    'json',
    'uuid',
    'datetime',
    'pathlib',
    'typing',
] 
 
a = Analysis( 
    ['pressure_sensor_ui.py'], 
    pathex=[str(project_root)], 
    binaries=[], 
    datas=datas, 
    hiddenimports=hiddenimports, 
    hookspath=[], 
    hooksconfig={}, 
    runtime_hooks=[], 
    excludes=[], 
    win_no_prefer_redirects=False, 
    win_private_assemblies=False, 
    cipher=None, 
    noarchive=False, 
) 
 
pyz = PYZ(a.pure, a.zipped_data, cipher=None) 
 
exe = EXE( 
    pyz, 
    a.scripts, 
    a.binaries, 
    a.zipfiles, 
    a.datas, 
    [], 
    name='SarcopeniaApp', 
    debug=False, 
    bootloader_ignore_signals=False, 
    strip=False, 
    upx=True, 
    upx_exclude=[], 
    runtime_tmpdir=None, 
    console=True, 
    disable_windowed_traceback=False, 
    target_arch=None, 
    codesign_identity=None, 
    entitlements_file=None, 
    icon=str(project_root / 'icon.ico'), 
) 
