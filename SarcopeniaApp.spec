# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pressure_sensor_ui.py'],
    pathex=[],
    binaries=[],
    datas=[('sarcneuro-edge', 'sarcneuro-edge'), ('config.ini', '.')],
    hiddenimports=[
        # Tkinter and GUI
        'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext', 'tkinter.messagebox', 'tkinter.filedialog',
        
        # Standard library
        'threading', 'time', 'os', 'json', 'sqlite3', 'datetime', 'configparser',
        'subprocess', 'signal', 'pathlib', 'uuid', 'math', 'base64', 'io',
        'logging', 'typing', 'queue', 'sys',
        
        # Third-party packages
        'serial', 'serial.tools', 'serial.tools.list_ports', 
        'PIL', 'PIL.Image', 'PIL.ImageTk',
        'numpy', 'pandas', 'requests', 
        'scipy', 'scipy.ndimage',
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg', 
        'matplotlib.figure', 'matplotlib.colors', 'matplotlib.font_manager',
        'uvicorn', 'uvicorn.main', 'uvicorn.config', 'uvicorn.server',
        'fastapi', 'fastapi.middleware.cors', 'fastapi.responses', 'fastapi.staticfiles',
        'pydantic', 'asyncio', 'jinja2',
        
        # Project modules
        'serial_interface', 'data_processor', 'visualization', 'device_config', 'window_manager',
        'patient_manager_ui', 'sarcopenia_database', 'detection_wizard_ui',
        'sarcneuro_service', 'logger_utils', 'date', 'port_manager', 'server_status',
        'data_converter', 'patient_info_dialog', 'detection_step_ui',
        'multi_port_interface', 'integration_ui', 'run_detection_system'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['jupyter', 'notebook', 'IPython'],
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
    name='SarcopeniaApp',
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
)
