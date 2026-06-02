# Add or remove TG Nav Hub from Windows login startup (Startup folder, no admin)
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$startScript = Join-Path $root "scripts\start_service.ps1"
$startupDir = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startupDir "TG Nav Hub.lnk"

if (-not (Test-Path $startScript)) {
    Write-Error "Missing $startScript"
}

if ($Remove) {
    if (Test-Path $lnkPath) {
        Remove-Item $lnkPath -Force
        Write-Host "Removed startup shortcut."
    } else {
        Write-Host "Startup shortcut not found."
    }
    exit 0
}

$arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startScript`""
$wsh = New-Object -ComObject WScript.Shell
$lnk = $wsh.CreateShortcut($lnkPath)
$lnk.TargetPath = "powershell.exe"
$lnk.Arguments = $arg
$lnk.WorkingDirectory = $root
$lnk.Description = "TG Nav Hub - http://127.0.0.1:8765"
$lnk.Save()

Write-Host "Added to Windows startup:"
Write-Host "  $lnkPath"
Write-Host ""
Write-Host "After next login (or reboot), site: http://127.0.0.1:8765"
Write-Host "Remove: .\scripts\install_startup.ps1 -Remove"
