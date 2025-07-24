@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ========================================
echo SarcopeniaApp EXE Build Script
echo ========================================
echo.

:: Check Python environment
echo [INFO] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python environment check passed
echo.

:: Check required files
echo [INFO] Checking required files...
if not exist "pressure_sensor_ui.py" (
    echo [ERROR] Main program file not found: pressure_sensor_ui.py
    pause
    exit /b 1
)

if not exist "sarcneuro-edge" (
    echo [ERROR] sarcneuro-edge directory not found
    pause
    exit /b 1
)

if not exist "SarcopeniaApp.spec" (
    echo [ERROR] PyInstaller config file not found
    pause
    exit /b 1
)
echo [OK] Required files check passed
echo.

:: Check dependencies
echo [INFO] Checking dependencies...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

:: Install project dependencies
echo [INFO] Installing project dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Some dependencies failed to install, continuing...
    )
)

:: Install sarcneuro-edge dependencies
echo [INFO] Installing SarcNeuro Edge dependencies...
if exist "sarcneuro-edge\requirements.txt" (
    pip install -r sarcneuro-edge\requirements.txt
    if errorlevel 1 (
        echo [WARN] SarcNeuro Edge dependencies failed to install, continuing...
    )
)

:: Clean previous builds
echo [INFO] Cleaning previous build files...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "__pycache__" rmdir /s /q "__pycache__" 2>nul

:: Start building
echo [INFO] Starting EXE build process...
echo This may take several minutes, please wait...
echo.

pyinstaller SarcopeniaApp.spec --clean --noconfirm

:: Check build result
if exist "dist\SarcopeniaApp.exe" (
    echo.
    echo [SUCCESS] Build completed successfully!
    echo.
    echo [INFO] Executable location: dist\SarcopeniaApp.exe
    
    :: Get file size
    for %%A in ("dist\SarcopeniaApp.exe") do set filesize=%%~zA
    set /a filesizeMB=!filesize!/1024/1024
    echo [INFO] File size: !filesizeMB! MB
    
    echo.
    echo [FEATURES] Included features:
    echo    - Real-time pressure sensor data collection
    echo    - Heatmap visualization
    echo    - Sarcopenia AI analysis (SarcNeuro Edge)
    echo    - Multi-device support
    echo.
    
    :: Ask to run immediately
    set /p choice="Run the program now? (y/n): "
    if /i "!choice!"=="y" (
        echo [INFO] Starting program...
        start "" "dist\SarcopeniaApp.exe"
    )
    
) else (
    echo.
    echo [ERROR] Build failed!
    echo Please check the error messages above
    echo.
    echo [TROUBLESHOOTING] Common solutions:
    echo 1. Ensure all dependencies are correctly installed
    echo 2. Check Python version is 3.8+
    echo 3. Ensure sufficient disk space (at least 2GB)
    echo 4. Check if antivirus is blocking file creation
    echo.
)

echo.
echo Press any key to exit...
pause >nul