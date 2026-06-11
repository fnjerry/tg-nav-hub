# Build KEY=VALUE lines for Render "Add from .env" (never commit output)
$root = Split-Path $PSScriptRoot -Parent
$src = Join-Path $root ".env"
$out = Join-Path $root "data\render-env-upload.txt"
if (-not (Test-Path $src)) { Write-Error "Missing .env" }
$keys = @(
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_SESSION_STRING",
    "TELEGRAM_CHANNELS",
    "ADMIN_SYNC_TOKEN",
    "DATABASE_PATH",
    "ENABLE_DAILY_SYNC",
    "DAILY_SYNC_TIME"
)
$map = @{}
Get-Content $src -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)\s*$') {
        $map[$Matches[1]] = $Matches[2]
    }
}
$map["DATABASE_PATH"] = "data/nav.db"
$lines = foreach ($k in $keys) {
    if ($map.ContainsKey($k) -and $map[$k]) { "$k=$($map[$k])" }
}
New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
$lines | Set-Content $out -Encoding UTF8
Write-Host "Wrote $out ($($lines.Count) vars)"
