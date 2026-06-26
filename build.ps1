# HanToPdf 빌드 스크립트 - 바탕화면에 exe 생성
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [Environment]::GetFolderPath("Desktop")
$DistExe = Join-Path $Desktop "HanToPdf.exe"

Set-Location $ProjectDir

Write-Host "의존성 설치 중..."
pip install -r requirements.txt -q

$RuntimeHook = Join-Path $ProjectDir "rthook_hide_console.py"

Write-Host "exe 빌드 중..."
pyinstaller `
    --onefile `
    --windowed `
    --name HanToPdf `
    --distpath $Desktop `
    --workpath (Join-Path $ProjectDir "build") `
    --specpath $ProjectDir `
    --runtime-hook $RuntimeHook `
    --clean `
    --noconfirm `
    --collect-all tkinterdnd2 `
    --exclude-module numpy `
    --exclude-module pandas `
    --exclude-module PIL `
    --exclude-module scipy `
    --exclude-module IPython `
    --exclude-module pytest `
    main.py

if (Test-Path $DistExe) {
    $size = [math]::Round((Get-Item $DistExe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "완료! $DistExe ($size MB)" -ForegroundColor Green

    $ShortcutPath = Join-Path $Desktop "HanToPdf.lnk"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $DistExe
    $Shortcut.WorkingDirectory = $Desktop
    $Shortcut.Description = "HanToPdf - 한글 파일 PDF 변환기"
    $Shortcut.Save()
    Write-Host "바로가기 생성: $ShortcutPath" -ForegroundColor Green
} else {
    Write-Host "빌드 실패" -ForegroundColor Red
    exit 1
}
