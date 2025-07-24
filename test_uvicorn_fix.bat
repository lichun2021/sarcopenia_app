@echo off
chcp 65001 >nul
echo ========================================
echo 测试 Uvicorn 日志修复
echo ========================================
echo.

echo [INFO] 快速重新打包...
pyinstaller SarcopeniaApp_clean.spec --noconfirm

if exist "dist\SarcopeniaApp.exe" (
    echo.
    echo [INFO] 启动程序测试 (有控制台窗口，方便调试)
    echo [INFO] 请尝试肌少症分析功能
    echo.
    
    :: 复制配置文件
    copy config.ini dist\ >nul 2>&1
    
    :: 启动并等待
    cd dist
    SarcopeniaApp.exe
    
) else (
    echo [ERROR] 打包失败！
)

pause