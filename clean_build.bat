@echo off
echo Cleaning all PyInstaller cache and rebuilding...
echo.

:: Clean PyInstaller cache
echo [1/6] Cleaning PyInstaller cache...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "__pycache__" rmdir /s /q "__pycache__" 2>nul

:: Clean Python cache files recursively
echo [2/6] Cleaning Python cache files...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul

:: Clean PyInstaller work directory
echo [3/6] Cleaning PyInstaller work directory...
if exist "%USERPROFILE%\.pyinstaller" rmdir /s /q "%USERPROFILE%\.pyinstaller" 2>nul
if exist "%TEMP%\pyinstaller" rmdir /s /q "%TEMP%\pyinstaller" 2>nul

:: Check main file modification time
echo [4/6] Checking main file...
if exist "pressure_sensor_ui.py" (
    echo Main file found: pressure_sensor_ui.py
    for %%f in ("pressure_sensor_ui.py") do echo Last modified: %%~tf
) else (
    echo ERROR: Main file not found!
    pause
    exit /b 1
)

:: Reinstall dependencies to ensure latest versions
echo [5/6] Updating dependencies...
pip install --upgrade pyinstaller
pip install -r requirements.txt --force-reinstall --no-cache-dir

:: Build with verbose output
echo [6/6] Building with verbose output...
echo This will show detailed information...
echo.

pyinstaller --clean --noconfirm --onefile --noconsole --name SarcopeniaApp --distpath dist --workpath build/work --specpath build ^
    --add-data "sarcneuro-edge;sarcneuro-edge" ^
    --add-data "device_config.json;." ^
    --add-data "icon.ico;." ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox ^
    --hidden-import numpy ^
    --hidden-import matplotlib ^
    --hidden-import serial ^
    --hidden-import requests ^
    --hidden-import sqlite3 ^
    pressure_sensor_ui.py

echo.
if exist "dist\SarcopeniaApp.exe" (
    echo SUCCESS: New executable created!
    echo Location: dist\SarcopeniaApp.exe
    for %%f in ("dist\SarcopeniaApp.exe") do echo Created: %%~tf
    for %%f in ("dist\SarcopeniaApp.exe") do echo Size: %%~zf bytes
) else (
    echo FAILED: No executable found!
    echo Check the output above for errors
)

echo.
pause