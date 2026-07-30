param([switch]$CheckOnly)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $projectRoot "logs"
$logPath = Join-Path $logDirectory "启动日志.txt"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
Start-Transcript -Path $logPath -Force | Out-Null

try {
    Set-Location $projectRoot
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  无人机路径规划程序" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""

    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "尚未安装独立运行环境。请先双击【安装环境.bat】。"
    }

    & $venvPython -c "import sys, numpy, matplotlib, openpyxl, uav_planner; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "运行环境缺少组件或版本不正确。请重新双击【安装环境.bat】。"
    }

    if ($CheckOnly) {
        Write-Host "检查通过：程序运行环境完整。" -ForegroundColor Green
        exit 0
    }

    & $venvPython "main.py"
    $programExitCode = $LASTEXITCODE
    if ($programExitCode -ne 0 -and $programExitCode -ne 130) {
        throw "程序异常结束，退出代码为 $programExitCode。"
    }
    exit $programExitCode
}
catch {
    Write-Host ""
    Write-Host "程序未能启动：" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "详细信息已保存到 logs\启动日志.txt。"
    exit 1
}
finally {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
}
