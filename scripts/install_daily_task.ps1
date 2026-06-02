# Register daily sync for current user (usually no Administrator needed)
param(
    [string]$Time = "09:00",
    [string]$TaskName = "TgNavHub-DailySync"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dailyScript = Join-Path $root "scripts\daily_sync.ps1"

if (-not (Test-Path $dailyScript)) {
    Write-Error "Missing $dailyScript"
}

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$dailyScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Update existing task $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "TG Nav Hub: daily Telegram channel sync" | Out-Null

Write-Host "OK: $TaskName runs daily at $Time (current user)"
Write-Host "Test: Start-ScheduledTask -TaskName $TaskName"
Write-Host "Logs: $root\logs\"
