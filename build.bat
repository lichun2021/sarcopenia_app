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

REM 构建后复制资源到 dist
if exist dist (
    echo 复制 chrome 目录到 dist\chrome ...
    if exist chrome (
        xcopy "chrome" "dist\chrome" /E /I /Y >nul
    ) else (
        echo 警告：未找到 chrome 目录，跳过复制
    )

    echo 复制 icon.ico 到 dist 根目录...
    if exist icon.ico (
        copy /Y "icon.ico" "dist\icon.ico" >nul
    ) else (
        echo 警告：未找到 icon.ico，跳过复制
    )

    echo 复制 config.ini 到 dist 根目录...
    if exist config.ini (
        copy /Y "config.ini" "dist\config.ini" >nul
    ) else (
        echo 警告：未找到 config.ini，跳过复制
    )

    
)

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