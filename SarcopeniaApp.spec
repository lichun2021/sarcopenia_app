# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pressure_sensor_ui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gemsage', 'gemsage'), 
        ('config.ini', '.'),
        ('icon.ico', '.')
    ],
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
        'cv2',
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_agg', 'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_svg',  # 添加SVG后端支持
        'matplotlib.figure', 'matplotlib.colors', 'matplotlib.font_manager',
        'matplotlib.patches', 'matplotlib.patches.Circle', 'matplotlib.patches.Ellipse', 
        'matplotlib.path', 'matplotlib.gridspec',
        'seaborn',
        'tkcalendar', 'babel', 'babel.dates',
        'uvicorn', 'uvicorn.main', 'uvicorn.config', 'uvicorn.server',
        'fastapi', 'fastapi.middleware.cors', 'fastapi.responses', 'fastapi.staticfiles',
        'pydantic', 'asyncio', 'jinja2',
        
        # PDF generation (Using Playwright)
        'playwright', 'playwright.async_api', 'playwright.sync_api',
        'html_to_pdf',  # 新的HTML转PDF模块
        
        # Project modules
        'serial_interface', 'data_processor', 'visualization', 'device_config', 'window_manager',
        'patient_manager_ui', 'sarcopenia_database', 'detection_wizard_ui',
        'sarcneuro_service', 'logger_utils', 'date', 'port_manager', 'server_status',
        'data_converter', 'patient_info_dialog', 'detection_step_ui',
        'multi_port_interface', 'integration_ui', 'run_detection_system',
        
        # Algorithm engine
        'algorithm_engine_manager',
        
        # GemSage单文件模块 (已融合为单文件)
        # 注意：不需要导入具体模块，因为是通过importlib动态加载
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
