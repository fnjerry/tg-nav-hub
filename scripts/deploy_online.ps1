# 触发线上部署并等待数据就绪（需已配置 GitHub → Render 自动部署）
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$SiteUrl = if ($env:SITE_URL) { $env:SITE_URL.TrimEnd("/") } else { "https://ai.24s.net" }
$Token = $env:ADMIN_SYNC_TOKEN
if (-not $Token) {
    $envFile = Join-Path $Root ".env"
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*ADMIN_SYNC_TOKEN=(.+)$') { $Token = $Matches[1].Trim(); break }
        }
    }
}
if (-not $Token) { throw "请设置 ADMIN_SYNC_TOKEN 或在 .env 中配置" }

Write-Host "==> 推送 main 触发 Render 部署..."
git push origin main

Write-Host "==> 等待 90s 让 Render 完成部署..."
Start-Sleep -Seconds 90

Write-Host "==> 健康检查 $SiteUrl/health"
curl.exe -fsS "$SiteUrl/health" | Write-Host

Write-Host "==> 触发 sync..."
curl.exe -fsS -X POST "$SiteUrl/api/sync" -H "Authorization: Bearer $Token" | Write-Host

Write-Host "==> 检查链接数量..."
$count = curl.exe -fsS "$SiteUrl/api/links" | & python -c "import json,sys; print(len(json.load(sys.stdin)))"
Write-Host "线上链接数: $count"
if ([int]$count -le 0) { throw "线上仍无数据，请检查 Render 环境变量与 Telegram 配置" }

Write-Host "部署完成: $SiteUrl"
