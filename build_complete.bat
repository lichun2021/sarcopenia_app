@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo ========================================
echo Sarcopenia App Complete Build
echo ========================================
echo.

:: Check if pyinstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

:: Clean up previous builds
echo [INFO] Cleaning previous builds...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul

:: Create temporary sarcneuro-edge without heavy files
echo [INFO] Preparing sarcneuro-edge for packaging...
if exist "temp_sarcneuro" rmdir /s /q "temp_sarcneuro" 2>nul
mkdir temp_sarcneuro

:: Copy essential Python files only (exclude venv, logs, reports, temp)
xcopy sarcneuro-edge\*.py temp_sarcneuro\ /s /e >nul 2>&1
xcopy sarcneuro-edge\api temp_sarcneuro\api\ /s /e >nul 2>&1
xcopy sarcneuro-edge\app temp_sarcneuro\app\ /s /e >nul 2>&1
xcopy sarcneuro-edge\core temp_sarcneuro\core\ /s /e >nul 2>&1
xcopy sarcneuro-edge\models temp_sarcneuro\models\ /s /e >nul 2>&1
xcopy sarcneuro-edge\templates temp_sarcneuro\templates\ /s /e >nul 2>&1
xcopy sarcneuro-edge\static temp_sarcneuro\static\ /s /e >nul 2>&1

:: Copy essential data files (exclude large databases)
if exist "sarcneuro-edge\data" (
    mkdir temp_sarcneuro\data 2>nul
    copy sarcneuro-edge\data\*.db temp_sarcneuro\data\ >nul 2>&1
)

:: Copy requirements and config files
copy sarcneuro-edge\requirements.txt temp_sarcneuro\ >nul 2>&1
copy sarcneuro-edge\README.md temp_sarcneuro\ >nul 2>&1

echo [INFO] Building executable with essential sarcneuro-edge files...
echo.

pyinstaller --onefile --windowed --name=SarcopeniaApp --add-data="temp_sarcneuro;sarcneuro-edge" --add-data="config.ini;." --icon=icon.ico pressure_sensor_ui.py

:: Clean up temp directory
if exist "temp_sarcneuro" rmdir /s /q "temp_sarcneuro" 2>nul

if exist "dist\SarcopeniaApp.exe" (
    echo.
    echo [SUCCESS] Build completed!
    echo.
    echo Output: dist\SarcopeniaApp.exe
    echo.
    
    :: Copy configuration files
    copy config.ini dist\ >nul 2>&1
    copy sarcopenia_system.db dist\ >nul 2>&1
    copy device_config.db dist\ >nul 2>&1
    
    echo [INFO] Configuration files copied
    echo [INFO] sarcneuro-edge code packaged in executable
    echo.
    
    set /p choice="Test the executable? (y/n): "
    if /i "!choice!"=="y" (
        echo Starting SarcopeniaApp...
        cd dist
        start "" "SarcopeniaApp.exe"
        cd ..
    )
    
) else (
    echo.
    echo [ERROR] Build failed!
    echo Check the error messages above
    echo.
)

echo.
pause