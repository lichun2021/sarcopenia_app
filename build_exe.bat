@echo off
chcp 65001 > nul
echo 🚀 肌少症检测系统 - EXE 打包脚本
echo ======================================

:: 检查Python环境
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python环境，请确保已安装Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

:: 检查必要文件
if not exist "pressure_sensor_ui.py" (
    echo ❌ 错误: 未找到主程序文件 pressure_sensor_ui.py
    pause
    exit /b 1
)

if not exist "sarcneuro-edge" (
    echo ❌ 错误: 未找到 sarcneuro-edge 目录
    pause
    exit /b 1
)

if not exist "SarcopeniaApp.spec" (
    echo ❌ 错误: 未找到 PyInstaller 配置文件
    pause
    exit /b 1
)

echo ✅ 必要文件检查通过

:: 检查依赖包
echo 🔍 检查依赖包...
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo 📦 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ 安装 PyInstaller 失败
        pause
        exit /b 1
    )
)

:: 安装项目依赖
echo 📦 安装项目依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ⚠️ 警告: 部分依赖包安装失败，继续打包...
)

:: 安装 sarcneuro-edge 依赖
echo 📦 安装 SarcNeuro Edge 依赖...
if exist "sarcneuro-edge\requirements.txt" (
    pip install -r sarcneuro-edge\requirements.txt
    if errorlevel 1 (
        echo ⚠️ 警告: SarcNeuro Edge 依赖包安装失败，继续打包...
    )
)

:: 清理之前的构建
echo 🧹 清理之前的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

:: 开始打包
echo 🚀 开始打包 EXE 文件...
echo 这可能需要几分钟，请耐心等待...
echo.

pyinstaller SarcopeniaApp.spec --clean --noconfirm

:: 检查打包结果
if exist "dist\SarcopeniaApp.exe" (
    echo.
    echo ✅ 打包成功！
    echo.
    echo 📂 可执行文件位置: dist\SarcopeniaApp.exe
    
    :: 获取文件大小
    for %%A in ("dist\SarcopeniaApp.exe") do set filesize=%%~zA
    set /a filesizeMB=filesize/1024/1024
    echo 📊 文件大小: %filesizeMB% MB
    
    echo.
    echo 🎉 打包完成！可以直接运行 dist\SarcopeniaApp.exe
    echo.
    echo 📋 包含功能:
    echo    - 实时压力传感器数据采集
    echo    - 热力图可视化
    echo    - 肌少症智能分析 (SarcNeuro Edge)
    echo    - 多设备支持
    echo.
    
    :: 询问是否立即运行
    set /p choice="是否立即运行程序? (y/n): "
    if /i "%choice%"=="y" (
        echo 🚀 启动程序...
        start "" "dist\SarcopeniaApp.exe"
    )
    
) else (
    echo.
    echo ❌ 打包失败！
    echo 请检查上述错误信息
    echo.
    echo 🔍 常见问题解决方案:
    echo 1. 确保所有依赖包已正确安装
    echo 2. 检查 Python 版本是否为 3.8+
    echo 3. 确保有足够的磁盘空间 (建议至少 2GB)
    echo 4. 检查防病毒软件是否阻止了文件创建
    echo.
)

echo.
echo ⏸️ 按任意键退出...
pause > nul