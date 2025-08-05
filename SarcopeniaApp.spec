# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pressure_sensor_ui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gemsage', 'gemsage'), 
        ('config.ini', '.'),
        ('GEMSAGE_MODIFICATIONS.md', '.')
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
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg', 
        'matplotlib.figure', 'matplotlib.colors', 'matplotlib.font_manager',
        'uvicorn', 'uvicorn.main', 'uvicorn.config', 'uvicorn.server',
        'fastapi', 'fastapi.middleware.cors', 'fastapi.responses', 'fastapi.staticfiles',
        'pydantic', 'asyncio', 'jinja2',
        
        # PDF generation
        'xhtml2pdf', 'xhtml2pdf.pisa', 'xhtml2pdf.default', 'xhtml2pdf.context',
        'weasyprint', 'weasyprint.css', 'weasyprint.css.targets', 'weasyprint.html',
        'reportlab', 'reportlab.pdfgen', 'reportlab.pdfgen.canvas',
        'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.colors',
        'reportlab.lib.styles', 'reportlab.lib.units', 'reportlab.lib.enums',
        'reportlab.platypus', 'reportlab.platypus.tables', 'reportlab.platypus.paragraph',
        'reportlab.platypus.doctemplate', 'reportlab.platypus.flowables',
        'reportlab.pdfbase', 'reportlab.pdfbase.pdfmetrics', 'reportlab.pdfbase.ttfonts',
        'reportlab.pdfbase.cidfonts', 'reportlab.pdfbase._cidfontdata',
        'reportlab.graphics', 'reportlab.graphics.barcode', 'reportlab.graphics.barcode.code128',
        'reportlab.graphics.barcode.code93', 'reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.common',
        'reportlab.graphics.barcode.eanbc', 'reportlab.graphics.barcode.qr', 'reportlab.graphics.barcode.usps',
        'html5lib', 'bs4', 'beautifulsoup4',
        
        # Project modules
        'serial_interface', 'data_processor', 'visualization', 'visualization_3d', 'device_config', 'window_manager',
        'patient_manager_ui', 'sarcopenia_database', 'detection_wizard_ui',
        'sarcneuro_service', 'logger_utils', 'date', 'port_manager', 'server_status',
        'data_converter', 'patient_info_dialog', 'detection_step_ui',
        'multi_port_interface', 'integration_ui', 'run_detection_system',
        
        # Algorithm engine
        'algorithm_engine_manager',
        
        # GemSage modules
        'gemsage', 'gemsage.core_calculator', 'gemsage.full_medical_report_generator',
        'gemsage.multi_file_workflow', 'gemsage.ai_assessment_engine',
        'gemsage.comprehensive_diagnosis', 'gemsage.adaptive_cop_analyzer',
        'gemsage.progressive_cop_analyzer', 'gemsage.ground_reaction_force_analysis',
        'gemsage.joint_angle_analysis', 'gemsage.joint_torque_power_analysis',
        'gemsage.hardware_adaptive_service', 'gemsage.fix_step_detection',
        'gemsage.debug_data_structure'
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
)
