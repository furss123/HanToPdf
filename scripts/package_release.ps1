# HanToPdf 릴리스 패키지 생성 (GitHub 자동 업데이트용)
# 사용: powershell -ExecutionPolicy Bypass -File scripts\package_release.ps1 -Version 1.0.1
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$GitHubRepo = "furss123/HanToPdf",
    [string]$GitHubBranch = "main",
    [string]$SourceDir = "",
    [string]$OutputDir = "",
    [string]$ReleaseNotes = ""
)
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $SourceDir) {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $SourceDir = Join-Path $Desktop "HanToPdf"
}
if (-not $OutputDir) {
    $OutputDir = Join-Path $ProjectDir "releases"
}
$ZipName = "HanToPdf-$Version.zip"
$ZipPath = Join-Path $OutputDir $ZipName
$ManifestPath = Join-Path $OutputDir "version.json"
$VersionPy = Join-Path $ProjectDir "version.py"

if (-not (Test-Path (Join-Path $SourceDir "HanToPdf.exe"))) {
    Write-Error "빌드 폴더를 찾을 수 없습니다: $SourceDir"
}

$BuildScript = Join-Path $ProjectDir "build.ps1"
Write-Host "버전 $Version 으로 재빌드 중..." -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File $BuildScript -Version $Version
if ($LASTEXITCODE -ne 0) {
    throw "build.ps1 실패 (exit $LASTEXITCODE)"
}
$Desktop = [Environment]::GetFolderPath("Desktop")
$SourceDir = Join-Path $Desktop "HanToPdf"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

$staging = Join-Path $env:TEMP ("HanToPdf_pkg_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $staging -Force | Out-Null
try {
    & robocopy $SourceDir $staging /E /COPY:DAT /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }
    Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $ZipPath -Force
} finally {
    Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
}

$hash = (Get-FileHash -Algorithm SHA256 -Path $ZipPath).Hash.ToLower()
if (-not $ReleaseNotes) {
    $ReleaseNotes = "HanToPdf $Version"
}
$manifest = @{
    version       = $Version
    download_url  = $ZipName
    sha256        = $hash
    release_notes = $ReleaseNotes
} | ConvertTo-Json -Depth 3
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($ManifestPath, $manifest, $utf8NoBom)

$rawBase = "https://raw.githubusercontent.com/$GitHubRepo/$GitHubBranch/releases"
Write-Host ""
Write-Host "ZIP: $ZipPath"
Write-Host "Manifest: $ManifestPath"
Write-Host "SHA256: $hash"
Write-Host ""
Write-Host "GitHub 업로드 (releases 폴더):" -ForegroundColor Cyan
Write-Host "  releases/version.json"
Write-Host "  releases/$ZipName"
Write-Host ""
Write-Host "download_url 은 앱에서 자동으로 다음 주소로 해석됩니다:" -ForegroundColor Cyan
Write-Host "  $rawBase/$ZipName"
Write-Host ""
Write-Host "update_config.py 의 GITHUB_REPO 가 `"$GitHubRepo`" 인지 확인하세요."
