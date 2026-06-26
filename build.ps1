# HanToPdf 빌드 스크립트 - 바탕화면에 exe 생성
param(
    [string]$Version = ""
)
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [Environment]::GetFolderPath("Desktop")
$DistDir = Join-Path $Desktop "HanToPdf"
$DistExe = Join-Path $DistDir "HanToPdf.exe"
$VersionPy = Join-Path $ProjectDir "version.py"

Set-Location $ProjectDir

if ($Version) {
    Write-Host "version.py -> $Version"
    $content = Get-Content $VersionPy -Raw -Encoding UTF8
    $content = [regex]::Replace($content, '_DEFAULT = "[^"]*"', "_DEFAULT = `"$Version`"")
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($VersionPy, $content, $utf8NoBom)
    $BuildVersion = $Version
} else {
    $content = Get-Content $VersionPy -Raw -Encoding UTF8
    if ($content -match '_DEFAULT = "([^"]*)"') {
        $BuildVersion = $Matches[1]
    } else {
        $BuildVersion = "1.0.0"
    }
}
Write-Host "의존성 설치 중..."
pip install -r requirements.txt -q

$AssetsDir = Join-Path $ProjectDir "assets"
$PatchScript = Join-Path $ProjectDir "scripts\patch_gui_subsystem.py"
$IconIco = Join-Path $AssetsDir "icon.ico"

Write-Host "exe 빌드 중..."
pyinstaller `
    HanToPdf.spec `
    --distpath $Desktop `
    --workpath (Join-Path $ProjectDir "build") `
    --clean `
    --noconfirm

if (Test-Path $DistExe) {
    python $PatchScript $DistExe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "exe GUI 서브시스템 패치 실패." -ForegroundColor Red
        exit 1
    }
    $size = [math]::Round((Get-Item $DistExe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "완료! $DistExe ($size MB)" -ForegroundColor Green
    Write-Host "실행 폴더: $DistDir" -ForegroundColor Green

    $ShortcutPath = Join-Path $Desktop "HanToPdf.lnk"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $DistExe
    $Shortcut.WorkingDirectory = $DistDir
    $Shortcut.Description = "HanToPdf - 한글 파일 PDF 변환기"
    if (Test-Path $IconIco) {
        $Shortcut.IconLocation = "$IconIco,0"
    }
    $Shortcut.Save()
    Write-Host "바로가기 생성: $ShortcutPath" -ForegroundColor Green

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText((Join-Path $DistDir "VERSION.txt"), $BuildVersion, $utf8NoBom)
    Write-Host "VERSION.txt -> $BuildVersion" -ForegroundColor Green
} else {
    Write-Host "빌드 실패" -ForegroundColor Red
    exit 1
}
