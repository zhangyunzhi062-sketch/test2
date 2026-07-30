@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo 未找到 Python。请先安装 Python 3.10 或更高版本，并勾选“Add Python to PATH”。
  pause
  exit /b 1
)

echo 正在创建独立运行环境……
py -3 -m venv .venv
if errorlevel 1 goto :failed

echo 正在安装程序需要的组件……
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo 安装完成。以后直接双击“启动程序.bat”即可。
pause
exit /b 0

:failed
echo.
echo 安装没有完成。请检查网络连接和上方错误提示。
pause
exit /b 1
