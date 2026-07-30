@echo off
setlocal EnableExtensions
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
set "UAV_EXIT_CODE=%ERRORLEVEL%"
echo.
pause
exit /b %UAV_EXIT_CODE%
