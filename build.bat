@echo off
chcp 65001 >nul
echo ========================================
echo 智能肌少症检测系统 - 打包
echo ========================================
echo.

REM 检查文件
if not exist pressure_sensor_ui.py (
    echo 错误：pressure_sensor_ui.py 文件不存在！
    pause
    exit /b 1
)

if not exist SarcopeniaApp.spec (
    echo 错误：SarcopeniaApp.spec 文件不存在！
    pause
    exit /b 1
)

REM 清理
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo 开始打包...
echo.

pyinstaller --clean --noconfirm SarcopeniaApp.spec

echo.

if exist dist\SarcopeniaApp.exe (
    echo ========================================
    echo 打包成功！
    echo 运行: dist\SarcopeniaApp.exe
    echo ========================================
) else (
    echo 打包失败！请检查上面的错误信息
)

echo.
pause