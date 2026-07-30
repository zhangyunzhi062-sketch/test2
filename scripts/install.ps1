param([switch]$CheckOnly)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $projectRoot "logs"
$logPath = Join-Path $logDirectory "安装日志.txt"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
Start-Transcript -Path $logPath -Force | Out-Null

function Test-PythonVersion {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$PrefixArguments = @()
    )
    try {
        & $Executable @PrefixArguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Find-SuitablePython {
    $candidates = [System.Collections.Generic.List[object]]::new()
    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        $candidates.Add([pscustomobject]@{
            Executable = $launcher.Source
            Arguments = @("-3")
            Label = "py -3"
        })
    }

    foreach ($commandName in @("python.exe", "python3.exe")) {
        $foundPaths = & where.exe $commandName 2>$null
        foreach ($foundPath in $foundPaths) {
            if (-not [string]::IsNullOrWhiteSpace($foundPath)) {
                $candidates.Add([pscustomobject]@{
                    Executable = $foundPath.Trim()
                    Arguments = @()
                    Label = $foundPath.Trim()
                })
            }
        }
    }

    $seen = @{}
    foreach ($candidate in $candidates) {
        $key = "$($candidate.Executable)|$($candidate.Arguments -join ' ')"
        if ($seen.ContainsKey($key)) {
            continue
        }
        $seen[$key] = $true
        if (Test-PythonVersion -Executable $candidate.Executable -PrefixArguments $candidate.Arguments) {
            return $candidate
        }
    }
    return $null
}

try {
    Set-Location $projectRoot
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  无人机路径规划程序：安装环境" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "详细日志：logs\安装日志.txt"
    Write-Host ""

    if (Test-Path -LiteralPath $venvPython) {
        if (-not (Test-PythonVersion -Executable $venvPython)) {
            throw "现有 .venv 环境无效或 Python 版本低于 3.10。请删除项目中的 .venv 文件夹后重新运行。"
        }
        Write-Host "已找到可用的独立运行环境。" -ForegroundColor Green
    }
    else {
        $python = Find-SuitablePython
        if ($null -eq $python) {
            throw @"
没有找到 Python 3.10 或更高版本。
请从 https://www.python.org/downloads/windows/ 安装新版 Python，
安装时勾选 Add Python to PATH，然后重新双击【安装环境.bat】。
"@
        }

        Write-Host "找到可用 Python：$($python.Label)"
        if ($CheckOnly) {
            Write-Host "检查通过：可以创建运行环境。" -ForegroundColor Green
            exit 0
        }

        Write-Host "正在创建独立运行环境，请稍候……"
        $pythonArguments = [string[]]$python.Arguments
        & $python.Executable @pythonArguments -m venv ".venv"
        if ($LASTEXITCODE -ne 0) {
            throw "创建 .venv 失败。"
        }
    }

    if ($CheckOnly) {
        Write-Host "检查通过：独立运行环境可用。" -ForegroundColor Green
        exit 0
    }

    Write-Host "正在更新安装工具……"
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "更新 pip 失败，请检查网络连接。"
    }

    Write-Host "正在安装程序组件……"
    & $venvPython -m pip install -r "requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        throw "安装程序组件失败，请检查网络连接。"
    }

    & $venvPython -c "import numpy, matplotlib, openpyxl, uav_planner"
    if ($LASTEXITCODE -ne 0) {
        throw "组件安装后自检失败。"
    }

    Write-Host ""
    Write-Host "安装完成！以后直接双击【启动程序.bat】即可。" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host ""
    Write-Host "安装没有完成：" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "请查看 logs\安装日志.txt 中的详细信息。"
    exit 1
}
finally {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
}
