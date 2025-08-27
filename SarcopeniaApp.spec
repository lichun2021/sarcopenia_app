# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pressure_sensor_ui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gemsage', 'gemsage'), 
        ('config.ini', '.'),
        ('icon.ico', '.'),
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
        'cv2',
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_agg', 'matplotlib.backends.backend_tkagg', 
        'matplotlib.figure', 'matplotlib.colors', 'matplotlib.font_manager',
        'matplotlib.patches', 'matplotlib.patches.Circle', 'matplotlib.patches.Ellipse', 
        'matplotlib.path', 'matplotlib.gridspec',
        'seaborn',
        'tkcalendar', 'babel', 'babel.dates',
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
        'reportlab.graphics', 'reportlab.graphics.barcode', 
        'reportlab.graphics.barcode.common', 'reportlab.graphics.barcode.code128', 'reportlab.graphics.barcode.code93',
        'reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.eanbc', 'reportlab.graphics.barcode.qr',
        'reportlab.graphics.barcode.usps', 'reportlab.graphics.barcode.usps4s', 'reportlab.graphics.barcode.lto',
        'reportlab.graphics.barcode.widgets', 'reportlab.graphics.barcode.fourstate', 'reportlab.graphics.barcode.dmtx',
        'reportlab.graphics.barcode.aztec', 'reportlab.graphics.barcode.code11', 'reportlab.graphics.barcode.itf',
        'reportlab.graphics.barcode.codabar', 'reportlab.graphics.barcode.ecc200datamatrix',
        'html5lib', 'bs4', 'beautifulsoup4',
        
        # Project modules
        'serial_interface', 'data_processor', 'visualization', 'device_config', 'window_manager',
        'patient_manager_ui', 'sarcopenia_database', 'detection_wizard_ui',
        'sarcneuro_service', 'logger_utils', 'date', 'port_manager', 'server_status',
        'data_converter', 'patient_info_dialog', 'detection_step_ui',
        'multi_port_interface', 'integration_ui', 'run_detection_system',
        
        # Algorithm engine
        'algorithm_engine_manager',
        
        # GemSage modules (根据11.py和实际导入更新)
        'gemsage',
        'gemsage.ultimate_fix_report_generator',      # 终极修复版报告生成器 (11.py入口)
        'gemsage.gait_report_generator',              # 基础步态报告生成器
        'gemsage.improved_report_generator',          # 改进版报告生成器
        'gemsage.gait_analyzer',                      # 步态分析器 (main_gait_system.py需要)
        'gemsage.visualization',                      # 可视化模块
        'gemsage.report_generator',                   # 报告生成器
        'gemsage.hospital_heatmap_generator',         # 医院级热力图生成器
        'gemsage.medical_heatmap_generator',          # 医疗热力图生成器
        'gemsage.medical_step_length_analyzer',       # 医疗步长分析器
        'gemsage.integrated_heatmap_report',          # 集成热力图报告
        'gemsage.improved_gait_report_generator',     # 改进版步态报告生成器
        'gemsage.complete_improved_report_generator', # 完整改进版报告生成器
        'gemsage.final_fix_report_generator',         # 最终修复版报告生成器
        'gemsage.generate_improved_report',           # 生成改进报告
        'gemsage.generate_professional_report',       # 生成专业报告
        'gemsage.batch_processor',                    # 批处理器
        'gemsage.template_filler',                    # 模板填充器
        'gemsage.main_gait_system',                   # 主步态系统
        'gemsage.advanced_gait_analyzer',             # 高级步态分析器 (main_gait_system需要)
        'gemsage.test_system'                         # 测试系统 (batch_processor需要)
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
