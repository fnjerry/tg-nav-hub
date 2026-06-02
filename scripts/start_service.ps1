# Autostart entry: start TG Nav Hub (minimal output)
$ErrorActionPreference = "SilentlyContinue"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$port = 8765
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    exit 1
}

# Stop old project processes
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match [regex]::Escape($root) } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

$alive = @{}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object { $alive[$_.ProcessId] = $true }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'spawn_main\(parent_pid=(\d+)' } |
    ForEach-Object {
        if ($_.CommandLine -match 'parent_pid=(\d+)') {
            $parent = [int]$Matches[1]
            if (-not $alive.ContainsKey($parent)) {
                Stop-Process -Id $_.ProcessId -Force
            }
        }
    }

Start-Sleep -Milliseconds 500
& $py -m app
