@echo off
chcp 65001 >nul
echo ======================================
echo SarcNeuro 启动调试工具
echo ======================================
echo.

:: 清理旧日志
if exist "logs" (
    echo [INFO] 清理旧日志文件...
    del /q logs\*.log 2>nul
) else (
    mkdir logs
)

:: 重新打包（快速版本）
echo [INFO] 重新打包（包含完整FastAPI依赖）...
pyinstaller SarcopeniaApp_clean.spec --clean --noconfirm

if not exist "dist\SarcopeniaApp.exe" (
    echo [ERROR] 打包失败！
    pause
    exit /b 1
)

echo [INFO] 启动程序，请进行肌少症分析测试...
echo [INFO] 程序启动后，请：
echo         1. 点击肌少症分析按钮
echo         2. 等待启动失败
echo         3. 关闭程序
echo         4. 回到这里按任意键查看日志
echo.

:: 启动exe
start /wait dist\SarcopeniaApp.exe

echo.
echo [INFO] 程序已关闭，正在分析日志...
echo.

:: 显示日志内容
if exist "logs\startup_debug.log" (
    echo ==================== 启动调试日志 ====================
    type logs\startup_debug.log
    echo.
    echo ==================== 日志结束 ====================
) else (
    echo [WARN] 没有找到启动调试日志文件
)

if exist "logs\sarcneuro_debug.log" (
    echo.
    echo ==================== 详细调试日志 ====================
    type logs\sarcneuro_debug.log
    echo.
    echo ==================== 日志结束 ====================
) else (
    echo [WARN] 没有找到详细调试日志文件
)

echo.
echo [INFO] 日志文件位置:
echo        - logs\startup_debug.log (关键启动信息)
echo        - logs\sarcneuro_debug.log (详细日志)
echo.
pause