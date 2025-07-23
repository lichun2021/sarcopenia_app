# -*- mode: python ; coding: utf-8 -*-
"""
SarcopeniaApp PyInstaller 配置文件
用于将整个肌少症检测系统打包为单个可执行文件
"""

import sys
import os
from pathlib import Path

# 获取项目根目录
project_root = Path(SPECPATH)

# 收集所有数据文件和依赖
datas = [
    # SarcNeuro Edge 整个目录
    (str(project_root / 'sarcneuro-edge'), 'sarcneuro-edge'),
    
    # 主系统配置文件
    (str(project_root / 'device_config.json'), '.'),
    (str(project_root / 'requirements.txt'), '.'),
    
    # 图标文件
    (str(project_root / 'icon.ico'), '.'),
    
    # 模块说明文档
    (str(project_root / '模块说明.md'), '.'),
]

# 隐藏导入 - SarcNeuro Edge 依赖的所有包
hiddenimports = [
    # FastAPI 相关
    'fastapi',
    'fastapi.staticfiles',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.security',
    'fastapi.responses',
    'fastapi.exceptions',
    'fastapi.params',
    'fastapi.routing',
    
    # Uvicorn 相关
    'uvicorn',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.server',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    
    # SQLAlchemy 相关
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.ext',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.dialects',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.engine',
    'sqlalchemy.pool',
    
    # Pydantic 相关
    'pydantic',
    'pydantic.main',
    'pydantic.fields',
    'pydantic.validators',
    'pydantic.typing',
    
    # 数据处理
    'numpy',
    'pandas',
    'scipy',
    'scipy.ndimage',
    'scipy._lib',
    'scipy._lib._docscrape',
    'scipy._lib._array_api',
    'scikit-learn',
    'sklearn',
    'sklearn.base',
    'sklearn.utils',
    
    # 其他依赖
    'jinja2',
    'aiofiles',
    'httpx',
    'python_multipart',
    'python_jose',
    'python_jose.jwt',
    'passlib',
    'passlib.context',
    'python_dotenv',
    'schedule',
    'reportlab',
    'matplotlib',
    'seaborn',
    'websockets',
    'psutil',
    
    # 系统模块
    'requests',
    'json',
    'threading',
    'subprocess',
    'signal',
    'pathlib',
    'contextlib',
    'asyncio',
    'datetime',
    'logging',
    'time',
    'os',
    'sys',
    'unittest',
    'unittest.mock',
    'pydoc',
    
    # 主系统模块
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'serial',
    'matplotlib.pyplot',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.figure',
    'matplotlib.colors',
    
    # 自定义模块
    'data_converter',
    'sarcneuro_service',
    'integration_ui',
    'serial_interface',
    'data_processor',
    'visualization',
    'device_config',
]

# 排除的模块（减少打包大小）
excludes = [
    'pytest',
    'tkinter.test',
]

# 分析主程序
a = Analysis(
    ['pressure_sensor_ui.py'],  # 主程序入口
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 处理Python字节码
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SarcopeniaApp',  # 可执行文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用UPX压缩
    upx_exclude=[
        "vcruntime140.dll",  # 不要压缩这些关键DLL
        "python38.dll",
        "python39.dll",
        "python310.dll",
        "python311.dll",
        "python312.dll",
        "python313.dll",
    ],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'icon.ico'),  # 图标文件
    version_file=None,
    uac_admin=False,  # 不需要管理员权限
    uac_uiaccess=False,
    manifest=None,
)

# 添加额外的构建信息
if sys.platform.startswith('win'):
    # Windows特定配置
    exe.append_pkg_path = True
    
print(f"""
🚀 PyInstaller 配置完成！

📦 打包设置:
- 主程序: pressure_sensor_ui.py
- 输出名称: SarcopeniaApp.exe
- 包含 SarcNeuro Edge: ✅
- UPX 压缩: ✅
- 控制台窗口: ❌ (隐藏)

🏗️ 开始打包命令:
pyinstaller SarcopeniaApp.spec --clean --noconfirm

📂 输出目录: dist/
""")