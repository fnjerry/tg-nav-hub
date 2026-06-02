# Free a TCP port by stopping tg-nav-hub / uvicorn orphans (Windows reload workers).
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# Project python processes
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match [regex]::Escape($root) } |
    ForEach-Object {
        Write-Host "Stop project python PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force
    }

# Uvicorn --reload orphans: worker parent_pid no longer exists
$alive = @{}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    ForEach-Object { $alive[$_.ProcessId] = $true }

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "spawn_main\(parent_pid=(\d+)" } |
    ForEach-Object {
        if ($_.CommandLine -match "parent_pid=(\d+)") {
            $parent = [int]$Matches[1]
            if (-not $alive.ContainsKey($parent)) {
                Write-Host "Stop orphan uvicorn worker PID $($_.ProcessId) (dead parent $parent)"
                Stop-Process -Id $_.ProcessId -Force
            }
        }
    }

Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { $_.OwningProcess } |
    Sort-Object -Unique |
    ForEach-Object {
        Write-Host "Stop listener on port $Port PID $_"
        Stop-Process -Id $_ -Force
    }

Start-Sleep -Milliseconds 500

& "$root\.venv\Scripts\python.exe" -c "import socket,sys; s=socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1]))); s.close()" $Port
if ($LASTEXITCODE -eq 0) {
    Write-Host "Port $Port is free."
    exit 0
}
Write-Host "Port $Port still in use. Close other terminals or reboot."
exit 1
