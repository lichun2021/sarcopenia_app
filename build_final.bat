@echo off
chcp 65001 >nul
echo ========================================
echo SarcopeniaApp 最终版本打包
echo ========================================
echo.

:: 清理
echo [INFO] 清理构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "logs" rmdir /s /q "logs"

:: 打包
echo [INFO] 开始打包最终版本...
echo        - 控制台窗口: 已关闭
echo        - 调试日志: 可通过config.ini配置
echo        - 报告保存: exe目录/日期/
echo.

pyinstaller SarcopeniaApp_clean.spec --clean --noconfirm

if exist "dist\SarcopeniaApp.exe" (
    echo.
    echo [SUCCESS] 打包成功！
    echo.
    echo [INFO] 程序特性:
    echo    ✓ 无控制台窗口
    echo    ✓ 可配置调试模式 (config.ini)
    echo    ✓ 报告保存在exe同级目录
    echo    ✓ FastAPI服务正常工作
    echo.
    echo [INFO] 配置文件说明:
    echo    - config.ini: 调试开关和路径配置
    echo    - 若需调试，修改enable_debug=true
    echo.
    
    :: 复制配置文件到dist目录
    copy config.ini dist\ >nul 2>&1
    echo [INFO] 已复制config.ini到程序目录
    echo.
    
    set /p choice="运行程序测试? (y/n): "
    if /i "!choice!"=="y" (
        echo [INFO] 启动程序 (无控制台窗口)...
        start "" "dist\SarcopeniaApp.exe"
    )
    
) else (
    echo.
    echo [ERROR] 打包失败！
    echo 请检查上方的错误信息
)

echo.
pause