# Start site on fixed port 8765 (http://127.0.0.1:8765)
Set-Location $PSScriptRoot

$port = "8765"

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match [regex]::Escape($PSScriptRoot) } |
    ForEach-Object {
        Write-Host "Stopping old server PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

# uvicorn --reload orphans: worker survives after parent died
$alive = @{}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object { $alive[$_.ProcessId] = $true }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'spawn_main\(parent_pid=(\d+)' } |
    ForEach-Object {
        if ($_.CommandLine -match 'parent_pid=(\d+)') {
            $parent = [int]$Matches[1]
            if (-not $alive.ContainsKey($parent)) {
                Write-Host "Stopping orphan worker PID $($_.ProcessId) (dead parent $parent)"
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
    }
Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { $_.OwningProcess } |
    Sort-Object -Unique |
    ForEach-Object {
        Write-Host "Free port $port : kill PID $_"
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Milliseconds 800

& .\.venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1]))); s.close()" $port
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Port $port is still in use (stale uvicorn from hot-reload is common)."
    Write-Host "Close all terminals running this project, or reboot, then run .\run.ps1 again."
    Write-Host "Preview: http://127.0.0.1:$port"
    exit 1
}

.\.venv\Scripts\python.exe -m app
