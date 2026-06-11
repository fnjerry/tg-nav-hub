# Push to github.com/fnjerry/tg-nav-hub (SSH:443, bypass broken git:// rewrite)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

git remote set-url origin git@github.com:fnjerry/tg-nav-hub.git

Write-Host "Testing SSH to GitHub (port 443)..."
ssh -T git@github.com 2>&1 | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "Pushing main..."
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: https://github.com/fnjerry/tg-nav-hub"
} else {
    Write-Host ""
    Write-Host "If you see 'Permission denied (publickey)':"
    Write-Host "  1. Copy public key:"
    Write-Host "     Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub"
    Write-Host "  2. GitHub -> Settings -> SSH and GPG keys -> New SSH key -> paste"
    Write-Host "  3. Run this script again"
    exit 1
}
