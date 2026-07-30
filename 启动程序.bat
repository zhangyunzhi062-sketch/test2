@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 尚未安装运行环境。请先双击“安装环境.bat”。
  pause
  exit /b 1
)

".venv\Scripts\python.exe" main.py
echo.
pause
