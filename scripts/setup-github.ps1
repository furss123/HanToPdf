# GitHub 저장소 생성 및 푸시
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$status = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub 로그인이 필요합니다." -ForegroundColor Yellow
    Write-Host "실행: gh auth login" -ForegroundColor Cyan
    gh auth login
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    $name = Read-Host "저장소 이름 (기본: HanToPdf)"
    if (-not $name) { $name = "HanToPdf" }
    $public = Read-Host "공개 저장소? (Y/n)"
    $isPublic = ($public -ne "n")
    $visibility = if ($isPublic) { "public" } else { "private" }
    gh repo create $name --$visibility --source=. --remote=origin --push
} else {
    Write-Host "원격 저장소: $remote"
    git push -u origin main
}

Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Green
Write-Host "1. GitHub → Settings → Pages → Source: GitHub Actions"
Write-Host "2. main 브랜치 push 시 docs/ 가 Pages에 자동 배포됩니다."
Write-Host "3. Codespaces: 저장소 → Code → Codespaces → Create codespace"
