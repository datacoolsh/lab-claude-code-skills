@echo off
REM ==============================================================================
REM setup_env.bat — Doc Classifier 环境引导脚本（Windows CMD 版）
REM ==============================================================================
REM
REM 功能: CMD 薄封装，自动调用 PowerShell 版本的 setup_env.ps1
REM 适用: 习惯使用 CMD 而非 PowerShell 的 Windows 用户
REM
REM 用法:
REM   scripts\setup_env.bat
REM ==============================================================================

echo [doc-classifier] 正在通过 PowerShell 执行环境引导...
echo.

REM 获取当前脚本所在目录
set "SCRIPT_DIR=%~dp0"

REM 调用 PowerShell 脚本（-ExecutionPolicy Bypass 避免策略限制）
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup_env.ps1" -Activate

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [doc-classifier] 环境引导失败，错误码: %ERRORLEVEL%
    echo [doc-classifier] 如果 PowerShell 不可用，请尝试直接运行:
    echo   python "%SCRIPT_DIR%batch_extract.py" ^<源文件夹^>
    echo   脚本内置自引导机制，会自动处理环境
    exit /b %ERRORLEVEL%
)

echo.
echo [doc-classifier] 环境就绪。激活虚拟环境:
echo   "%SCRIPT_DIR%..\.venv\Scripts\activate.bat"