# 每日定时采集（Windows 任务计划程序调用）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$logDir = Join-Path $PWD "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("sync-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

$py = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "未找到虚拟环境，请先执行: py -m venv .venv && pip install -r requirements.txt"
}

& $py scripts\run_sync.py *>&1 | Tee-Object -FilePath $logFile
exit $LASTEXITCODE
